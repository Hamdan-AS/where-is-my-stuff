"""Adversarial regression tests for authorization and match state boundaries."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Draft, Event, Match, Report, User
from .services import moderate, transition


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AdversarialFlowTests(TestCase):
    password = "Correct-horse-763!"
    private_answers = {
        "colour": "Black", "kind": "Backpack", "material": "Fabric",
        "pockets": "2", "mark": "None",
    }

    def setUp(self):
        self.owner = self.make_user("owner")
        self.finder = self.make_user("finder")
        self.outsider = self.make_user("outsider")
        self.lost = self.make_report(self.owner, "Lost")
        self.found = self.make_report(self.finder, "Found")
        self.match = Match.objects.create(
            lost=self.lost, found=self.found, score=100,
            breakdown={"Category": 20, "Location": 20, "Date": 15,
                       "Description": 15, "Private": 30},
        )

    def make_user(self, name, *, staff=False):
        email = f"{name}@example.com"
        return User.objects.create_user(
            username=email, email=email, password=self.password, is_staff=staff,
        )

    def make_report(self, owner, kind, **overrides):
        fields = {
            "owner": owner, "kind": kind, "title": "Black backpack",
            "category": "Bag", "description": "Black backpack water bottle side pocket",
            "location": "Central Library", "lat": "24.86070000",
            "lng": "67.00110000", "location_detail": "Near entrance",
            "event_date": timezone.localdate(), "contact": "03001234567",
            "answers": self.private_answers,
        }
        fields.update(overrides)
        return Report.objects.create(**fields)

    def meeting(self, **overrides):
        value = {
            "meeting_place": "NED Security Office",
            "meeting_at": timezone.now() + timedelta(days=1),
        }
        value.update(overrides)
        return value

    def test_nonparticipant_cannot_transition_match_or_create_events(self):
        before = Event.objects.count()
        for action in ("propose", "reject", "restore", "accept", "returned"):
            with self.subTest(action=action), self.assertRaises(ValidationError):
                transition(self.match.pk, self.outsider, action, self.meeting())
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")
        self.assertEqual(Event.objects.count(), before)

    def test_proposal_is_reserved_and_cannot_be_accepted_by_proposer(self):
        transition(self.match.pk, self.owner, "propose", self.meeting())
        self.lost.refresh_from_db()
        self.found.refresh_from_db()
        self.match.refresh_from_db()
        self.assertTrue(self.lost.reserved)
        self.assertTrue(self.found.reserved)
        self.assertEqual(self.match.state, "Handover Proposed")
        self.assertEqual(self.match.proposer_id, self.owner.pk)
        with self.assertRaises(ValidationError):
            transition(self.match.pk, self.owner, "accept")

    def test_invalid_proposal_never_reserves_reports(self):
        bad_meetings = (None, {}, self.meeting(meeting_place=None),
                        self.meeting(meeting_at=None),
                        self.meeting(meeting_at=timezone.now() - timedelta(seconds=1)))
        for meeting in bad_meetings:
            with self.subTest(meeting=meeting), self.assertRaises(ValidationError):
                transition(self.match.pk, self.owner, "propose", meeting)
            self.lost.refresh_from_db()
            self.found.refresh_from_db()
            self.assertFalse(self.lost.reserved)
            self.assertFalse(self.found.reserved)

    def test_rejecting_proposal_releases_both_reservations(self):
        transition(self.match.pk, self.owner, "propose", self.meeting())
        transition(self.match.pk, self.finder, "reject")
        self.lost.refresh_from_db()
        self.found.refresh_from_db()
        self.match.refresh_from_db()
        self.assertFalse(self.lost.reserved)
        self.assertFalse(self.found.reserved)
        self.assertEqual(self.match.state, "Rejected")
        self.assertEqual(self.match.rejected_by_id, self.finder.pk)

    def test_rejected_match_can_only_be_restored_by_rejecting_user(self):
        transition(self.match.pk, self.finder, "reject")
        with self.assertRaises(ValidationError):
            transition(self.match.pk, self.owner, "restore")
        transition(self.match.pk, self.finder, "restore")
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")
        self.assertIsNone(self.match.rejected_by_id)

    def test_actions_outside_current_state_are_rejected_without_mutation(self):
        for action in ("accept", "returned", "restore", "bogus"):
            with self.subTest(action=action), self.assertRaises(ValidationError):
                transition(self.match.pk, self.owner, action)
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Possible Match")

    def test_scheduled_handover_cannot_be_dismissed_or_reproposed(self):
        transition(self.match.pk, self.owner, "propose", self.meeting())
        transition(self.match.pk, self.finder, "accept")
        for action in ("reject", "propose", "accept"):
            with self.subTest(action=action), self.assertRaises(ValidationError):
                transition(self.match.pk, self.owner, action, self.meeting())
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, "Handover Scheduled")
        self.assertEqual(Report.objects.filter(pk__in=[self.lost.pk, self.found.pk], reserved=True).count(), 2)

    def test_return_is_blocked_until_meeting_and_closes_both_reports(self):
        transition(self.match.pk, self.owner, "propose", self.meeting())
        transition(self.match.pk, self.finder, "accept")
        with self.assertRaises(ValidationError):
            transition(self.match.pk, self.owner, "returned")
        Match.objects.filter(pk=self.match.pk).update(meeting_at=timezone.now() - timedelta(seconds=1))
        transition(self.match.pk, self.finder, "returned")
        self.lost.refresh_from_db()
        self.found.refresh_from_db()
        self.match.refresh_from_db()
        self.assertEqual((self.lost.status, self.found.status), ("Returned", "Returned"))
        self.assertFalse(self.lost.reserved or self.found.reserved)
        self.assertEqual(self.match.state, "Returned")

    def test_match_page_hides_contact_until_handover_is_accepted(self):
        self.client.force_login(self.owner)
        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertNotContains(page, "03001234567")
        self.assertNotContains(page, "Participant contact details")
        transition(self.match.pk, self.owner, "propose", self.meeting())
        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertNotContains(page, "03001234567")
        transition(self.match.pk, self.finder, "accept")
        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertContains(page, "Participant contact details")
        self.assertContains(page, "03001234567")

    def test_private_matching_answers_never_render_in_app_pages(self):
        self.client.force_login(self.owner)
        for url in (reverse("report", args=[self.lost.pk]),
                    reverse("match", args=[self.match.pk]),
                    reverse("dashboard")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotContains(response, '"pockets"')
        staff = User.objects.create_user(
            username="privacy-staff@example.com", email="privacy-staff@example.com",
            password=self.password, is_staff=True,
        )
        self.client.force_login(staff)
        self.assertNotContains(self.client.get(reverse("management")), '"pockets"')

    def test_reports_drafts_and_matches_are_not_registered_in_admin(self):
        self.client.force_login(self.make_user("admin", staff=True))
        for model_name in ("report", "draft", "match", "event"):
            with self.subTest(model=model_name):
                response = self.client.get(f"/admin/core/{model_name}/")
                self.assertEqual(response.status_code, 404)

    def test_owner_scoping_hides_other_users_reports_and_drafts(self):
        draft = Draft.objects.create(owner=self.finder)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("report", args=[self.found.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("draft", args=[draft.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("match", args=[Match.objects.create(
            lost=self.make_report(self.finder, "Lost", title="Other lost"),
            found=self.make_report(self.outsider, "Found", title="Other found"), score=80,
        ).pk])).status_code, 404)

    def test_non_staff_cannot_moderate_and_invalid_actions_do_not_change_report(self):
        with self.assertRaises(ValidationError):
            moderate(self.lost, self.owner, "close")
        moderator = self.make_user("moderator", staff=True)
        with self.assertRaises(ValidationError):
            moderate(self.lost, moderator, "purge")
        self.lost.refresh_from_db()
        self.assertEqual(self.lost.status, "Open")

    def test_moderation_is_audited_and_rejects_related_possible_matches(self):
        other_found = self.make_report(self.outsider, "Found", title="Another backpack")
        other_match = Match.objects.create(lost=self.lost, found=other_found, score=80)
        moderator = self.make_user("moderator", staff=True)
        moderate(self.lost, moderator, "close")
        self.lost.refresh_from_db()
        other_match.refresh_from_db()
        self.assertEqual(self.lost.status, "Closed")
        self.assertEqual(other_match.state, "Rejected")
        self.assertTrue(Event.objects.filter(report=self.lost, actor=moderator,
                                             text="Closed by management").exists())

    def test_reserved_report_cannot_be_moderated(self):
        transition(self.match.pk, self.owner, "propose", self.meeting())
        moderator = self.make_user("moderator", staff=True)
        with self.assertRaises(ValidationError):
            moderate(self.lost, moderator, "remove")
        self.lost.refresh_from_db()
        self.assertEqual(self.lost.status, "Open")

    def test_edit_endpoint_requires_post_and_owner(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("edit", args=[self.lost.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse("edit", args=[self.found.pk])).status_code, 404)

    def test_report_public_id_is_unique_and_not_the_sequential_primary_key(self):
        other = self.make_report(self.outsider, "Found", title="Other item")
        self.assertNotEqual(self.lost.public_id, other.public_id)
        self.assertNotEqual(str(self.lost.public_id), str(self.lost.pk))
