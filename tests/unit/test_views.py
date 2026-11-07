"""Unit tests for ``core.views``: each view's own branching and HTTP contract."""

import uuid
from datetime import timedelta

from django.contrib.messages import get_messages
from django.core.files.base import ContentFile
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Draft, QRLabel, Report
from core.views import posted_selection
from tests.support import (
    PASSWORD,
    TempMediaMixin,
    draft_data,
    make_match,
    make_report,
    make_user,
    meeting_field_value,
)


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


class PostedSelectionTests(TestCase):
    def test_scalar_values_are_copied_and_repeated_values_are_collected(self):
        post = QueryDict("kind=Lost&title=Blue+bag&contents=CNIC&contents=Cash")
        self.assertEqual(posted_selection(post), {
            "kind": "Lost",
            "title": "Blue bag",
            "contents": ["CNIC", "Cash"],
        })

    def test_a_missing_selection_becomes_an_empty_list(self):
        self.assertEqual(posted_selection(QueryDict("kind=Lost")), {
            "kind": "Lost",
            "contents": [],
        })


class LoginRedirectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("login-redirect@example.test")

    def login(self, **extra):
        payload = {
            "username": self.user.email,
            "password": PASSWORD,
        }
        payload.update(extra)
        return self.client.post(reverse("login"), payload)

    def test_a_user_without_reports_or_a_draft_starts_a_new_report(self):
        response = self.login()
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)

    def test_a_saved_draft_is_resumed(self):
        draft = Draft.objects.create(owner=self.user, data={"title": "Saved"})
        response = self.login()
        self.assertRedirects(
            response, reverse("draft", args=[draft.pk]), fetch_redirect_response=False,
        )

    def test_a_user_with_a_report_lands_on_the_dashboard(self):
        make_report(self.user)
        response = self.login()
        self.assertRedirects(
            response, reverse("dashboard"), fetch_redirect_response=False,
        )

    def test_a_safe_next_url_wins_over_the_default_redirect(self):
        response = self.login(next=reverse("reports"))
        self.assertRedirects(
            response, reverse("reports"), fetch_redirect_response=False,
        )

    def test_bad_credentials_render_the_form_again(self):
        response = self.client.post(reverse("login"), {
            "username": self.user.email,
            "password": "wrong",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class DashboardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("dashboard-owner@example.test")
        cls.finder = make_user("dashboard-finder@example.test")

    def test_anonymous_visitors_are_sent_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
            fetch_redirect_response=False,
        )

    def test_a_user_with_no_reports_and_no_draft_starts_a_report(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)

    def test_a_saved_draft_is_resumed_instead_of_the_dashboard(self):
        draft = Draft.objects.create(owner=self.owner, data={"title": "Saved"})
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response, reverse("draft", args=[draft.pk]), fetch_redirect_response=False,
        )

    def test_removed_reports_do_not_count_as_reports(self):
        make_report(self.owner, status="Removed")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)

    def test_counts_and_the_report_slice_exclude_removed_reports(self):
        open_report = make_report(self.owner, "Lost", title="Open item")
        returned = make_report(self.owner, "Lost", title="Returned item", status="Returned")
        closed = make_report(self.owner, "Lost", title="Closed item", status="Closed")
        make_report(self.owner, "Lost", title="Removed item", status="Removed")

        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_count"], 3)
        self.assertEqual(response.context["open_count"], 1)
        self.assertEqual(response.context["returned_count"], 1)
        self.assertEqual([report.pk for report in response.context["reports"]], [open_report.pk])
        self.assertEqual([report.pk for report in response.context["returned_reports"]], [returned.pk])
        self.assertIn(closed, Report.objects.all())

    def test_reserved_reports_come_first_then_newest_first(self):
        oldest = make_report(self.owner, "Lost", title="Oldest reserved")
        second = make_report(self.owner, "Lost", title="Second")
        third = make_report(self.owner, "Lost", title="Third")
        newest = make_report(self.owner, "Lost", title="Newest")
        Report.objects.filter(pk=oldest.pk).update(
            reserved=True, created_at=timezone.now() - timedelta(days=3),
        )
        Report.objects.filter(pk=second.pk).update(created_at=timezone.now() - timedelta(days=2))
        Report.objects.filter(pk=third.pk).update(created_at=timezone.now() - timedelta(days=1))
        Report.objects.filter(pk=newest.pk).update(created_at=timezone.now())

        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(
            [report.pk for report in response.context["reports"]],
            [oldest.pk, newest.pk, third.pk],
        )

    def test_a_handover_proposed_by_the_other_participant_is_the_hero(self):
        pairs = {}
        for name, state, proposer in (
            ("possible", "Possible Match", None),
            ("proposed_by_finder", "Handover Proposed", self.finder),
            ("scheduled", "Handover Scheduled", None),
            ("proposed_by_owner", "Handover Proposed", self.owner),
        ):
            lost = make_report(self.owner, "Lost", title=f"Lost {name}")
            found = make_report(self.finder, "Found", title=f"Found {name}")
            pairs[name] = make_match(lost, found, state=state, proposer=proposer)

        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard"))

        # A proposal waiting for this user's response is most urgent, then a
        # scheduled handover, then the user's own open proposal.
        self.assertEqual(response.context["hero"].pk, pairs["proposed_by_finder"].pk)
        self.assertEqual(
            [match.pk for match in response.context["other_matches"]],
            [
                pairs["scheduled"].pk,
                pairs["proposed_by_owner"].pk,
                pairs["possible"].pk,
            ],
        )
        self.assertEqual(response.context["possible_count"], 1)
        self.assertEqual(response.context["handover_count"], 3)

    def test_possible_matches_for_reserved_reports_are_hidden(self):
        busy = make_report(self.owner, "Lost", title="Busy", reserved=True)
        found = make_report(self.finder, "Found", title="Found busy")
        make_match(busy, found, state="Possible Match")

        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard"))

        self.assertIsNone(response.context["hero"])
        self.assertEqual(response.context["possible_count"], 0)


class ReportHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("history-owner@example.test")
        cls.other = make_user("history-other@example.test")

    def setUp(self):
        self.client.force_login(self.owner)

    def test_anonymous_visitors_are_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("login")))

    def test_history_only_lists_the_owners_visible_reports(self):
        mine = make_report(self.owner, title="My wallet")
        make_report(self.owner, title="Removed wallet", status="Removed")
        make_report(self.other, title="Someone else")

        response = self.client.get(reverse("reports"))

        self.assertEqual(
            [report.pk for report in response.context["page_obj"].object_list],
            [mine.pk],
        )

    def test_untrusted_search_characters_are_a_bad_request(self):
        for value in ("\u200b", "wallet\u202e"):
            with self.subTest(value=repr(value)):
                response = self.client.get(reverse("reports"), {"q": value})
                self.assertEqual(response.status_code, 400)
                self.assertIn("Remove special or invisible characters", response.content.decode())

    def test_search_matches_the_title_or_location_without_case(self):
        by_title = make_report(self.owner, title="Silver wristwatch")
        by_location = make_report(self.owner, title="Unknown item", location="Silver Hall")
        make_report(self.owner, title="Unrelated")

        response = self.client.get(reverse("reports"), {"q": "SILVER"})

        self.assertEqual(
            {report.pk for report in response.context["page_obj"].object_list},
            {by_title.pk, by_location.pk},
        )
        self.assertEqual(response.context["search"], "SILVER")

    def test_status_and_kind_filters_are_applied_independently(self):
        open_lost = make_report(self.owner, "Lost", title="Open lost")
        make_report(self.owner, "Found", title="Open found")
        returned_lost = make_report(self.owner, "Lost", title="Returned lost", status="Returned")

        response = self.client.get(reverse("reports"), {"status": "Returned", "kind": "Lost"})

        self.assertEqual(
            [report.pk for report in response.context["page_obj"].object_list],
            [returned_lost.pk],
        )
        self.assertEqual(response.context["status_filter"], "Returned")
        self.assertEqual(response.context["kind_filter"], "Lost")
        self.assertNotIn(open_lost, response.context["page_obj"].object_list)

    def test_unknown_filters_are_ignored(self):
        report = make_report(self.owner, "Lost", title="Still listed")
        response = self.client.get(reverse("reports"), {"status": "Lost", "kind": "Bag"})
        self.assertEqual(
            [item.pk for item in response.context["page_obj"].object_list], [report.pk],
        )
        self.assertEqual(response.context["status_filter"], "Lost")
        self.assertEqual(response.context["kind_filter"], "Bag")

    def test_pages_hold_ten_reports_and_fall_back_to_the_nearest_page(self):
        for index in range(11):
            make_report(self.owner, title=f"Report {index:02d}")

        first = self.client.get(reverse("reports"))
        beyond = self.client.get(reverse("reports"), {"page": "99"})
        nonsense = self.client.get(reverse("reports"), {"page": "not-a-number"})

        self.assertEqual(len(first.context["page_obj"].object_list), 10)
        self.assertEqual(beyond.context["page_obj"].number, 2)
        self.assertEqual(len(beyond.context["page_obj"].object_list), 1)
        self.assertEqual(nonsense.context["page_obj"].number, 1)


class WizardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("wizard-owner@example.test")
        cls.outsider = make_user("wizard-outsider@example.test")

    def setUp(self):
        self.client.force_login(self.owner)

    def make_draft(self, **data):
        return Draft.objects.create(owner=self.owner, data=draft_data(**data))

    def test_opening_a_new_report_creates_a_draft_and_redirects_to_it(self):
        response = self.client.get(reverse("create"))
        draft = Draft.objects.get(owner=self.owner)
        self.assertRedirects(
            response, reverse("draft", args=[draft.pk]), fetch_redirect_response=False,
        )

    def test_an_existing_draft_is_offered_for_resume(self):
        draft = Draft.objects.create(owner=self.owner, data={"title": "Saved"})
        response = self.client.get(reverse("create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "resume_draft.html")
        self.assertEqual(response.context["draft"], draft)

    def test_discarding_a_draft_needs_the_confirmation_and_its_id(self):
        draft = Draft.objects.create(owner=self.owner, data={"title": "Saved"})

        missing = self.client.post(reverse("create"), {"action": "new"})
        wrong_id = self.client.post(reverse("create"), {
            "action": "new", "confirm_discard": "yes", "discard_draft_id": draft.pk + 1,
        })

        for response in (missing, wrong_id):
            self.assertEqual(response.status_code, 200)
            self.assertIn("discard_error", response.context)
        self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())

    def test_a_confirmed_discard_removes_the_draft(self):
        draft = Draft.objects.create(owner=self.owner, data={"title": "Saved"})
        response = self.client.post(reverse("create"), {
            "action": "new",
            "confirm_discard": "yes",
            "discard_draft_id": str(draft.pk),
        })
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)
        self.assertFalse(Draft.objects.filter(pk=draft.pk).exists())

    def test_another_users_draft_is_not_found(self):
        draft = Draft.objects.create(owner=self.outsider, data={"title": "Theirs"})
        response = self.client.get(reverse("draft", args=[draft.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_draft_for_a_closed_report_is_locked(self):
        report = make_report(self.owner, status="Returned")
        draft = Draft.objects.create(owner=self.owner, report=report, data=draft_data())
        response = self.client.get(reverse("draft", args=[draft.pk]))
        self.assertRedirects(
            response, reverse("report", args=[report.pk]), fetch_redirect_response=False,
        )
        self.assertIn("Editing is locked", messages_of(response)[0])

    def test_a_draft_for_a_reserved_report_is_locked(self):
        report = make_report(self.owner, reserved=True)
        draft = Draft.objects.create(owner=self.owner, report=report, data=draft_data())
        response = self.client.get(reverse("draft", args=[draft.pk]))
        self.assertRedirects(
            response, reverse("report", args=[report.pk]), fetch_redirect_response=False,
        )

    def test_the_step_query_is_clamped_to_one_through_five(self):
        draft = self.make_draft()
        url = reverse("draft", args=[draft.pk])

        for query, expected in (("0", 1), ("-3", 1), ("not-a-number", 1), ("99", 5)):
            with self.subTest(query=query):
                response = self.client.get(f"{url}?step={query}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["step"], expected)

    def test_later_steps_redirect_back_to_the_first_unfinished_step(self):
        url = reverse("draft", args=[self.make_draft().pk])

        missing_type = Draft.objects.create(owner=self.owner, data={"answers": {}})
        missing_description = Draft.objects.create(owner=self.owner, data={
            "kind": "Lost", "title": "Bag", "category": "Bag",
            "event_date": timezone.localdate().isoformat(),
        })
        missing_location = Draft.objects.create(owner=self.owner, data={
            "kind": "Lost", "title": "Bag", "category": "Bag",
            "event_date": timezone.localdate().isoformat(),
            "description": "Blue fabric bag", "contact": "03001234567",
        })
        missing_answers = Draft.objects.create(owner=self.owner, data={
            "kind": "Lost", "title": "Bag", "category": "Bag",
            "event_date": timezone.localdate().isoformat(),
            "description": "Blue fabric bag", "contact": "03001234567",
            "location": "Library", "lat": "24.86", "lng": "67.001",
            "location_detail": "Entrance",
        })

        cases = (
            (missing_type, 5, "?step=1"),
            (missing_description, 3, "?step=2"),
            (missing_location, 4, "?step=3"),
            (missing_answers, 5, "?step=4"),
        )
        for draft, step, suffix in cases:
            with self.subTest(draft=draft.pk, step=step):
                path = reverse("draft", args=[draft.pk])
                response = self.client.get(f"{path}?step={step}")
                self.assertRedirects(
                    response, f"{path}{suffix}", fetch_redirect_response=False,
                )
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_a_stored_date_the_wizard_cannot_parse_renders_a_blank_step(self):
        draft = self.make_draft(event_date="not-a-date")
        response = self.client.get(f"{reverse('draft', args=[draft.pk])}?step=1")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["form"].initial["event_date"])

    def test_saving_a_step_advances_and_keeps_the_answers(self):
        draft = self.make_draft()
        url = reverse("draft", args=[draft.pk])
        response = self.client.post(f"{url}?step=1", {
            "kind": "Lost",
            "title": "Blue backpack",
            "category": "Bag",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })
        self.assertRedirects(response, f"{url}?step=2", fetch_redirect_response=False)
        draft.refresh_from_db()
        self.assertEqual(draft.data["event_date"], timezone.localdate().isoformat())
        self.assertIn("answers", draft.data)

    def test_changing_the_category_drops_the_answers_for_the_old_one(self):
        draft = self.make_draft()
        url = reverse("draft", args=[draft.pk])
        self.client.post(f"{url}?step=1", {
            "kind": "Lost",
            "title": "Blue backpack",
            "category": "Keys",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })
        draft.refresh_from_db()
        self.assertEqual(draft.data["category"], "Keys")
        self.assertNotIn("answers", draft.data)

    def test_reviewing_and_publishing_creates_the_report(self):
        draft = self.make_draft()
        url = reverse("draft", args=[draft.pk])
        response = self.client.post(f"{url}?step=5", {})
        report = Report.objects.get(owner=self.owner)
        self.assertRedirects(
            response,
            f"{reverse('dashboard')}?new={report.pk}#report-{report.pk}",
            fetch_redirect_response=False,
        )
        self.assertEqual(report.title, "Blue backpack")
        self.assertFalse(Draft.objects.filter(pk=draft.pk).exists())

    def test_a_refresh_on_the_matching_step_rebuilds_the_form_without_saving(self):
        draft = self.make_draft()
        url = reverse("draft", args=[draft.pk])
        response = self.client.post(f"{url}?step=4", {
            "action": "refresh",
            **{key: value for key, value in draft.data["answers"].items()},
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 4)
        self.assertIsNotNone(response.context["form"])


class ReportFoundTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("found-owner@example.test")
        cls.finder = make_user("found-finder@example.test")

    def setUp(self):
        self.report = make_report(self.owner, "Lost", title="Blue backpack")

    def scan(self):
        return self.client.get(reverse("report-found", args=[self.report.public_id]))

    def test_anonymous_visitors_are_sent_to_login(self):
        response = self.scan()
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('report-found', args=[self.report.public_id])}",
            fetch_redirect_response=False,
        )

    def test_the_owner_is_told_to_hand_the_code_to_a_finder(self):
        self.client.force_login(self.owner)
        response = self.scan()
        self.assertRedirects(
            response, reverse("report", args=[self.report.pk]),
            fetch_redirect_response=False,
        )
        self.assertIn("only a finder scans it", messages_of(response)[0])

    def test_a_closed_or_reserved_report_shows_a_closed_notice(self):
        for change in ({"status": "Returned"}, {"reserved": True}):
            with self.subTest(change=change):
                report = make_report(
                    self.owner, "Lost", title=f"Closed {change}", **change,
                )
                self.client.force_login(self.finder)
                response = self.client.get(
                    reverse("report-found", args=[report.public_id]),
                )
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "closed_notice.html")

    def test_a_finder_starts_a_found_draft_with_only_the_public_hints(self):
        self.client.force_login(self.finder)
        response = self.scan()

        draft = Draft.objects.get(owner=self.finder)
        self.assertRedirects(
            response,
            f"{reverse('draft', args=[draft.pk])}?step=3",
            fetch_redirect_response=False,
        )
        self.assertEqual(draft.data["kind"], "Found")
        self.assertEqual(draft.data["category"], self.report.category)
        self.assertEqual(draft.data["title"], self.report.title)
        self.assertEqual(draft.data["location"], self.report.location)
        self.assertEqual(draft.data["event_date"], timezone.localdate().isoformat())
        for key in ("description", "location_detail", "contact", "answers", "lat", "lng"):
            self.assertNotIn(key, draft.data)

    def test_an_existing_draft_is_resumed_and_cleaned(self):
        draft = Draft.objects.create(owner=self.finder, data={
            "description": "old", "contact": "03001234567", "lat": "24.86",
        })
        self.client.force_login(self.finder)
        response = self.scan()
        draft.refresh_from_db()
        self.assertRedirects(
            response,
            f"{reverse('draft', args=[draft.pk])}?step=3",
            fetch_redirect_response=False,
        )
        self.assertNotIn("description", draft.data)
        self.assertNotIn("contact", draft.data)
        self.assertNotIn("lat", draft.data)

    def test_an_unknown_public_id_is_not_found(self):
        self.client.force_login(self.finder)
        response = self.client.get(reverse("report-found", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)


class ManagementViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = make_user("management-staff@example.test", staff=True)
        cls.owner = make_user("management-owner@example.test")

    def setUp(self):
        self.report = make_report(self.owner, "Lost", title="Reported item")

    def test_anonymous_visitors_are_sent_to_login(self):
        response = self.client.get(reverse("management"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("login")))

    def test_non_staff_members_are_forbidden(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("management")).status_code, 403)

    def test_staff_see_every_visible_report_newest_first(self):
        older = make_report(self.owner, "Lost", title="Older")
        removed = make_report(self.owner, "Lost", title="Removed", status="Removed")
        self.client.force_login(self.staff)
        response = self.client.get(reverse("management"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [report.pk for report in response.context["reports"]],
            [older.pk, self.report.pk],
        )
        self.assertNotIn(removed, response.context["reports"])

    def test_an_invalid_report_id_is_a_bad_request(self):
        self.client.force_login(self.staff)
        for value in ("", "abc", "0", "-1", "1.5", "9223372036854775808"):
            with self.subTest(value=value):
                response = self.client.post(reverse("management"), {
                    "report": value, "action": "close",
                })
                self.assertEqual(response.status_code, 400)
                self.assertIn("Choose a valid report", response.content.decode())

    def test_a_missing_report_is_not_found(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("management"), {
            "report": self.report.pk + 100, "action": "close",
        })
        self.assertEqual(response.status_code, 404)

    def test_staff_can_close_a_report(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("management"), {
            "report": self.report.pk, "action": "close",
        })
        self.assertRedirects(
            response, reverse("management"), fetch_redirect_response=False,
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "Closed")
        self.assertIn("Report updated", messages_of(response)[0])

    def test_an_invalid_action_leaves_the_report_alone(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("management"), {
            "report": self.report.pk, "action": "delete",
        })
        self.assertRedirects(
            response, reverse("management"), fetch_redirect_response=False,
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "Open")
        self.assertIn("Moderator access required", messages_of(response)[0])


class QRLabelPublicTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from core.qr_labels import new_label_token, token_digest

        cls.owner = make_user("public-label@example.test")
        cls.token = new_label_token()
        cls.label = QRLabel.objects.create(
            owner=cls.owner,
            item_name="Blue backpack",
            contact_phone="03001234567",
            token_hash=token_digest(cls.token),
            expires_at=timezone.now() + timedelta(days=1),
            qr_image="",
        )

    def test_only_the_hash_is_stored(self):
        self.assertNotEqual(self.label.token_hash, self.token)
        self.assertEqual(len(self.label.token_hash), 64)

    def test_an_active_label_is_served_with_private_headers(self):
        response = self.client.get(reverse("qr-label-public", args=[self.token]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["active"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Referrer-Policy"], "no-referrer")

    def test_an_expired_label_is_served_as_inactive(self):
        QRLabel.objects.filter(pk=self.label.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        response = self.client.get(reverse("qr-label-public", args=[self.token]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["active"])

    def test_a_revoked_label_is_served_as_inactive(self):
        QRLabel.objects.filter(pk=self.label.pk).update(revoked=True)
        response = self.client.get(reverse("qr-label-public", args=[self.token]))
        self.assertFalse(response.context["active"])

    def test_a_wrong_token_is_not_found(self):
        response = self.client.get(reverse("qr-label-public", args=["not-the-token"]))
        self.assertEqual(response.status_code, 404)


class PhotoViewTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("photo-owner@example.test")
        cls.finder = make_user("photo-finder@example.test")
        cls.outsider = make_user("photo-outsider@example.test")

    def make_photo_report(self, owner=None, data=b"photo-bytes"):
        report = make_report(owner or self.owner, title="Photo item")
        report.photo.save("item.jpg", ContentFile(data), save=True)
        return report

    def test_the_owner_can_read_their_report_photo(self):
        report = self.make_photo_report()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("report-photo", args=[report.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        response.close()

    def test_a_match_participant_can_read_the_other_report_photo(self):
        lost = self.make_photo_report()
        found = make_report(self.finder, "Found", title="Found item")
        make_match(lost, found)
        self.client.force_login(self.finder)
        response = self.client.get(reverse("report-photo", args=[lost.pk]))
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_an_outsider_cannot_read_a_report_photo(self):
        report = self.make_photo_report()
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("report-photo", args=[report.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_report_without_a_photo_is_not_found(self):
        report = make_report(self.owner, title="No photo")
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.get(reverse("report-photo", args=[report.pk])).status_code, 404,
        )

    def test_a_photo_missing_from_storage_is_not_found(self):
        report = self.make_photo_report()
        report.photo.storage.delete(report.photo.name)
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.get(reverse("report-photo", args=[report.pk])).status_code, 404,
        )

    def test_only_the_draft_owner_can_read_a_draft_photo(self):
        draft = Draft.objects.create(owner=self.owner)
        draft.photo.save("draft.jpg", ContentFile(b"draft-bytes"), save=True)

        self.client.force_login(self.owner)
        response = self.client.get(reverse("draft-photo", args=[draft.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        response.close()

        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(reverse("draft-photo", args=[draft.pk])).status_code, 404,
        )

    def test_a_draft_without_a_photo_is_not_found(self):
        draft = Draft.objects.create(owner=self.owner)
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.get(reverse("draft-photo", args=[draft.pk])).status_code, 404,
        )

    def test_a_draft_photo_missing_from_storage_is_not_found(self):
        draft = Draft.objects.create(owner=self.owner)
        draft.photo.save("draft.jpg", ContentFile(b"draft-bytes"), save=True)
        draft.photo.storage.delete(draft.photo.name)
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.get(reverse("draft-photo", args=[draft.pk])).status_code, 404,
        )


class EditReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("edit-owner@example.test")
        cls.outsider = make_user("edit-outsider@example.test")

    def setUp(self):
        self.client.force_login(self.owner)
        self.report = make_report(self.owner, title="Editable")

    def test_editing_opens_a_draft_with_the_report_values(self):
        response = self.client.post(reverse("edit", args=[self.report.pk]))
        draft = Draft.objects.get(owner=self.owner, report=self.report)
        self.assertRedirects(
            response, reverse("draft", args=[draft.pk]), fetch_redirect_response=False,
        )
        self.assertEqual(draft.data["title"], "Editable")
        self.assertEqual(draft.data["event_date"], self.report.event_date.isoformat())
        self.assertEqual(draft.data["lat"], "24.86070000")
        self.assertEqual(draft.data["lng"], "67.00110000")
        self.assertEqual(draft.data["answers"], self.report.answers)
        self.assertNotIn("photo", draft.data)

    def test_editing_twice_reuses_the_same_draft(self):
        self.client.post(reverse("edit", args=[self.report.pk]))
        first = Draft.objects.get(owner=self.owner, report=self.report)
        self.client.post(reverse("edit", args=[self.report.pk]))
        self.assertEqual(
            Draft.objects.filter(owner=self.owner, report=self.report).count(), 1,
        )
        self.assertEqual(
            Draft.objects.get(owner=self.owner, report=self.report).pk, first.pk,
        )

    def test_a_closed_or_reserved_report_is_locked(self):
        for change in ({"status": "Returned"}, {"reserved": True}):
            with self.subTest(change=change):
                report = make_report(self.owner, title=f"Locked {change}", **change)
                response = self.client.post(reverse("edit", args=[report.pk]))
                self.assertRedirects(
                    response, reverse("report", args=[report.pk]),
                    fetch_redirect_response=False,
                )
                self.assertFalse(Draft.objects.filter(report=report).exists())
                self.assertIn("locked", messages_of(response)[0])

    def test_editing_requires_post_and_ownership(self):
        self.assertEqual(
            self.client.get(reverse("edit", args=[self.report.pk])).status_code, 405,
        )
        other = make_report(self.outsider, title="Theirs")
        self.assertEqual(
            self.client.post(reverse("edit", args=[other.pk])).status_code, 404,
        )


class ReportQRImageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("report-qr@example.test")

    def test_a_report_qr_is_a_public_png(self):
        report = make_report(self.owner)
        response = self.client.get(reverse("report-qr", args=[report.public_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Content-Disposition"].split(";")[0], "inline")

    def test_the_download_parameter_marks_the_qr_as_an_attachment(self):
        report = make_report(self.owner)
        response = self.client.get(
            reverse("report-qr", args=[report.public_id]) + "?download=1",
        )
        self.assertEqual(response["Content-Disposition"].split(";")[0], "attachment")
        self.assertIn("report-qr.png", response["Content-Disposition"])

    def test_an_unknown_report_is_not_found(self):
        response = self.client.get(reverse("report-qr", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)


class QRLabelViewTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("label-owner@example.test")
        cls.outsider = make_user("label-outsider@example.test")

    def setUp(self):
        self.client.force_login(self.owner)

    def make_label(self, owner=None, **overrides):
        from core.qr_labels import new_label_token, token_digest

        fields = {
            "owner": owner or self.owner,
            "item_name": "Blue backpack",
            "contact_phone": "03001234567",
            "token_hash": token_digest(new_label_token()),
            "expires_at": timezone.now() + timedelta(days=1),
            "qr_image": "",
        }
        fields.update(overrides)
        return QRLabel.objects.create(**fields)

    def test_the_page_only_lists_the_owners_labels(self):
        mine = self.make_label()
        self.make_label(owner=self.outsider)
        response = self.client.get(reverse("qr-labels"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([label.pk for label in response.context["labels"]], [mine.pk])

    def test_a_valid_form_creates_a_label_with_a_hashed_token_and_qr_image(self):
        response = self.client.post(reverse("qr-labels"), {
            "item_name": "Blue backpack",
            "contact_phone": "03001234567",
        })
        self.assertRedirects(
            response, reverse("qr-labels"), fetch_redirect_response=False,
        )
        label = QRLabel.objects.get(owner=self.owner)
        self.assertEqual(len(label.token_hash), 64)
        self.assertTrue(all(character in "0123456789abcdef" for character in label.token_hash))
        self.assertTrue(label.qr_image.name.endswith(".png"))
        self.assertTrue(label.qr_image.storage.exists(label.qr_image.name))
        self.assertTrue(label.is_active)
        self.assertGreater(label.expires_at, timezone.now() + timedelta(days=150))

    def test_an_invalid_form_does_not_create_a_label(self):
        response = self.client.post(reverse("qr-labels"), {
            "item_name": "Bag",
            "contact_phone": "123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(QRLabel.objects.filter(owner=self.owner).exists())

    def test_reactivating_makes_the_printed_code_work_again(self):
        label = self.make_label(
            expires_at=timezone.now() - timedelta(days=1), revoked=True,
        )
        response = self.client.post(reverse("qr-label-reactivate", args=[label.pk]))
        self.assertRedirects(
            response, reverse("qr-labels"), fetch_redirect_response=False,
        )
        label.refresh_from_db()
        self.assertFalse(label.revoked)
        self.assertTrue(label.is_active)

    def test_deactivating_revokes_the_label(self):
        label = self.make_label()
        response = self.client.post(reverse("qr-label-deactivate", args=[label.pk]))
        self.assertRedirects(
            response, reverse("qr-labels"), fetch_redirect_response=False,
        )
        label.refresh_from_db()
        self.assertTrue(label.revoked)
        self.assertFalse(label.is_active)

    def test_both_label_actions_require_post(self):
        label = self.make_label()
        self.assertEqual(
            self.client.get(reverse("qr-label-reactivate", args=[label.pk])).status_code, 405,
        )
        self.assertEqual(
            self.client.get(reverse("qr-label-deactivate", args=[label.pk])).status_code, 405,
        )

    def test_another_users_label_cannot_be_changed(self):
        label = self.make_label(owner=self.outsider)
        self.assertEqual(
            self.client.post(reverse("qr-label-reactivate", args=[label.pk])).status_code, 404,
        )
        self.assertEqual(
            self.client.post(reverse("qr-label-deactivate", args=[label.pk])).status_code, 404,
        )

    def test_the_owner_can_download_the_qr_image(self):
        label = self.make_label()
        label.qr_image.save("label.png", ContentFile(b"png-bytes"), save=True)

        inline = self.client.get(reverse("qr-label-image", args=[label.pk]))
        download = self.client.get(reverse("qr-label-image", args=[label.pk]) + "?download=1")

        self.assertEqual(inline.status_code, 200)
        self.assertEqual(inline["Content-Type"], "image/png")
        self.assertEqual(inline["Cache-Control"], "private, no-store")
        self.assertEqual(inline["Content-Disposition"].split(";")[0], "inline")
        self.assertEqual(download["Content-Disposition"].split(";")[0], "attachment")
        self.assertIn(f"item-qr-{label.pk}.png", download["Content-Disposition"])

    def test_a_label_image_is_private(self):
        label = self.make_label()
        label.qr_image.save("label.png", ContentFile(b"png-bytes"), save=True)

        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(reverse("qr-label-image", args=[label.pk])).status_code, 404,
        )

    def test_a_missing_qr_image_is_not_found(self):
        label = self.make_label()
        self.assertEqual(
            self.client.get(reverse("qr-label-image", args=[label.pk])).status_code, 404,
        )

    def test_a_qr_image_missing_from_storage_is_not_found(self):
        label = self.make_label()
        label.qr_image.save("label.png", ContentFile(b"png-bytes"), save=True)
        label.qr_image.storage.delete(label.qr_image.name)
        self.assertEqual(
            self.client.get(reverse("qr-label-image", args=[label.pk])).status_code, 404,
        )


class MatchDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("detail-owner@example.test")
        cls.finder = make_user("detail-finder@example.test")
        cls.outsider = make_user("detail-outsider@example.test")

    def setUp(self):
        self.lost = make_report(self.owner, "Lost", title="Blue backpack")
        self.found = make_report(self.finder, "Found", title="Found blue backpack")
        self.match = make_match(self.lost, self.found)

    def test_outsiders_cannot_open_a_match(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_participant_can_open_the_match(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["form"])
        self.assertFalse(response.context["contacts"])
        self.assertFalse(response.context["can_restore"])

    def test_contacts_appear_once_a_handover_is_scheduled_or_returned(self):
        for state in ("Handover Scheduled", "Returned"):
            with self.subTest(state=state):
                match = make_match(
                    make_report(self.owner, title=f"Lost {state}"),
                    make_report(self.finder, "Found", title=f"Found {state}"),
                    state=state,
                )
                self.client.force_login(self.owner)
                response = self.client.get(reverse("match", args=[match.pk]))
                self.assertTrue(response.context["contacts"])

    def test_an_invalid_proposal_rerenders_without_reserving_reports(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("match", args=[self.match.pk]), {
            "action": "propose",
        })
        self.assertEqual(response.status_code, 200)
        self.match.refresh_from_db()
        self.lost.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")
        self.assertFalse(self.lost.reserved)

    def test_a_valid_proposal_reserves_both_reports(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("match", args=[self.match.pk]), {
            "action": "propose",
            "meeting_place": "NED Security Office",
            "meeting_at": meeting_field_value(),
        })
        self.assertRedirects(
            response, reverse("match", args=[self.match.pk]),
            fetch_redirect_response=False,
        )
        self.match.refresh_from_db()
        self.lost.refresh_from_db()
        self.found.refresh_from_db()
        self.assertEqual(self.match.state, "Handover Proposed")
        self.assertTrue(self.lost.reserved)
        self.assertTrue(self.found.reserved)

    def test_rejecting_and_restoring_are_available_to_the_dismisser(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("match", args=[self.match.pk]), {
            "action": "propose",
            "meeting_place": "NED Security Office",
            "meeting_at": meeting_field_value(),
        })

        self.client.force_login(self.finder)
        rejected = self.client.post(
            reverse("match", args=[self.match.pk]), {"action": "reject"},
        )
        self.assertRedirects(
            rejected, reverse("match", args=[self.match.pk]),
            fetch_redirect_response=False,
        )
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Rejected")
        self.assertTrue(self.match.rejected_by_id == self.finder.pk)

        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertTrue(page.context["can_restore"])

        restored = self.client.post(
            reverse("match", args=[self.match.pk]), {"action": "restore"},
        )
        self.assertRedirects(
            restored, reverse("match", args=[self.match.pk]),
            fetch_redirect_response=False,
        )
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")

    def test_an_action_outside_the_state_shows_an_error_message(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("match", args=[self.match.pk]), {"action": "returned"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("unavailable in this state", messages_of(response)[0])
