"""Error paths: missing rows, wrong owners, wrong methods, and failed storage.

The behaviour layer proves the product works. This module proves the same
boundaries fail in a predictable, non-destructive way when they are crossed.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Draft, Match, QRLabel, Report
from core.qr_labels import token_digest
from core.services import get_or_create_draft, moderate
from tests.support import (
    BAG_ANSWERS,
    AppTestCase,
    TempMediaMixin,
    make_match,
    make_report,
    make_user,
    meeting,
    start_wizard,
    submit_wizard,
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MissingObjectTests(TestCase):
    def setUp(self):
        self.user = make_user("missing@example.test")
        self.client.force_login(self.user)

    def test_unknown_numeric_ids_are_404_not_500(self):
        cases = [
            ("get", reverse("report", args=[999999])),
            ("post", reverse("edit", args=[999999])),
            ("get", reverse("report-photo", args=[999999])),
            ("get", reverse("draft", args=[999999])),
            ("get", reverse("draft-photo", args=[999999])),
            ("get", reverse("match", args=[999999])),
            ("get", reverse("qr-label-image", args=[999999])),
            ("post", reverse("qr-label-reactivate", args=[999999])),
            ("post", reverse("qr-label-deactivate", args=[999999])),
        ]
        for method, path in cases:
            with self.subTest(path=path):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 404)

    def test_unknown_uuid_and_token_routes_are_404(self):
        random_id = uuid.uuid4()
        paths = [
            reverse("report-qr", args=[random_id]),
            reverse("report-found", args=[random_id]),
            reverse("qr-label-public", args=["not-a-real-token"]),
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_a_non_numeric_path_segment_is_404_not_a_server_error(self):
        for path in ("/reports/not-a-number/", "/drafts/not-a-number/", "/matches/x/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class OwnershipBoundaryTests(AppTestCase):
    def setUp(self):
        self.report = make_report(self.owner)
        self.draft = Draft.objects.create(owner=self.owner, data={"title": "Mine"})
        self.match = make_match(
            self.report, make_report(self.finder, "Found"), score=90,
        )
        self.label = QRLabel.objects.create(
            owner=self.owner,
            item_name="Blue backpack",
            contact_phone="03001234567",
            token_hash=token_digest("owner-token"),
            qr_image="private_qr_labels/missing.png",
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.login(self.outsider)

    def test_another_account_cannot_read_or_change_private_resources(self):
        cases = [
            ("get", reverse("report", args=[self.report.pk])),
            ("post", reverse("edit", args=[self.report.pk])),
            ("get", reverse("report-photo", args=[self.report.pk])),
            ("get", reverse("draft", args=[self.draft.pk])),
            ("get", reverse("draft-photo", args=[self.draft.pk])),
            ("get", reverse("match", args=[self.match.pk])),
            ("get", reverse("qr-label-image", args=[self.label.pk])),
            ("post", reverse("qr-label-reactivate", args=[self.label.pk])),
            ("post", reverse("qr-label-deactivate", args=[self.label.pk])),
        ]
        for method, path in cases:
            with self.subTest(path=path):
                self.assertEqual(getattr(self.client, method)(path).status_code, 404)

    def test_an_outsider_cannot_act_on_a_match_even_with_a_valid_action(self):
        response = self.client.post(
            reverse("match", args=[self.match.pk]), {"action": "reject"},
        )
        self.assertEqual(response.status_code, 404)
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class HttpMethodTests(AppTestCase):
    def setUp(self):
        self.report = make_report(self.owner)
        self.label = QRLabel.objects.create(
            owner=self.owner,
            item_name="Bag",
            contact_phone="03001234567",
            token_hash=token_digest("method-token"),
            qr_image="private_qr_labels/missing.png",
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.login()

    def test_post_only_endpoints_reject_every_read_or_update_method(self):
        paths = [
            reverse("edit", args=[self.report.pk]),
            reverse("qr-label-reactivate", args=[self.label.pk]),
            reverse("qr-label-deactivate", args=[self.label.pk]),
            reverse("logout"),
        ]
        for path in paths:
            for method in ("get", "put", "patch", "delete"):
                with self.subTest(path=path, method=method):
                    response = getattr(self.client, method)(path)
                    self.assertEqual(response.status_code, 405)

    def test_post_only_endpoints_still_accept_post(self):
        response = self.client.post(reverse("qr-label-deactivate", args=[self.label.pk]))
        self.assertRedirects(response, reverse("qr-labels"), fetch_redirect_response=False)
        self.label.refresh_from_db()
        self.assertTrue(self.label.revoked)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ManagementErrorTests(AppTestCase):
    def setUp(self):
        self.report = make_report(self.owner)

    def test_non_staff_members_cannot_open_or_post_to_management(self):
        self.login(self.owner)
        self.assertEqual(self.client.get(reverse("management")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("management"), {
                "report": self.report.pk, "action": "close",
            }).status_code,
            403,
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "Open")

    def test_invalid_report_ids_are_rejected_with_400(self):
        self.login(self.staff)
        for value in ("", "abc", "0", "-1", "9223372036854775808", "1.5"):
            with self.subTest(value=value):
                response = self.client.post(reverse("management"), {
                    "report": value, "action": "close",
                })
                self.assertEqual(response.status_code, 400)

    def test_a_valid_but_unknown_report_is_a_404(self):
        self.login(self.staff)
        self.assertEqual(
            self.client.post(reverse("management"), {
                "report": 999999, "action": "close",
            }).status_code,
            404,
        )

    def test_an_unknown_action_leaves_the_report_untouched(self):
        self.login(self.staff)
        response = self.client.post(reverse("management"), {
            "report": self.report.pk, "action": "bogus",
        })
        self.assertRedirects(response, reverse("management"), fetch_redirect_response=False)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "Open")

    def test_closing_and_removing_update_the_report_and_dismiss_open_matches(self):
        for action, expected in (("close", "Closed"), ("remove", "Removed")):
            with self.subTest(action=action):
                report = make_report(self.owner, title=f"{action} me")
                found = make_report(self.finder, "Found", title=f"{action} found")
                match = make_match(report, found, score=90)
                self.login(self.staff)
                response = self.client.post(reverse("management"), {
                    "report": report.pk, "action": action,
                })
                self.assertRedirects(
                    response, reverse("management"), fetch_redirect_response=False,
                )
                report.refresh_from_db()
                match.refresh_from_db()
                self.assertEqual(report.status, expected)
                self.assertEqual(match.state, "Rejected")

    def test_reserved_or_closed_reports_cannot_be_moderated(self):
        for changes in ({"reserved": True}, {"status": "Returned"}):
            with self.subTest(changes=changes):
                report = make_report(self.owner, **changes)
                self.login(self.staff)
                self.client.post(reverse("management"), {
                    "report": report.pk, "action": "close",
                })
                report.refresh_from_db()
                self.assertNotEqual(report.status, "Closed")

    def test_the_service_refuses_a_non_moderator_even_with_a_valid_action(self):
        with self.assertRaises(Exception):
            moderate(self.report, self.owner, "close")
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "Open")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DraftAndPublishErrorTests(AppTestCase):
    def test_an_incomplete_draft_is_not_published_or_deleted(self):
        draft, url = start_wizard(self.client, self.owner)
        # All steps look visited, but one value is blank so publishing must
        # still fail instead of creating a half-empty report.
        draft.data = {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": timezone.localdate().isoformat(),
            "description": "", "contact": "03001234567",
            "location": "Central Library", "lat": "24.86", "lng": "67.001",
            "location_detail": "Entrance",
            "answers": {"colour": "Blue", "kind": "Backpack",
                        "material": "Fabric", "pockets": "2", "mark": "None"},
        }
        draft.save(update_fields=["data"])
        response = self.client.post(url + "?step=5")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Complete and check every step before submitting.")
        self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())
        self.assertFalse(Report.objects.filter(owner=self.owner).exists())

    def test_a_published_draft_cannot_be_published_a_second_time(self):
        draft, url = start_wizard(self.client, self.owner)
        submit_wizard(self.client, self.owner)
        self.assertEqual(self.client.post(url + "?step=5").status_code, 404)
        self.assertEqual(Report.objects.filter(owner=self.owner).count(), 1)

    def test_scanning_a_lost_report_resumes_the_newest_of_several_drafts(self):
        lost = make_report(self.owner, "Lost", title="Blue backpack")
        older = Draft.objects.create(owner=self.finder, data={"title": "Old draft"})
        newer = Draft.objects.create(owner=self.finder, data={
            "description": "stale public text",
            "contact": "03001111111",
            "answers": {"colour": "Blue"},
            "lat": "24.86",
            "lng": "67.001",
        })
        Draft.objects.filter(pk=older.pk).update(
            updated_at=timezone.now() - timedelta(days=1),
        )
        self.login(self.finder)
        response = self.client.get(reverse("report-found", args=[lost.public_id]))
        self.assertRedirects(
            response,
            reverse("draft", args=[newer.pk]) + "?step=3",
            fetch_redirect_response=False,
        )
        newer.refresh_from_db()
        older.refresh_from_db()
        self.assertEqual(newer.data["kind"], "Found")
        self.assertEqual(newer.data["category"], lost.category)
        self.assertEqual(newer.data["title"], lost.title)
        self.assertEqual(newer.data["location"], lost.location)
        for private_key in ("description", "location_detail", "contact", "answers", "lat", "lng"):
            with self.subTest(private_key=private_key):
                self.assertNotIn(private_key, newer.data)
        self.assertEqual(older.data, {"title": "Old draft"})

    def test_scanning_a_closed_report_shows_a_notice_and_creates_no_draft(self):
        for changes in ({"status": "Closed"}, {"reserved": True}, {"status": "Removed"}):
            with self.subTest(changes=changes):
                lost = make_report(self.owner, "Lost", title="Blue backpack", **changes)
                self.login(self.finder)
                response = self.client.get(
                    reverse("report-found", args=[lost.public_id]),
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "already been resolved")
                self.assertFalse(
                    Draft.objects.filter(owner=self.finder, report__isnull=True).exists()
                )

    def test_scanning_your_own_report_redirects_without_making_a_draft(self):
        lost = make_report(self.owner, "Lost")
        self.login(self.owner)
        response = self.client.get(reverse("report-found", args=[lost.public_id]))
        self.assertRedirects(
            response, reverse("report", args=[lost.pk]), fetch_redirect_response=False,
        )
        self.assertFalse(
            Draft.objects.filter(owner=self.owner, report__isnull=True).exists()
        )

    def test_get_or_create_draft_returns_the_most_recent_unattached_draft(self):
        older = Draft.objects.create(owner=self.owner, data={"title": "Older"})
        newer = Draft.objects.create(owner=self.owner, data={"title": "Newer"})
        Draft.objects.filter(pk=older.pk).update(
            updated_at=timezone.now() - timedelta(days=1),
        )
        draft, created = get_or_create_draft(self.owner)
        self.assertFalse(created)
        self.assertEqual(draft.pk, newer.pk)

    def test_get_or_create_draft_creates_one_when_none_exists(self):
        draft, created = get_or_create_draft(self.owner)
        self.assertTrue(created)
        self.assertEqual(draft.owner, self.owner)
        self.assertEqual(draft.data, {})


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class StorageFailureTests(TempMediaMixin, AppTestCase):
    def test_a_qr_image_failure_does_not_leave_an_orphan_label(self):
        self.login()
        self.client.raise_request_exception = False
        with patch("core.views.make_label_qr", side_effect=OSError("disk full")):
            response = self.client.post(reverse("qr-labels"), {
                "item_name": "Blue backpack",
                "contact_phone": "03001234567",
            })
        self.assertEqual(response.status_code, 500)
        self.assertFalse(QRLabel.objects.filter(owner=self.owner).exists())

    def test_missing_private_files_are_404_not_500(self):
        self.login()
        label = QRLabel.objects.create(
            owner=self.owner,
            item_name="Bag",
            contact_phone="03001234567",
            token_hash=token_digest("missing-file-token"),
            qr_image="private_qr_labels/missing.png",
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.client.raise_request_exception = False
        self.assertEqual(
            self.client.get(reverse("qr-label-image", args=[label.pk])).status_code,
            404,
        )


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MatchActionErrorTests(AppTestCase):
    def setUp(self):
        self.lost = make_report(self.owner, "Lost", answers=BAG_ANSWERS)
        self.found = make_report(self.finder, "Found", answers=BAG_ANSWERS)
        self.match = make_match(self.lost, self.found)

    def test_an_unknown_action_is_reported_without_changing_state(self):
        self.login(self.owner)
        response = self.client.post(
            reverse("match", args=[self.match.pk]), {"action": "bogus"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unavailable in this state")
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")

    def test_a_missing_action_is_reported_without_changing_state(self):
        self.login(self.owner)
        response = self.client.post(reverse("match", args=[self.match.pk]), {})
        self.assertEqual(response.status_code, 200)
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")

    def test_a_proposer_cannot_accept_their_own_proposal(self):
        from core.services import transition

        transition(self.match.pk, self.owner, "propose", meeting())
        self.login(self.owner)
        response = self.client.post(
            reverse("match", args=[self.match.pk]), {"action": "accept"},
        )
        self.assertEqual(response.status_code, 200)
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Handover Proposed")

    def test_a_malformed_meeting_never_reserves_a_report(self):
        self.login(self.owner)
        response = self.client.post(reverse("match", args=[self.match.pk]), {
            "action": "propose",
            "meeting_place": "NED Security Office",
            "meeting_at": "not a time",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DD-MM-YY hh:mm AM/PM")
        self.lost.refresh_from_db()
        self.found.refresh_from_db()
        self.match.refresh_from_db()
        self.assertFalse(self.lost.reserved or self.found.reserved)
        self.assertEqual(self.match.state, "Possible Match")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class QrLabelStateErrorTests(AppTestCase):
    def setUp(self):
        self.label = QRLabel.objects.create(
            owner=self.owner,
            item_name="Blue backpack",
            contact_phone="03001234567",
            token_hash=token_digest("state-token"),
            qr_image="private_qr_labels/missing.png",
            expires_at=timezone.now() + timedelta(days=30),
        )

    def test_deactivation_and_reactivation_are_owner_only_post_actions(self):
        self.login(self.owner)
        self.client.post(reverse("qr-label-deactivate", args=[self.label.pk]))
        self.label.refresh_from_db()
        self.assertTrue(self.label.revoked)
        self.assertFalse(self.label.is_active)

        self.client.post(reverse("qr-label-reactivate", args=[self.label.pk]))
        self.label.refresh_from_db()
        self.assertFalse(self.label.revoked)
        self.assertTrue(self.label.is_active)
        self.assertEqual(self.label.token_hash, token_digest("state-token"))

    def test_a_revoked_or_expired_public_page_never_shows_the_phone(self):
        self.label.revoked = True
        self.label.save(update_fields=["revoked"])
        response = self.client.get(reverse("qr-label-public", args=["state-token"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This QR label is inactive")
        self.assertNotContains(response, "03001234567")

        self.label.revoked = False
        self.label.expires_at = timezone.now() - timedelta(seconds=1)
        self.label.save(update_fields=["revoked", "expires_at"])
        response = self.client.get(reverse("qr-label-public", args=["state-token"]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "03001234567")
