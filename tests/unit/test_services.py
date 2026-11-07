"""Unit tests for ``core.services``: scoring, publishing, and the handover state machine."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from core.models import Draft, Event, Match, Report
from core.services import (
    get_or_create_draft,
    haversine_km,
    location_score,
    moderate,
    publish,
    recalculate,
    score,
    transition,
    validated,
)
from tests.support import (
    BAG_ANSWERS,
    TempMediaMixin,
    draft_data,
    make_match,
    make_report,
    make_user,
    meeting,
)

LATITUDE_KM = 111.19492664455873


class DraftDataTests(TestCase):
    def test_a_complete_draft_is_cleaned_into_report_fields(self):
        result = validated(draft_data(event_date="2026-01-15"))
        self.assertEqual(result["event_date"], date(2026, 1, 15))
        self.assertEqual(result["kind"], "Lost")
        self.assertEqual(result["title"], "Blue backpack")
        self.assertEqual(result["answers"]["colour"], "Blue")
        self.assertEqual(result["lat"], Decimal("24.86"))
        self.assertNotIn("photo", result)
        self.assertNotIn("remove_photo", result)

    def test_unknown_draft_keys_are_dropped(self):
        result = validated(draft_data(unexpected="ignored"))
        self.assertNotIn("unexpected", result)

    def test_non_mapping_draft_data_is_a_normal_validation_error(self):
        for value in ([], "text", None, 5):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validated(value)

    def test_non_mapping_answers_are_a_normal_validation_error(self):
        for value in ([], "text", 5):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validated(draft_data(answers=value))

    def test_a_missing_step_is_reported_as_incomplete(self):
        with self.assertRaisesMessage(
            ValidationError, "Complete and check every step before submitting.",
        ):
            validated({"kind": "Lost", "title": "Blue backpack"})

    def test_a_stored_date_that_is_not_iso_is_rejected_clearly(self):
        for value in ("15/01/2026", 20260115, "2026-1-5"):
            with self.subTest(value=value):
                with self.assertRaisesMessage(
                    ValidationError, "Invalid event date stored in the draft.",
                ):
                    validated(draft_data(event_date=value))

    def test_a_public_field_with_private_data_fails_validation(self):
        with self.assertRaisesMessage(
            ValidationError, "Complete and check every step before submitting.",
        ):
            validated(draft_data(title="Call 03001234567"))


class DistanceTests(SimpleTestCase):
    def point(self, lat, lng):
        return SimpleNamespace(lat=lat, lng=lng)

    def test_the_same_point_is_zero_kilometres(self):
        self.assertEqual(haversine_km(24.86, 67.0, 24.86, 67.0), 0)

    def test_one_degree_of_latitude_is_about_111_kilometres(self):
        self.assertAlmostEqual(haversine_km(0, 0, 1, 0), LATITUDE_KM, places=1)

    def test_distance_is_symmetric(self):
        forward = haversine_km(24.86, 67.0, 24.9, 67.1)
        backward = haversine_km(24.9, 67.1, 24.86, 67.0)
        self.assertAlmostEqual(forward, backward, places=9)

    def test_location_score_steps_down_with_distance(self):
        base = self.point(Decimal("24.86"), Decimal("67.0"))
        for km, expected in ((0.4, 20), (0.6, 15), (1.2, 10), (2.5, 5), (6, 0)):
            with self.subTest(km=km):
                other = self.point(
                    Decimal(str(24.86 + km / LATITUDE_KM)), Decimal("67.0"),
                )
                self.assertEqual(location_score(base, other), expected)

    def test_missing_coordinates_score_zero(self):
        left = self.point(None, Decimal("67.0"))
        right = self.point(Decimal("24.86"), Decimal("67.0"))
        self.assertEqual(location_score(left, right), 0)
        self.assertEqual(location_score(right, left), 0)


class ScoreTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("score-owner@example.test")
        cls.finder = make_user("score-finder@example.test")
        cls.lost = make_report(cls.owner, "Lost", title="Blue backpack")
        cls.found = make_report(cls.finder, "Found", title="Blue backpack")

    def test_identical_reports_score_one_hundred(self):
        value, breakdown = score(self.lost, self.found)
        self.assertEqual(value, 100)
        self.assertEqual(breakdown, {
            "Category": 20,
            "Location": 20,
            "Date": 15,
            "Description": 15,
            "Private": 30,
        })

    def test_reports_from_the_same_owner_never_match(self):
        other = make_report(self.owner, "Found", title="My own found item")
        self.assertIsNone(score(self.lost, other))

    def test_different_categories_never_match(self):
        other = make_report(self.finder, "Found", category="Keys", title="Keys")
        self.assertIsNone(score(self.lost, other))

    def test_the_kinds_must_be_lost_and_found(self):
        self.assertIsNone(score(make_report(self.owner, "Found"), self.found))
        self.assertIsNone(score(self.lost, make_report(self.finder, "Lost")))

    def test_a_report_that_is_no_longer_open_never_matches(self):
        self.assertIsNone(score(self.lost, make_report(self.finder, "Found", status="Returned")))

    def test_two_private_answers_must_agree(self):
        # Everything public matches, but only the colour agrees privately.
        close = make_report(self.finder, "Found", answers={"colour": "Blue"})
        self.assertIsNone(score(self.lost, close))

    def test_a_pair_below_the_threshold_never_matches(self):
        far = make_report(
            self.finder, "Found",
            title="Red handbag",
            answers={"colour": "Red", "kind": "Handbag", "material": "Leather",
                     "pockets": "1", "mark": "Scratch"},
            description="Red leather handbag with a broken strap",
            location="Clifton",
            lat="24.81",
            lng="67.03",
            event_date=timezone.localdate() + timedelta(days=40),
        )
        self.assertIsNone(score(self.lost, far))

    def test_stopwords_do_not_change_the_description_score(self):
        left = make_report(self.owner, "Lost", description="lost blue bag near library")
        right = make_report(self.finder, "Found", description="found blue bag from library")
        result = score(left, right)
        self.assertIsNotNone(result)
        self.assertEqual(result[1]["Description"], 15)

    def test_bank_cards_are_compared_as_an_unordered_set(self):
        answers = {
            "colour": "Black", "material": "Leather", "contents": [], "logo": "No",
            "mark": "None", "bank_count": 2,
            "bank_1_issuer": "HBL", "bank_1_suffix": "1111222233334444",
            "bank_2_issuer": "Other", "bank_2_other": "NayaPay",
            "bank_2_suffix": "5555666677778888",
        }
        reversed_answers = {
            **answers,
            "bank_1_issuer": "Other", "bank_1_other": "NayaPay",
            "bank_1_suffix": "5555666677778888",
            "bank_2_issuer": "HBL", "bank_2_suffix": "1111222233334444",
        }
        left = make_report(self.owner, "Lost", category="Wallet / Purse", answers=answers)
        right = make_report(self.finder, "Found", category="Wallet / Purse", answers=reversed_answers)
        result = score(left, right)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 100)

    def test_shape_only_answers_are_excluded_from_evidence(self):
        left = make_report(self.owner, "Lost", category="Wallet / Purse", answers={
            "colour": "Black", "material": "Leather", "contents": ["CNIC"],
            "logo": "No", "bank_count": 1, "mark": "None",
        })
        right = make_report(self.finder, "Found", category="Wallet / Purse", answers={
            "colour": "Black", "material": "Leather", "contents": [],
            "logo": "Yes", "bank_count": 3, "mark": "None",
        })
        result = score(left, right)
        self.assertIsNotNone(result)
        self.assertEqual(result[1]["Private"], 30)


class DraftServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("draft-service@example.test")

    def test_the_first_call_creates_a_draft(self):
        draft, created = get_or_create_draft(self.user)
        self.assertTrue(created)
        self.assertEqual(draft.owner, self.user)
        self.assertIsNone(draft.report)

    def test_a_second_call_reuses_the_active_draft(self):
        first, _ = get_or_create_draft(self.user)
        second, created = get_or_create_draft(self.user)
        self.assertFalse(created)
        self.assertEqual(second.pk, first.pk)

    def test_an_edit_draft_is_separate_from_the_new_report_draft(self):
        report = make_report(self.user)
        active, _ = get_or_create_draft(self.user)
        edit, created = get_or_create_draft(self.user, report=report)
        self.assertTrue(created)
        self.assertEqual(edit.report, report)
        self.assertNotEqual(edit.pk, active.pk)
        self.assertEqual(get_or_create_draft(self.user)[0].pk, active.pk)

    def test_the_most_recently_updated_draft_wins(self):
        older = Draft.objects.create(owner=self.user, data={"title": "Older"})
        Draft.objects.create(owner=self.user, data={"title": "Newer"})
        Draft.objects.filter(pk=older.pk).update(
            updated_at=timezone.now() + timedelta(minutes=1),
        )
        picked, _ = get_or_create_draft(self.user)
        self.assertEqual(picked.pk, older.pk)


class PublishTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("publish-owner@example.test")
        cls.finder = make_user("publish-finder@example.test")

    def test_publishing_creates_a_report_event_and_consumes_the_draft(self):
        draft = Draft.objects.create(owner=self.owner, data=draft_data())
        report = publish(draft, self.owner)
        self.assertEqual(report.owner, self.owner)
        self.assertEqual(report.title, "Blue backpack")
        self.assertEqual(report.status, "Open")
        self.assertFalse(Draft.objects.filter(pk=draft.pk).exists())
        self.assertTrue(Event.objects.filter(report=report, text="Report created").exists())

    def test_publishing_an_edit_updates_in_place(self):
        report = make_report(self.owner)
        draft = Draft.objects.create(
            owner=self.owner, report=report, data=draft_data(title="Blue backpack updated"),
        )
        updated = publish(draft, self.owner)
        self.assertEqual(updated.pk, report.pk)
        self.assertEqual(updated.title, "Blue backpack updated")
        self.assertEqual(Report.objects.filter(owner=self.owner).count(), 1)
        self.assertTrue(Event.objects.filter(report=report, text="Report updated").exists())

    def test_a_reserved_report_cannot_be_republished(self):
        report = make_report(self.owner, reserved=True)
        draft = Draft.objects.create(owner=self.owner, report=report, data=draft_data())
        with self.assertRaisesMessage(ValidationError, "Editing is locked"):
            publish(draft, self.owner)

    def test_a_closed_report_cannot_be_republished(self):
        report = make_report(self.owner, status="Returned")
        draft = Draft.objects.create(owner=self.owner, report=report, data=draft_data())
        with self.assertRaisesMessage(ValidationError, "Editing is locked"):
            publish(draft, self.owner)

    def test_a_draft_that_was_already_submitted_is_reported(self):
        draft = Draft.objects.create(owner=self.owner, data=draft_data())
        draft.delete()
        with self.assertRaisesMessage(ValidationError, "already been submitted"):
            publish(draft, self.owner)

    def test_publishing_creates_a_match_for_the_opposite_report(self):
        found = make_report(self.finder, "Found", title="Found blue backpack")
        draft = Draft.objects.create(owner=self.owner, data=draft_data())
        report = publish(draft, self.owner)
        match = Match.objects.get(lost=report, found=found)
        self.assertEqual(match.score, score(report, found)[0])

    def test_removing_a_photo_clears_the_report_photo(self):
        report = make_report(self.owner, photo="report_photos/old.jpg")
        draft = Draft.objects.create(
            owner=self.owner, report=report,
            data=draft_data(remove_photo=True),
        )

        class MemoryStorage:
            def delete(self, name):
                pass

        publish(draft, self.owner)
        report.refresh_from_db()
        self.assertFalse(report.photo.name)


class PublishPhotoTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("publish-photo@example.test")

    def test_a_photo_uploaded_to_the_draft_follows_the_report(self):
        draft = Draft.objects.create(owner=self.owner, data=draft_data())
        draft.photo.save("item-photo.jpg", ContentFile(b"photo-bytes"), save=True)
        report = publish(draft, self.owner)
        self.assertEqual(report.photo.name, draft.photo.name)
        self.assertTrue(report.photo.storage.exists(report.photo.name))

    def test_a_replaced_photo_is_deleted_after_commit(self):
        report = make_report(self.owner)
        report.photo.save("old.jpg", ContentFile(b"old"), save=True)
        old_name = report.photo.name
        draft = Draft.objects.create(owner=self.owner, report=report, data=draft_data())
        draft.photo.save("new.jpg", ContentFile(b"new"), save=True)

        with self.captureOnCommitCallbacks(execute=True):
            publish(draft, self.owner)

        report.refresh_from_db()
        self.assertNotEqual(report.photo.name, old_name)
        self.assertFalse(report.photo.storage.exists(old_name))
        self.assertTrue(report.photo.storage.exists(report.photo.name))


class RecalculateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("recalc-owner@example.test")
        cls.finder = make_user("recalc-finder@example.test")

    def test_recalculating_creates_a_possible_match(self):
        lost = make_report(self.owner, "Lost")
        found = make_report(self.finder, "Found")
        recalculate(lost)
        match = Match.objects.get(lost=lost, found=found)
        self.assertEqual(match.state, "Possible Match")
        self.assertEqual(match.score, 100)

    def test_recalculating_removes_a_match_that_no_longer_scores(self):
        lost = make_report(self.owner, "Lost")
        found = make_report(self.finder, "Found")
        recalculate(lost)
        found.answers = {"colour": "Red", "kind": "Handbag"}
        found.save()
        recalculate(lost)
        self.assertFalse(Match.objects.filter(lost=lost, found=found).exists())

    def test_recalculating_leaves_an_active_handover_alone(self):
        lost = make_report(self.owner, "Lost")
        found = make_report(self.finder, "Found")
        match = make_match(lost, found, state="Handover Proposed")
        recalculate(lost)
        match.refresh_from_db()
        self.assertEqual(match.state, "Handover Proposed")

    def test_reserved_reports_are_not_offered_as_new_matches(self):
        lost = make_report(self.owner, "Lost")
        found = make_report(self.finder, "Found", reserved=True)
        recalculate(lost)
        self.assertFalse(Match.objects.filter(lost=lost, found=found).exists())


class TransitionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("transition-owner@example.test")
        cls.finder = make_user("transition-finder@example.test")
        cls.other = make_user("transition-other@example.test")

    def setUp(self):
        self.lost = make_report(self.owner, "Lost", title="Blue backpack")
        self.found = make_report(self.finder, "Found", title="Found blue backpack")
        self.match = make_match(self.lost, self.found)

    def refresh(self):
        self.lost.refresh_from_db()
        self.found.refresh_from_db()
        self.match.refresh_from_db()

    def propose(self):
        transition(self.match.pk, self.owner, "propose", meeting())
        self.refresh()

    def schedule(self):
        self.propose()
        transition(self.match.pk, self.finder, "accept")
        self.refresh()

    def test_proposing_reserves_both_reports_and_records_the_meeting(self):
        self.propose()
        self.assertTrue(self.lost.reserved)
        self.assertTrue(self.found.reserved)
        self.assertEqual(self.match.state, "Handover Proposed")
        self.assertEqual(self.match.proposer, self.owner)
        self.assertEqual(self.match.meeting_place, "NED Security Office")
        self.assertTrue(Event.objects.filter(report=self.lost, text="Handover Proposed").exists())

    def test_a_second_handover_cannot_reserve_a_busy_report(self):
        self.found.reserved = True
        self.found.save()
        with self.assertRaisesMessage(ValidationError, "already reserves"):
            transition(self.match.pk, self.owner, "propose", meeting())

    def test_the_meeting_place_and_time_are_required(self):
        for payload in (meeting(meeting_place=None), meeting(meeting_at=None), None):
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    transition(self.match.pk, self.owner, "propose", payload)

    def test_a_meeting_in_the_past_cannot_be_proposed(self):
        with self.assertRaisesMessage(ValidationError, "Choose a future meeting"):
            transition(self.match.pk, self.owner, "propose", meeting(
                meeting_at=timezone.now() - timedelta(hours=1),
            ))

    def test_only_the_other_participant_can_accept(self):
        self.propose()
        with self.assertRaisesMessage(ValidationError, "unavailable in this state"):
            transition(self.match.pk, self.owner, "accept")

    def test_the_other_participant_can_accept(self):
        self.schedule()
        self.assertEqual(self.match.state, "Handover Scheduled")

    def test_a_proposal_cannot_be_accepted_after_its_time_passed(self):
        self.propose()
        Match.objects.filter(pk=self.match.pk).update(
            meeting_at=timezone.now() - timedelta(seconds=1),
        )
        with self.assertRaisesMessage(ValidationError, "This meeting time has passed"):
            transition(self.match.pk, self.finder, "accept")

    def test_rejecting_frees_the_reports_and_records_who_dismissed(self):
        self.propose()
        transition(self.match.pk, self.finder, "reject")
        self.refresh()
        self.assertEqual(self.match.state, "Rejected")
        self.assertEqual(self.match.rejected_by, self.finder)
        self.assertFalse(self.lost.reserved)
        self.assertFalse(self.found.reserved)

    def test_only_the_dismisser_can_restore(self):
        self.propose()
        transition(self.match.pk, self.finder, "reject")
        with self.assertRaisesMessage(ValidationError, "Only the participant who dismissed"):
            transition(self.match.pk, self.owner, "restore")
        transition(self.match.pk, self.finder, "restore")
        self.refresh()
        self.assertEqual(self.match.state, "Possible Match")
        self.assertIsNone(self.match.rejected_by)

    def test_a_suggestion_cannot_return_while_another_handover_is_active(self):
        self.propose()
        transition(self.match.pk, self.finder, "reject")
        self.found.reserved = True
        self.found.save()
        with self.assertRaisesMessage(ValidationError, "handover is in progress"):
            transition(self.match.pk, self.finder, "restore")

    def test_a_suggestion_that_no_longer_scores_cannot_be_restored(self):
        self.propose()
        transition(self.match.pk, self.finder, "reject")
        # Rejecting clears ``reserved`` in the database; refresh so saving the
        # changed answers does not write the stale flag back.
        self.found.refresh_from_db()
        self.found.answers = {"colour": "Red", "kind": "Handbag"}
        self.found.save()
        with self.assertRaisesMessage(ValidationError, "no longer meets the matching rules"):
            transition(self.match.pk, self.finder, "restore")

    def test_the_return_cannot_be_confirmed_before_the_meeting(self):
        self.schedule()
        with self.assertRaisesMessage(ValidationError, "at or after the meeting time"):
            transition(self.match.pk, self.owner, "returned")

    def test_confirming_the_return_closes_both_reports_and_other_suggestions(self):
        self.schedule()
        other_found = make_report(self.other, "Found", title="Second found")
        recalculate(self.lost)
        competing = Match.objects.get(lost=self.lost, found=other_found)
        Match.objects.filter(pk=self.match.pk).update(
            meeting_at=timezone.now() - timedelta(seconds=1),
        )

        transition(self.match.pk, self.owner, "returned")
        self.refresh()
        competing.refresh_from_db()
        self.assertEqual((self.lost.status, self.found.status), ("Returned", "Returned"))
        self.assertEqual(self.match.state, "Returned")
        self.assertFalse(self.lost.reserved or self.found.reserved)
        self.assertEqual(competing.state, "Rejected")

    def test_outsiders_cannot_change_a_match(self):
        with self.assertRaisesMessage(ValidationError, "Only participants"):
            transition(self.match.pk, self.other, "propose", meeting())

    def test_actions_that_do_not_belong_to_the_state_are_rejected(self):
        with self.assertRaisesMessage(ValidationError, "unavailable in this state"):
            transition(self.match.pk, self.owner, "returned")
        with self.assertRaisesMessage(ValidationError, "unavailable in this state"):
            transition(self.match.pk, self.owner, "not-an-action")

    def test_reports_that_are_no_longer_open_block_the_action(self):
        self.lost.status = "Closed"
        self.lost.save()
        with self.assertRaisesMessage(ValidationError, "no longer open"):
            transition(self.match.pk, self.owner, "propose", meeting())


class ModerateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("moderate-owner@example.test")
        cls.staff = make_user("moderate-staff@example.test", staff=True)
        cls.finder = make_user("moderate-finder@example.test")

    def setUp(self):
        self.report = make_report(self.owner, "Lost")

    def test_staff_can_close_a_report(self):
        moderate(self.report, self.staff, "close")
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "Closed")
        self.assertTrue(Event.objects.filter(
            report=self.report, text="Closed by management",
        ).exists())

    def test_staff_can_remove_a_report(self):
        moderate(self.report, self.staff, "remove")
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "Removed")
        self.assertTrue(Event.objects.filter(
            report=self.report, text="Removed by management",
        ).exists())

    def test_moderation_rejects_possible_matches(self):
        found = make_report(self.finder, "Found")
        match = make_match(self.report, found)
        moderate(self.report, self.staff, "close")
        match.refresh_from_db()
        self.assertEqual(match.state, "Rejected")

    def test_non_staff_cannot_moderate(self):
        with self.assertRaisesMessage(ValidationError, "Moderator access required"):
            moderate(self.report, self.owner, "close")

    def test_unknown_actions_are_rejected(self):
        with self.assertRaisesMessage(ValidationError, "Moderator access required"):
            moderate(self.report, self.staff, "delete")

    def test_reserved_or_closed_reports_cannot_be_moderated(self):
        for change in ({"reserved": True}, {"status": "Returned"}):
            with self.subTest(change=change):
                report = make_report(self.owner, title=f"Moderated {change}", **change)
                with self.assertRaisesMessage(ValidationError, "Only open reports"):
                    moderate(report, self.staff, "close")
