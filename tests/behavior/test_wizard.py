"""The five-step report wizard: drafts, validation, publication, and editing."""

from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Draft, Event, Report
from tests.support import (
    CATEGORY_ANSWERS,
    AppTestCase,
    make_report,
    make_user,
    start_wizard,
    submit_wizard,
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WizardNavigationTests(AppTestCase):
    def test_create_starts_a_draft_and_redirects_to_step_one(self):
        self.login()
        response = self.client.get(reverse("create"))
        draft = Draft.objects.get(owner=self.owner, report__isnull=True)
        self.assertRedirects(
            response, reverse("draft", args=[draft.pk]), fetch_redirect_response=False,
        )

    def test_later_steps_redirect_back_until_earlier_steps_are_saved(self):
        draft, url = start_wizard(self.client, self.owner)
        self.assertRedirects(
            self.client.get(url + "?step=2"), url + "?step=1",
            fetch_redirect_response=False,
        )
        self.client.post(url + "?step=1", {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })
        self.assertRedirects(
            self.client.get(url + "?step=3"), url + "?step=2",
            fetch_redirect_response=False,
        )

    def test_step_numbers_are_clamped_and_invalid_values_fall_back_to_one(self):
        draft, url = start_wizard(self.client, self.owner)
        self.assertEqual(self.client.get(url + "?step=0").context["step"], 1)
        self.assertEqual(self.client.get(url + "?step=-5").context["step"], 1)
        self.assertEqual(self.client.get(url + "?step=abc").context["step"], 1)
        draft.data = {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": timezone.localdate().isoformat(),
            "description": "Blue fabric backpack", "location": "Library",
            "lat": "24.86", "lng": "67.001", "location_detail": "Entrance",
            "answers": CATEGORY_ANSWERS["Bag"],
        }
        draft.save(update_fields=["data"])
        self.assertEqual(self.client.get(url + "?step=99").context["step"], 5)

    def test_each_step_saves_and_advances(self):
        draft, url = start_wizard(self.client, self.owner)
        payloads = [
            (1, {"kind": "Lost", "title": "Blue backpack", "category": "Bag",
                 "event_date": timezone.localdate().strftime("%d-%m-%Y")}),
            (2, {"description": "Blue fabric backpack", "contact": "03001234567"}),
            (3, {"location": "Central Library", "lat": "24.86", "lng": "67.001",
                 "location_detail": "Beside the entrance"}),
            (4, CATEGORY_ANSWERS["Bag"]),
        ]
        for step, payload in payloads:
            with self.subTest(step=step):
                response = self.client.post(f"{url}?step={step}", payload)
                self.assertRedirects(
                    response, f"{url}?step={step + 1}",
                    fetch_redirect_response=False,
                )
                draft.refresh_from_db()
        self.assertEqual(draft.data["title"], "Blue backpack")
        self.assertEqual(draft.data["answers"]["colour"], "Blue")

    def test_changing_category_clears_private_answers(self):
        draft, url = start_wizard(self.client, self.owner)
        self.client.post(url + "?step=1", {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })
        self.client.post(url + "?step=2", {
            "description": "Blue fabric backpack", "contact": "03001234567",
        })
        self.client.post(url + "?step=3", {
            "location": "Library", "lat": "24.86", "lng": "67.001",
            "location_detail": "Entrance",
        })
        self.client.post(url + "?step=4", CATEGORY_ANSWERS["Bag"])
        draft.refresh_from_db()
        self.assertIn("answers", draft.data)
        self.assertContains(
            self.client.get(url + "?step=1"), "Changing category clears your private answers.",
        )

        response = self.client.post(url + "?step=1", {
            "kind": "Lost", "title": "Wallet", "category": "Wallet / Purse",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertNotIn("answers", draft.data)
        # The warning is gone because there are no private answers left to clear.
        self.assertNotContains(
            self.client.get(url + "?step=1"), "Changing category clears your private answers.",
        )


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WizardValidationTests(AppTestCase):
    def test_each_step_rejects_invalid_input_and_keeps_the_previous_save(self):
        draft, url = start_wizard(self.client, self.owner)
        self.client.post(url + "?step=1", {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })

        invalid_two = self.client.post(url + "?step=2", {
            "description": "call me 03001234567", "contact": "123",
        })
        self.assertEqual(invalid_two.status_code, 200)
        self.assertContains(invalid_two, "at least 11 characters")
        self.assertContains(invalid_two, "Move phone numbers, emails, CNIC, card, account, and roll numbers")
        draft.refresh_from_db()
        self.assertNotIn("description", draft.data)

        valid_two = self.client.post(url + "?step=2", {
            "description": "Blue fabric backpack with two front pockets",
            "contact": "03001234567",
        })
        self.assertEqual(valid_two.status_code, 302)

        invalid_three = self.client.post(url + "?step=3", {
            "location": "Library", "lat": "91", "lng": "181",
            "location_detail": "Entrance",
        })
        self.assertEqual(invalid_three.status_code, 200)
        self.assertContains(invalid_three, "less than or equal to 90")
        self.assertContains(invalid_three, "less than or equal to 180")

    def test_a_future_event_date_is_rejected_with_a_readable_message(self):
        draft, url = start_wizard(self.client, self.owner)
        response = self.client.post(url + "?step=1", {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": (timezone.localdate() + timedelta(days=1)).strftime("%d-%m-%Y"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a real date between 2000 and today.")
        draft.refresh_from_db()
        self.assertNotIn("kind", draft.data)

    def test_review_escapes_user_text_instead_of_rendering_markup(self):
        draft, url = start_wizard(self.client, self.owner)
        draft.data = {
            "kind": "Lost", "title": "<script>alert(1)</script>", "category": "Bag",
            "event_date": timezone.localdate().isoformat(),
            "description": "Blue backpack", "location": "Library",
            "lat": "24.86", "lng": "67.001", "location_detail": "Entrance",
            "answers": CATEGORY_ANSWERS["Bag"],
        }
        draft.save(update_fields=["data"])
        response = self.client.get(url + "?step=5")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_submitting_an_incomplete_draft_shows_an_error_and_keeps_the_draft(self):
        draft, url = start_wizard(self.client, self.owner)
        # Every step has been visited, so the review page renders. One saved
        # value is blank, so publishing must still fail cleanly.
        draft.data = {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": timezone.localdate().isoformat(),
            "description": "", "contact": "03001234567",
            "location": "Central Library", "lat": "24.86", "lng": "67.001",
            "location_detail": "Entrance", "answers": CATEGORY_ANSWERS["Bag"],
        }
        draft.save(update_fields=["data"])
        response = self.client.post(url + "?step=5")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Complete and check every step before submitting.")
        self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())
        self.assertFalse(Report.objects.filter(owner=self.owner).exists())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WizardPublicationTests(AppTestCase):
    def test_all_categories_publish_successfully(self):
        for category, answers in CATEGORY_ANSWERS.items():
            with self.subTest(category=category):
                report = submit_wizard(
                    self.client, self.owner,
                    title=f"{category} item",
                    category=category,
                    answers=answers,
                )
                self.assertEqual(report.category, category)
                self.assertEqual(report.status, "Open")
                self.assertEqual(report.owner, self.owner)
                self.assertEqual(report.answers.get("colour"), answers["colour"])

    def test_publication_creates_one_report_deletes_the_draft_and_logs_the_event(self):
        draft, url = start_wizard(self.client, self.owner)
        report = submit_wizard(self.client, self.owner)
        self.assertFalse(Draft.objects.filter(pk=draft.pk).exists())
        self.assertEqual(Report.objects.filter(owner=self.owner).count(), 1)
        self.assertEqual(report.answers["kind"], "Backpack")
        self.assertTrue(Event.objects.filter(
            report=report, actor=self.owner, text="Report created",
        ).exists())

    def test_success_message_reports_when_a_possible_match_was_found(self):
        found = make_report(
            self.finder, "Found", title="Blue backpack found", answers=CATEGORY_ANSWERS["Bag"],
        )
        self.login(self.owner)
        response = submit_wizard(
            self.client, self.owner, title="Blue backpack",
            answers=CATEGORY_ANSWERS["Bag"],
        )
        dashboard = self.client.get(response.get_absolute_url() if hasattr(response, "get_absolute_url") else reverse("dashboard"))
        self.assertContains(dashboard, "possible match")

    def test_a_duplicate_open_report_is_flagged_on_review(self):
        make_report(self.owner, title="Blue backpack", category="Bag")
        draft, url = start_wizard(self.client, self.owner)
        draft.data = {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": timezone.localdate().isoformat(),
            "description": "Blue fabric backpack", "contact": "03001234567",
            "location": "Library", "lat": "24.86", "lng": "67.001",
            "location_detail": "Entrance", "answers": CATEGORY_ANSWERS["Bag"],
        }
        draft.save(update_fields=["data"])
        response = self.client.get(url + "?step=5")
        self.assertContains(response, "A similar open report already exists")

    def test_the_same_draft_cannot_be_published_twice(self):
        draft, url = start_wizard(self.client, self.owner)
        submit_wizard(self.client, self.owner)
        self.assertEqual(self.client.post(url + "?step=5").status_code, 404)
        self.assertEqual(Report.objects.filter(owner=self.owner).count(), 1)

    def test_category_dependencies_render_and_update_without_javascript(self):
        draft, url = start_wizard(self.client, self.owner)
        self.client.post(url + "?step=1", {
            "kind": "Lost", "title": "Black wallet", "category": "Wallet / Purse",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })
        self.client.post(url + "?step=2", {
            "description": "Black leather wallet", "contact": "03001234567",
        })
        self.client.post(url + "?step=3", {
            "location": "Library", "lat": "24.86", "lng": "67.001",
            "location_detail": "Entrance",
        })
        response = self.client.post(url + "?step=4", {
            **CATEGORY_ANSWERS["Wallet / Purse"], "contents": ["CNIC"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Full 13-digit CNIC")

        response = self.client.post(url + "?step=4", {
            **CATEGORY_ANSWERS["Wallet / Purse"], "contents": ["Bank cards"],
            "bank_count": "3",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bank card 3 bank or payment service")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DraftResumeTests(AppTestCase):
    def test_resume_page_offers_continue_and_discard(self):
        draft = Draft.objects.create(owner=self.owner, data={
            "kind": "Lost", "title": "Saved keys", "category": "Keys",
            "event_date": timezone.localdate().isoformat(),
        })
        self.login()
        response = self.client.get(reverse("create"))
        self.assertContains(response, "Continue the Lost draft")
        self.assertContains(response, "Discard draft and start new")
        self.assertContains(response, "permanently discards this saved draft")
        self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())

    def test_discard_requires_the_exact_confirmation_and_draft_id(self):
        draft = Draft.objects.create(owner=self.owner, data={"title": "Keep me"})
        self.login()
        for payload in (
            {"action": "new"},
            {"action": "new", "confirm_discard": "yes"},
            {"action": "new", "confirm_discard": "yes", "discard_draft_id": "999"},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(reverse("create"), payload)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Confirm that you want to discard")
                self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())

        response = self.client.post(reverse("create"), {
            "action": "new", "confirm_discard": "yes",
            "discard_draft_id": str(draft.pk),
        })
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)
        self.assertFalse(Draft.objects.filter(pk=draft.pk).exists())

    def test_blank_draft_prompt_does_not_invent_a_kind(self):
        Draft.objects.create(owner=self.owner)
        self.login()
        response = self.client.get(reverse("create"))
        self.assertContains(response, "Continue the draft")
        self.assertNotContains(response, "Continue the Lost draft")

    def test_another_users_draft_is_not_reachable(self):
        other = make_user("draft-owner@example.test")
        draft = Draft.objects.create(owner=other)
        self.login()
        self.assertEqual(
            self.client.get(reverse("draft", args=[draft.pk])).status_code, 404,
        )


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EditReportTests(AppTestCase):
    def test_editing_loads_saved_values_and_updates_in_place(self):
        report = make_report(self.owner, answers=CATEGORY_ANSWERS["Bag"])
        self.login()
        response = self.client.post(reverse("edit", args=[report.pk]))
        draft = Draft.objects.get(owner=self.owner, report=report)
        self.assertRedirects(
            response, reverse("draft", args=[draft.pk]),
            fetch_redirect_response=False,
        )

        location = self.client.get(reverse("draft", args=[draft.pk]) + "?step=3").context["form"]
        self.assertEqual(location["location"].value(), report.location)
        self.assertEqual(location["location_detail"].value(), report.location_detail)
        self.assertEqual(location["lat"].value(), str(report.lat))
        matching = self.client.get(reverse("draft", args=[draft.pk]) + "?step=4").context["form"]
        self.assertEqual(matching["colour"].value(), "Blue")

        self.client.post(reverse("draft", args=[draft.pk]) + "?step=1", {
            "kind": "Lost", "title": "Blue backpack updated", "category": "Bag",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })
        response = self.client.post(reverse("draft", args=[draft.pk]) + "?step=5")
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.title, "Blue backpack updated")
        self.assertEqual(Report.objects.filter(owner=self.owner).count(), 1)
        self.assertTrue(Event.objects.filter(
            report=report, text="Report updated",
        ).exists())

    def test_editing_is_locked_while_reserved_or_closed(self):
        self.login()
        for changes in ({"reserved": True}, {"status": "Returned"}):
            with self.subTest(changes=changes):
                report = make_report(
                    self.owner, title=f"Locked {changes}", **changes,
                )
                response = self.client.post(reverse("edit", args=[report.pk]))
                self.assertRedirects(
                    response, reverse("report", args=[report.pk]),
                    fetch_redirect_response=False,
                )
                self.assertFalse(Draft.objects.filter(report=report).exists())

    def test_an_existing_edit_draft_is_locked_when_the_report_closes(self):
        report = make_report(self.owner)
        self.login()
        self.client.post(reverse("edit", args=[report.pk]))
        draft = Draft.objects.get(report=report)
        report.status = "Returned"
        report.save(update_fields=["status"])
        response = self.client.get(reverse("draft", args=[draft.pk]))
        self.assertRedirects(
            response, reverse("report", args=[report.pk]),
            fetch_redirect_response=False,
        )
