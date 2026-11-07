"""Matching rules and the complete handover state machine."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.forms import MeetingForm
from core.models import Event, Match, Report
from core.services import recalculate, score, transition
from tests.support import (
    BAG_ANSWERS,
    AppTestCase,
    make_match,
    make_report,
    make_user,
    meeting,
    meeting_field_value,
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MatchingRulesTests(AppTestCase):
    def pair(self, **overrides):
        lost = make_report(self.owner, "Lost", answers=BAG_ANSWERS, **overrides)
        found = make_report(self.finder, "Found", answers=BAG_ANSWERS, **overrides)
        return lost, found

    def test_identical_opposite_reports_score_one_hundred(self):
        lost, found = self.pair()
        total, parts = score(lost, found)
        self.assertEqual(total, 100)
        self.assertEqual(parts, {
            "Category": 20, "Location": 20, "Date": 15,
            "Description": 15, "Private": 30,
        })

    def test_ineligible_pairs_never_match(self):
        lost, found = self.pair()
        cases = {
            "same owner": {"owner_id": lost.owner_id},
            "wrong category": {"category": "Keys"},
            "both lost": {"kind": "Lost"},
            "not open": {"status": "Returned"},
        }
        for label, change in cases.items():
            with self.subTest(case=label):
                candidate = make_report(self.finder, "Found", answers=BAG_ANSWERS)
                for key, value in change.items():
                    setattr(candidate, key, value)
                self.assertIsNone(score(lost, candidate))
        self.assertIsNone(score(found, lost))

    def test_two_meaningful_agreements_are_required(self):
        lost = make_report(self.owner, "Lost", answers={"colour": "Blue", "mark": "None"})
        found = make_report(self.finder, "Found", answers={"colour": "Blue", "mark": "None"})
        # "None" is deliberately ignored, so only one evidence field agrees.
        self.assertIsNone(score(lost, found))

    def test_a_pair_below_the_score_threshold_is_not_a_match(self):
        lost = make_report(
            self.owner, "Lost", answers={"colour": "Blue", "kind": "Backpack", "mark": "None"},
            lat="24.8607", lng="67.0011",
            description="blue backpack",
        )
        found = make_report(
            self.finder, "Found",
            answers={"colour": "Blue", "kind": "Backpack", "mark": "Scratch"},
            lat="24.8900", lng="67.0300",
            description="completely different words",
        )
        result = score(lost, found)
        self.assertIsNone(result)

    def test_generic_values_do_not_supply_agreements(self):
        generic = {"colour": "Other", "kind": "Other", "mark": "Other"}
        lost = make_report(self.owner, "Lost", answers=generic)
        found = make_report(self.finder, "Found", answers=generic)
        self.assertIsNone(score(lost, found))

    def test_location_bands_follow_the_nearest_half_kilometre(self):
        lost, found = self.pair()
        cases = [
            ("24.86", "67.001", "24.86", "67.001", 20),
            ("24.86", "67.001", "24.86", "67.008", 15),
            ("24.86", "67.001", "24.86", "67.015", 10),
            ("24.86", "67.001", "24.88", "67.020", 5),
            ("24.86", "67.001", "25.200", "67.500", 0),
        ]
        for la, lo, fb, fl, expected in cases:
            with self.subTest(far=(fb, fl)):
                lost.lat, lost.lng = la, lo
                found.lat, found.lng = fb, fl
                self.assertEqual(score(lost, found)[1]["Location"], expected)
        lost.lat = lost.lng = None
        self.assertEqual(score(lost, found)[1]["Location"], 0)

    def test_date_bands_follow_calendar_day_distance(self):
        lost, found = self.pair()
        for days, expected in [(0, 15), (1, 10), (-1, 10), (2, 5), (3, 5), (4, 0)]:
            with self.subTest(days=days):
                found.event_date = lost.event_date + timedelta(days=days)
                self.assertEqual(score(lost, found)[1]["Date"], expected)

    def test_description_similarity_is_token_overlap(self):
        lost, found = self.pair(description="blue backpack with a silver zip")
        found.description = "blue backpack with a silver zip"
        self.assertEqual(score(lost, found)[1]["Description"], 15)
        found.description = "completely unrelated green umbrella"
        self.assertEqual(score(lost, found)[1]["Description"], 0)

    def test_bank_cards_are_compared_as_an_unordered_set(self):
        lost, found = self.pair()
        lost.category = found.category = "Wallet / Purse"
        lost.answers = {
            "colour": "Black", "material": "Leather",
            "bank_1_issuer": "Other", "bank_1_other": "Bank A",
            "bank_1_suffix": "4111111111111111",
            "bank_2_issuer": "Other", "bank_2_other": "Bank B",
            "bank_2_suffix": "4222222222222222",
        }
        found.answers = {
            "colour": "Black", "material": "Leather",
            "bank_1_issuer": "Other", "bank_1_other": "Bank B",
            "bank_1_suffix": "4222222222222222",
            "bank_2_issuer": "Other", "bank_2_other": "Bank A",
            "bank_2_suffix": "4111111111111111",
        }
        self.assertEqual(score(lost, found)[0], 100)

    def test_recalculate_creates_and_refreshes_possible_matches(self):
        lost = make_report(self.owner, "Lost", answers=BAG_ANSWERS)
        found = make_report(self.finder, "Found", answers=BAG_ANSWERS)
        recalculate(lost)
        match = Match.objects.get(lost=lost, found=found)
        self.assertEqual(match.score, 100)
        self.assertEqual(match.state, "Possible Match")

        found.lat, found.lng = "25.20000000", "67.50000000"
        found.save(update_fields=["lat", "lng"])
        recalculate(lost)
        self.assertEqual(Match.objects.filter(lost=lost, found=found).count(), 1)
        self.assertLess(Match.objects.get(lost=lost, found=found).score, 100)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class HandoverStateMachineTests(AppTestCase):
    def setUp(self):
        self.lost = make_report(self.owner, "Lost", answers=BAG_ANSWERS)
        self.found = make_report(self.finder, "Found", answers=BAG_ANSWERS)
        self.match = make_match(self.lost, self.found)

    def test_non_participants_cannot_change_a_match(self):
        before = Event.objects.count()
        for action in ("propose", "accept", "reject", "restore", "returned"):
            with self.subTest(action=action), self.assertRaises(ValidationError):
                transition(self.match.pk, self.outsider, action, meeting())
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")
        self.assertEqual(Event.objects.count(), before)

    def test_proposal_reserves_both_reports_and_records_the_proposer(self):
        transition(self.match.pk, self.owner, "propose", meeting())
        self.match.refresh_from_db()
        self.lost.refresh_from_db()
        self.found.refresh_from_db()
        self.assertEqual(self.match.state, "Handover Proposed")
        self.assertEqual(self.match.proposer, self.owner)
        self.assertTrue(self.lost.reserved)
        self.assertTrue(self.found.reserved)

    def test_invalid_proposals_never_reserve_anything(self):
        invalid = [
            None,
            {},
            meeting(meeting_place=None),
            meeting(meeting_at=None),
            meeting(meeting_at=timezone.now() - timedelta(seconds=1)),
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                transition(self.match.pk, self.owner, "propose", payload)
            self.lost.refresh_from_db()
            self.found.refresh_from_db()
            self.assertFalse(self.lost.reserved or self.found.reserved)

    def test_proposer_cannot_accept_their_own_proposal(self):
        transition(self.match.pk, self.owner, "propose", meeting())
        with self.assertRaises(ValidationError):
            transition(self.match.pk, self.owner, "accept")

    def test_rejecting_a_proposal_releases_both_reservations(self):
        transition(self.match.pk, self.owner, "propose", meeting())
        transition(self.match.pk, self.finder, "reject")
        self.lost.refresh_from_db()
        self.found.refresh_from_db()
        self.match.refresh_from_db()
        self.assertFalse(self.lost.reserved or self.found.reserved)
        self.assertEqual(self.match.state, "Rejected")
        self.assertEqual(self.match.rejected_by, self.finder)

    def test_only_the_dismisser_can_restore_and_the_pair_is_rechecked(self):
        transition(self.match.pk, self.finder, "reject")
        with self.assertRaises(ValidationError):
            transition(self.match.pk, self.owner, "restore")
        transition(self.match.pk, self.finder, "restore")
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")
        self.assertIsNone(self.match.rejected_by)

    def test_restore_fails_when_the_pair_no_longer_scores(self):
        transition(self.match.pk, self.finder, "reject")
        self.found.category = "Keys"
        self.found.save(update_fields=["category"])
        with self.assertRaises(ValidationError):
            transition(self.match.pk, self.finder, "restore")

    def test_acceptance_requires_a_future_meeting(self):
        transition(self.match.pk, self.owner, "propose", meeting())
        Match.objects.filter(pk=self.match.pk).update(
            meeting_at=timezone.now() - timedelta(seconds=1),
        )
        with self.assertRaises(ValidationError):
            transition(self.match.pk, self.finder, "accept")

    def test_scheduled_handovers_cannot_be_dismissed_or_reproposed(self):
        transition(self.match.pk, self.owner, "propose", meeting())
        transition(self.match.pk, self.finder, "accept")
        for action in ("reject", "propose", "accept"):
            with self.subTest(action=action), self.assertRaises(ValidationError):
                transition(self.match.pk, self.owner, action, meeting())
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Handover Scheduled")

    def test_return_is_blocked_until_the_meeting_time(self):
        transition(self.match.pk, self.owner, "propose", meeting())
        transition(self.match.pk, self.finder, "accept")
        with self.assertRaises(ValidationError):
            transition(self.match.pk, self.owner, "returned")
        Match.objects.filter(pk=self.match.pk).update(
            meeting_at=timezone.now() - timedelta(seconds=1),
        )
        transition(self.match.pk, self.finder, "returned")
        self.lost.refresh_from_db()
        self.found.refresh_from_db()
        self.match.refresh_from_db()
        self.assertEqual((self.lost.status, self.found.status), ("Returned", "Returned"))
        self.assertFalse(self.lost.reserved or self.found.reserved)
        self.assertEqual(self.match.state, "Returned")

    def test_return_rejects_other_possible_matches_for_either_report(self):
        other_found = make_report(
            make_user("other-found@example.test"), "Found", title="Other found",
        )
        competing = make_match(self.lost, other_found, score=80)
        transition(self.match.pk, self.owner, "propose", meeting())
        transition(self.match.pk, self.finder, "accept")
        Match.objects.filter(pk=self.match.pk).update(
            meeting_at=timezone.now() - timedelta(seconds=1),
        )
        transition(self.match.pk, self.finder, "returned")
        competing.refresh_from_db()
        self.assertEqual(competing.state, "Rejected")

    def test_actions_outside_the_current_state_do_not_mutate(self):
        for action in ("accept", "returned", "restore", "bogus"):
            with self.subTest(action=action), self.assertRaises(ValidationError):
                transition(self.match.pk, self.owner, action, meeting())
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")

    def test_each_transition_writes_an_audit_event_for_both_reports(self):
        transition(self.match.pk, self.owner, "propose", meeting())
        self.assertTrue(Event.objects.filter(
            report=self.lost, actor=self.owner, text="Handover Proposed",
        ).exists())
        self.assertTrue(Event.objects.filter(
            report=self.found, actor=self.owner, text="Handover Proposed",
        ).exists())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MatchPageTests(AppTestCase):
    def setUp(self):
        self.lost = make_report(self.owner, "Lost", answers=BAG_ANSWERS)
        self.found = make_report(self.finder, "Found", answers=BAG_ANSWERS)
        self.match = make_match(self.lost, self.found)

    def test_only_participants_can_open_the_match_page(self):
        self.login(self.outsider)
        self.assertEqual(
            self.client.get(reverse("match", args=[self.match.pk])).status_code, 404,
        )
        for user in (self.owner, self.finder):
            with self.subTest(user=user.email):
                self.login(user)
                self.assertEqual(
                    self.client.get(reverse("match", args=[self.match.pk])).status_code,
                    200,
                )

    def test_contacts_stay_locked_until_the_other_side_accepts(self):
        self.login(self.owner)
        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertContains(page, "Contact details locked")
        self.assertNotContains(page, "03001234567")

        transition(self.match.pk, self.owner, "propose", meeting())
        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertContains(page, "Contact details locked")
        self.assertNotContains(page, "03001234567")

        transition(self.match.pk, self.finder, "accept")
        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertContains(page, "Participant contact details")
        self.assertContains(page, "03001234567")

    def test_the_other_side_sees_accept_but_the_proposer_does_not(self):
        transition(self.match.pk, self.owner, "propose", meeting())
        self.login(self.finder)
        self.assertContains(
            self.client.get(reverse("match", args=[self.match.pk])),
            "Accept this meeting",
        )
        self.login(self.owner)
        self.assertNotContains(
            self.client.get(reverse("match", args=[self.match.pk])),
            "Accept this meeting",
        )

    def test_proposal_through_the_form_uses_the_shared_time_format(self):
        self.login(self.owner)
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
        self.assertEqual(self.match.state, "Handover Proposed")

    def test_a_malformed_meeting_time_is_rejected_without_reserving(self):
        self.login(self.owner)
        response = self.client.post(reverse("match", args=[self.match.pk]), {
            "action": "propose",
            "meeting_place": "NED Security Office",
            "meeting_at": "tomorrow at noon",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Use DD-MM-YY hh:mm AM/PM")
        self.match.refresh_from_db()
        self.lost.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")
        self.assertFalse(self.lost.reserved)

    def test_reject_and_restore_work_through_the_view(self):
        self.login(self.owner)
        response = self.client.post(
            reverse("match", args=[self.match.pk]), {"action": "reject"},
        )
        self.assertRedirects(
            response, reverse("match", args=[self.match.pk]),
            fetch_redirect_response=False,
        )
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Rejected")
        self.assertEqual(self.match.rejected_by, self.owner)
        self.assertContains(
            self.client.get(reverse("match", args=[self.match.pk])),
            "Restore suggestion",
        )

        response = self.client.post(
            reverse("match", args=[self.match.pk]), {"action": "restore"},
        )
        self.assertRedirects(
            response, reverse("match", args=[self.match.pk]),
            fetch_redirect_response=False,
        )
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")

    def test_an_outsider_cannot_post_an_action(self):
        self.login(self.outsider)
        response = self.client.post(
            reverse("match", args=[self.match.pk]), {"action": "reject"},
        )
        self.assertEqual(response.status_code, 404)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CompetingHandoverTests(AppTestCase):
    def test_only_one_pair_can_be_reserved_at_a_time(self):
        lost = make_report(self.owner, "Lost", answers=BAG_ANSWERS)
        first = make_match(lost, make_report(self.finder, "Found", answers=BAG_ANSWERS))
        second = make_match(
            lost, make_report(self.outsider, "Found", answers=BAG_ANSWERS),
        )
        transition(first.pk, self.owner, "propose", meeting())
        with self.assertRaises(ValidationError):
            transition(second.pk, self.outsider, "propose", meeting())
        second.refresh_from_db()
        self.assertEqual(second.state, "Possible Match")

    def test_releasing_the_first_pair_makes_the_second_available(self):
        lost = make_report(self.owner, "Lost", answers=BAG_ANSWERS)
        first = make_match(lost, make_report(self.finder, "Found", answers=BAG_ANSWERS))
        second = make_match(
            lost, make_report(self.outsider, "Found", answers=BAG_ANSWERS),
        )
        transition(first.pk, self.owner, "propose", meeting())
        transition(first.pk, self.finder, "reject")
        transition(second.pk, self.outsider, "propose", meeting())
        second.refresh_from_db()
        self.assertEqual(second.state, "Handover Proposed")

    def test_the_parked_match_is_hidden_from_its_owner_until_released(self):
        lost = make_report(self.owner, "Lost", answers=BAG_ANSWERS)
        first = make_match(lost, make_report(self.finder, "Found", answers=BAG_ANSWERS))
        second = make_match(
            lost, make_report(self.outsider, "Found", answers=BAG_ANSWERS),
        )
        transition(first.pk, self.owner, "propose", meeting())
        self.login(self.outsider)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, reverse("match", args=[second.pk]))
        self.assertEqual(response.context["possible_count"], 0)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AutomaticMatchingTests(AppTestCase):
    def test_publishing_opposite_reports_creates_a_match_automatically(self):
        from tests.support import submit_wizard

        lost = submit_wizard(self.client, self.owner, kind="Lost", answers=BAG_ANSWERS)
        found = submit_wizard(self.client, self.finder, kind="Found", answers=BAG_ANSWERS)
        match = Match.objects.get(lost=lost, found=found)
        self.assertEqual(match.score, 100)
        self.assertEqual(match.state, "Possible Match")

    def test_same_owner_reports_never_match(self):
        from tests.support import submit_wizard

        lost = submit_wizard(self.client, self.owner, kind="Lost", title="Mine lost",
                             answers=BAG_ANSWERS)
        found = submit_wizard(self.client, self.owner, kind="Found", title="Mine found",
                              answers=BAG_ANSWERS)
        self.assertFalse(Match.objects.filter(lost=lost, found=found).exists())

    def test_different_categories_never_match(self):
        from tests.support import submit_wizard

        lost = submit_wizard(self.client, self.owner, kind="Lost", answers=BAG_ANSWERS)
        found = submit_wizard(
            self.client, self.finder, kind="Found", category="Keys",
            title="Keys found", answers={
                "colour": "Silver", "count": "3", "kind": "Home",
                "fob": "Plastic", "mark": "None",
            },
        )
        self.assertFalse(Match.objects.filter(lost=lost, found=found).exists())
