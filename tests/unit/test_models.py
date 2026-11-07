"""Unit tests for ``core.models``: derived values, defaults, and constraints."""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from core.models import Draft, Event, Match, QRLabel, Report, User
from tests.support import make_match, make_report, make_user


class UserModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("models-user@example.test")

    def test_visible_report_count_ignores_removed_reports(self):
        for status in ("Open", "Returned", "Closed", "Removed"):
            make_report(self.user, status=status, title=f"{status} item")
        self.assertEqual(self.user.visible_report_count, 3)

    def test_visible_report_count_is_scoped_to_the_owner(self):
        make_report(make_user("models-other@example.test"), title="Other item")
        self.assertEqual(self.user.visible_report_count, 0)

    def test_username_and_email_accept_the_same_length(self):
        # Login uses the email as the username, so both columns must agree.
        self.assertEqual(User._meta.get_field("username").max_length, 254)
        self.assertEqual(User._meta.get_field("email").max_length, 254)


class ReportModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("models-report@example.test")

    def test_display_id_prefixes_the_kind_and_zero_pads(self):
        lost = make_report(self.owner, "Lost", title="Lost wallet")
        found = make_report(self.owner, "Found", title="Found wallet")
        self.assertEqual(lost.display_id, f"LFD-{lost.pk:03d}")
        self.assertEqual(found.display_id, f"FND-{found.pk:03d}")

    def test_display_id_keeps_numbers_longer_than_three_digits(self):
        report = make_report(self.owner, title="Numbered")
        # The property only formats the number, so a larger in-memory id is enough.
        report.pk = 1234
        self.assertEqual(report.display_id, "LFD-1234")

    def test_str_includes_kind_number_and_title(self):
        report = make_report(self.owner, "Lost", title="Blue backpack")
        self.assertEqual(str(report), f"Lost #{report.pk}: Blue backpack")

    def test_new_report_defaults_to_open_and_not_reserved(self):
        report = make_report(self.owner)
        self.assertEqual(report.status, "Open")
        self.assertFalse(report.reserved)
        self.assertEqual(report.answers["colour"], "Blue")

    def test_deleting_an_owner_with_reports_is_protected(self):
        make_report(make_user("models-protected@example.test"))
        owner = User.objects.get(email="models-protected@example.test")
        with self.assertRaises(ProtectedError):
            owner.delete()

    def test_deleting_a_report_cascades_to_its_draft(self):
        report = make_report(self.owner, title="Draft owner")
        draft = Draft.objects.create(owner=self.owner, report=report)
        report.delete()
        self.assertFalse(Draft.objects.filter(pk=draft.pk).exists())

    def test_deleting_a_report_is_protected_by_its_events(self):
        report = make_report(self.owner, title="Audited")
        Event.objects.create(report=report, actor=self.owner, text="Report created")
        with self.assertRaises(ProtectedError):
            report.delete()


class DraftModelTests(TestCase):
    def test_data_defaults_to_an_empty_mapping(self):
        draft = Draft.objects.create(owner=make_user("models-draft@example.test"))
        draft.refresh_from_db()
        self.assertEqual(draft.data, {})

    def test_updated_at_changes_when_the_draft_is_saved(self):
        draft = Draft.objects.create(
            owner=make_user("models-touch@example.test"), data={"title": "One"},
        )
        original = draft.updated_at
        Draft.objects.filter(pk=draft.pk).update(
            updated_at=original - timedelta(days=1),
        )
        draft.refresh_from_db()
        draft.data = {"title": "Two"}
        draft.save()
        draft.refresh_from_db()
        self.assertGreater(draft.updated_at, original - timedelta(hours=1))


class QRLabelModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("models-label@example.test")

    def make_label(self, **overrides):
        fields = {
            "owner": self.owner,
            "item_name": "Blue backpack",
            "contact_phone": "03001234567",
            "token_hash": "a" * 64,
            "expires_at": timezone.now() + timedelta(days=1),
        }
        fields.update(overrides)
        return QRLabel.objects.create(**fields)

    def test_a_future_unrevoked_label_is_active(self):
        self.assertTrue(self.make_label().is_active)

    def test_an_expired_label_is_inactive(self):
        self.assertFalse(self.make_label(expires_at=timezone.now() - timedelta(seconds=1)).is_active)

    def test_a_revoked_label_is_inactive_even_before_expiry(self):
        self.assertFalse(self.make_label(revoked=True).is_active)

    def test_labels_are_ordered_newest_first(self):
        first = self.make_label(token_hash="b" * 64)
        second = self.make_label(token_hash="c" * 64)
        QRLabel.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(list(self.owner.qr_labels.all()), [second, first])


class MatchModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("models-match-owner@example.test")
        cls.finder = make_user("models-match-finder@example.test")
        cls.lost = make_report(cls.owner, "Lost")
        cls.found = make_report(cls.finder, "Found")

    def test_a_pair_can_only_have_one_match(self):
        make_match(self.lost, self.found)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_match(self.lost, self.found)

    def test_the_score_cannot_exceed_one_hundred(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_match(self.lost, self.found, score=101)

    def test_a_new_match_starts_as_a_possible_match(self):
        match = make_match(self.lost, self.found)
        self.assertEqual(match.state, "Possible Match")
        self.assertIsNone(match.proposer)

    def test_str_uses_both_display_ids_and_the_state(self):
        match = make_match(self.lost, self.found)
        self.assertEqual(
            str(match), f"{self.lost.display_id} ↔ {self.found.display_id} (Possible Match)",
        )

    def test_event_str_names_the_action_and_report(self):
        event = Event.objects.create(report=self.lost, actor=self.owner, text="Report created")
        self.assertEqual(str(event), f"Report created — {self.lost.display_id}")
