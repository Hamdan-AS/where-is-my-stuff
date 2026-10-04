from datetime import timedelta
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import User, Report, Draft, Match
from .forms import MatchingForm, TypeForm, DetailsForm, LocationForm, MeetingForm, public_text, public_short, MEETING_TIME_PATTERN
from .services import score, transition, moderate

class PublicFieldScreeningTests(TestCase):
    """Public fields must reject private identifiers, never rewrite them."""

    def test_description_rejects_emails_and_phones(self):
        leaks = ["contact a@example.com", "call 0312 3456789 after 5pm", "0300-1234567 is my number",
                 "my cell is +92-300-1234567", "dial 3051234 any time", "reach me at 99251234",
                 "phone 0300.123.4567 thanks", "call me 0321 7654321", "number is 0 3 0 0 1 2 3 4 5 6 7",
                 "mobile ０３００１２３４５６７"]
        for text in leaks:
            with self.subTest(text=text):
                with self.assertRaises(ValidationError):
                    public_text(text)

    def test_description_rejects_ids_and_accounts(self):
        leaks = ["cnic 42101-1234567-1 for verification", "id: 4210112345671",
                 "visa card number 1234 5678 9012 3456", "bank account 012345678901 iirc",
                 "iban PK36SCBL0000001123456702", "last 4 digits are 1234 on the card",
                 "last four digits are 4321", "roll no 2023-ME-123 on the tag", "2023ME123 engraved",
                 "reg no 2023-CS-045 inside", "seat number 654321 written under it",
                 "card no 1234 on the back", "token #88 on the lanyard", "passport AV-1234567"]
        for text in leaks:
            with self.subTest(text=text):
                with self.assertRaises(ValidationError):
                    public_text(text)

    def test_description_rejects_obfuscation(self):
        leaks = ["reach ali at gmail dot com please", "email ME AT GMAIL DOT COM teehee",
                 "0300\x00-1234567 cell", "0300\u200c1234567 cell"]
        for text in leaks:
            with self.subTest(text=text):
                with self.assertRaises(ValidationError):
                    public_text(text)

    def test_description_allows_legitimate_item_text(self):
        ok = ["Black leather wallet lost near the library entrance",
              "blue rain jacket, size small, sleeve patch",
              "HP laptop, 8GB RAM, 256GB SSD, charger included",
              "iPhone 15 Pro, 512GB storage, dark blue case",
              "lost on 12-05-2026 near the cafeteria",
              "in room 105, building 5, second floor",
              "the card is on floor 12, near the window",
              "seat belt found in the 2026 car",
              "سياه بٹوہ لائبریری کے قریب ملا",
              "4GB USB drive, black casing, red cap",
              "found near gate 3 by the banyan tree",
              "Batch 2026-27, MTech students only"]
        for text in ok:
            with self.subTest(text=text):
                self.assertEqual(public_text(text), text)

    def test_short_fields_reject_ids_but_allow_labels(self):
        for label in ["iPhone 03001234567", "Wallet a@example.com", "Bag 42101-1234567-1"]:
            with self.subTest(label=label):
                with self.assertRaises(ValidationError):
                    public_short(label)
        for label in ["2023-ME-123 notebook", "Room 105", "Blue backpack", "2023ME123", "Black umbrella"]:
            with self.subTest(label=label):
                self.assertEqual(public_short(label), label)

    def test_title_and_location_reject_ids(self):
        self.assertFalse(TypeForm({"kind": "Lost", "title": "Call 03001234567", "category": "Bag", "event_date": timezone.localdate().strftime("%d-%m-%Y")}).is_valid())
        self.assertFalse(LocationForm({"location": "Main Gate", "lat": "24.86", "lng": "67.001", "location_detail": "Card 42101-1234567-1"}).is_valid())

    def test_control_characters_rejected_everywhere(self):
        with self.assertRaises(ValidationError):
            public_text("black bag\x00found here")
        with self.assertRaises(ValidationError):
            public_short("jacket\u200c")

    def test_bidi_isolates_and_c1_controls_rejected(self):
        # The embeddings U+202a-U+202e were already blocked, which left the
        # bidi isolates U+2066-U+2069 able to reorder a rendered place or name.
        # Each mark goes between words: words() strips the ends first, and a
        # mark only misleads a reader when it sits inside the text.
        for mark in ("\u2066", "\u2069", "\u0085", "\u009f"):
            with self.assertRaises(ValidationError):
                public_short("jac" + mark + "ket")
            with self.assertRaises(ValidationError):
                public_text("black ba" + mark + "g found here")

    def test_meeting_place_rejects_invisible_characters(self):
        # The meeting place is the one field the other party reads to choose
        # where to meet, so it has to reject what every other field rejects.
        when = (timezone.localdate() + timedelta(days=30)).strftime("%d-%m-%y %I:%M %p")
        for mark in ("\u202e", "\u2066", "\u200d"):
            self.assertFalse(
                MeetingForm({"meeting_place": "Gulshan Chow" + mark + "rangi",
                             "meeting_at": when}).is_valid(),
                msg=f"meeting_place accepted U+{ord(mark):04x}")
        self.assertTrue(
            MeetingForm({"meeting_place": "Gulshan Chowrangi, near the fountain",
                         "meeting_at": when}).is_valid())

    def test_wizard_rejects_leaky_public_description_and_keeps_draft(self):
        owner = User.objects.create_user(username="leak@example.com", email="leak@example.com", password="Correct-horse-111!")
        client = Client()
        client.force_login(owner)
        client.get(reverse("create"))
        draft = Draft.objects.get(owner=owner, report__isnull=True)
        url = reverse("draft", args=[draft.pk])
        client.post(url + "?step=1", {"kind": "Lost", "title": "Wallet", "category": "Bag", "event_date": timezone.localdate().strftime("%d-%m-%Y")})
        response = client.post(url + "?step=2", {"description": "call me 03001234567", "contact": "03009999999"})
        draft.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("description", draft.data)

    def test_size_boundaries_reject_overage_inside_the_form(self):
        date = timezone.localdate().strftime("%d-%m-%Y")
        coords = {"lat": "24.86", "lng": "67.001"}
        self.assertTrue(TypeForm({"kind": "Lost", "title": "b" * 120, "category": "Bag", "event_date": date}).is_valid())
        self.assertFalse(TypeForm({"kind": "Lost", "title": "b" * 121, "category": "Bag", "event_date": date}).is_valid())
        self.assertTrue(DetailsForm({"description": "a" * 2000, "contact": "03009999999"}).is_valid())
        self.assertFalse(DetailsForm({"description": "a" * 2001, "contact": "03009999999"}).is_valid())
        self.assertTrue(LocationForm({"location": "Main Gate", **coords, "location_detail": "c" * 255}).is_valid())
        self.assertFalse(LocationForm({"location": "Main Gate", **coords, "location_detail": "c" * 256}).is_valid())
        self.assertFalse(DetailsForm({"description": "a" * 2000, "contact": "x" * 121}).is_valid())

    def test_step_one_accepts_original_categories_and_guides_clear_titles(self):
        from .forms import CATEGORIES
        form = TypeForm({"kind": "Found", "title": "Handbag", "category": "Bag",
                         "event_date": timezone.localdate().strftime("%d-%m-%Y")})
        self.assertTrue(form.is_valid())
        self.assertIn("clear item name", form.fields["title"].help_text)
        self.assertEqual(form.fields["title"].widget.attrs["list"], "item-title-suggestions")
        for category in ["Wallet / Purse", "Cards / IDs", "Keys", "Electronics", "Bag", "Documents", "Cash / Money", "Other"]:
            with self.subTest(category=category):
                self.assertTrue(TypeForm({"kind": "Lost", "title": "Lost item", "category": category,
                                         "event_date": timezone.localdate().strftime("%d-%m-%Y")}).is_valid())
        self.assertFalse(TypeForm({"kind": "Lost", "title": "Lost item", "category": "Unknown category",
                                  "event_date": timezone.localdate().strftime("%d-%m-%Y")}).is_valid())

    def test_allowed_characters_accept_unicode_and_reject_pure_symbols(self):
        public_text("Black jacket — zipper, côte, café 2026, naïve edit")
        public_text("Evolution of the cover, blue dot")
        with self.assertRaises(ValidationError):
            public_text("🔑🔒🔔")  # symbols only, no words

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class FlowTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(username="a@example.com", email="a@example.com", password="Correct-horse-763!")
        self.b = User.objects.create_user(username="b@example.com", email="b@example.com", password="Correct-horse-763!")
        self.c = User.objects.create_user(username="c@example.com", email="c@example.com", password="Correct-horse-763!")
        self.client.force_login(self.a)
        self.answers = {"colour": "Black", "kind": "Backpack", "material": "Fabric", "pockets": "2", "mark": "None"}

    def report(self, owner, kind):
        return Report.objects.create(owner=owner, kind=kind, title="Black backpack", category="Bag", description="Black backpack water bottle side pocket",
            location="Central Library", lat="24.86", lng="67.001", location_detail="Near entrance", event_date=timezone.localdate(), contact=owner.email, answers=self.answers)

    def test_registration_and_login(self):
        client = Client()
        response = client.post("/register/", {"first_name": "Sara", "email": "SARA@example.com", "password1": "Correct-horse-991!", "password2": "Correct-horse-991!"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="sara@example.com").exists())
        client.post("/logout/")
        self.assertEqual(client.post("/login/", {"username": "sara@example.com", "password": "Correct-horse-991!"}).status_code, 302)

    def test_details_summary_follows_step_one_without_changing_description(self):
        draft = Draft.objects.create(owner=self.a, data={
            "kind": "Lost", "title": "Keys", "category": "Keys",
            "event_date": timezone.localdate().isoformat(),
            "description": "Silver keyring with a blue tag",
        })
        url = reverse("draft", args=[draft.pk])
        response = self.client.get(url + "?step=2")
        self.assertContains(response, "You lost a set of keys.")
        self.assertContains(response, "Add details about the item")
        self.assertContains(response, "Keep card numbers, cash amounts, and hidden contents")
        self.assertEqual(response.context["form"]["description"].value(), "Silver keyring with a blue tag")
        self.client.post(url + "?step=1", {
            "kind": "Found", "title": "Cash", "category": "Cash / Money",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })
        response = self.client.get(url + "?step=2")
        self.assertContains(response, "You found some cash.")
        self.assertNotContains(response, "You lost a set of keys.")
        draft.refresh_from_db()
        self.assertEqual(draft.data["description"], "Silver keyring with a blue tag")

    def test_full_wizard_and_single_publication(self):
        response = self.client.get("/reports/new/")
        self.assertEqual(response.status_code, 302)
        url = response.url
        draft = Draft.objects.get(owner=self.a)
        self.client.post(url + "?step=1", {"kind": "Lost", "title": "Backpack", "category": "Bag", "event_date": timezone.localdate().strftime("%d-%m-%Y")})
        self.client.post(url + "?step=2", {"description": "Black backpack water bottle", "contact": "03001234567"})
        self.client.post(url + "?step=3", {"location": "Central Library", "lat": "24.86", "lng": "67.001", "location_detail": "Near entrance"})
        response = self.client.post(url + "?step=4", self.answers)
        self.assertEqual(response.status_code, 302)
        review = self.client.get(url + "?step=5")
        self.assertContains(review, "Review your report")
        response = self.client.post(url + "?step=5")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Report.objects.filter(owner=self.a).count(), 1)
        self.assertFalse(Draft.objects.filter(pk=draft.pk).exists())
        self.assertEqual(self.client.post(url + "?step=5").status_code, 404)

    def test_create_prompts_to_continue_or_start_new_draft(self):
        draft = Draft.objects.create(owner=self.a, data={"kind": "Lost", "title": "Old keys", "category": "Keys", "event_date": timezone.localdate().isoformat()})
        response = self.client.get(reverse("create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue the Lost draft")
        self.assertContains(response, "Discard draft and start new")
        self.assertContains(response, "permanently discards this saved draft and its photo")
        self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())
        response = self.client.post(reverse("create"), {"action": "new"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirm that you want to discard")
        draft.refresh_from_db()
        self.assertEqual(draft.data["title"], "Old keys")
        response = self.client.post(reverse("create"), {
            "action": "new", "confirm_discard": "yes", "discard_draft_id": str(draft.pk),
        })
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)
        self.assertFalse(Draft.objects.filter(pk=draft.pk).exists())
        self.client.get(reverse("create"))
        self.assertEqual(Draft.objects.filter(owner=self.a, report__isnull=True).count(), 1)

    def test_stale_discard_confirmation_keeps_current_draft(self):
        draft = Draft.objects.create(owner=self.a, data={"title": "Keep these keys"})
        for submitted_id in (None, str(draft.pk + 1)):
            with self.subTest(submitted_id=submitted_id):
                payload = {"action": "new", "confirm_discard": "yes"}
                if submitted_id:
                    payload["discard_draft_id"] = submitted_id
                response = self.client.post(reverse("create"), payload)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())

    def test_edit_preserves_saved_location_and_matching_answers(self):
        report = self.report(self.a, "Lost")
        report.refresh_from_db()
        response = self.client.post(reverse("edit", args=[report.pk]))
        url = response.url
        location = self.client.get(url + "?step=3").context["form"]
        self.assertEqual(location["location"].value(), report.location)
        self.assertEqual(location["location_detail"].value(), report.location_detail)
        self.assertEqual(location["lat"].value(), str(report.lat))
        self.assertEqual(location["lng"].value(), str(report.lng))
        matching = self.client.get(url + "?step=4").context["form"]
        for key, value in self.answers.items():
            self.assertEqual(matching[key].value(), value)
        response = self.client.post(url + "?step=4", self.answers)
        self.assertRedirects(response, url + "?step=5", fetch_redirect_response=False)

    def test_wizard_displays_actionable_validation_errors(self):
        draft = Draft.objects.create(owner=self.a, data={
            "kind": "Lost", "title": "Keys", "category": "Keys",
            "event_date": timezone.localdate().isoformat(), "description": "Silver keys",
        })
        url = reverse("draft", args=[draft.pk])
        response = self.client.post(url + "?step=1", {
            "kind": "Lost", "title": "Keys", "category": "Keys",
            "event_date": (timezone.localdate() + timedelta(days=1)).strftime("%d-%m-%Y"),
        })
        self.assertContains(response, "Enter a real date between 2000 and today.")
        response = self.client.post(url + "?step=2", {"description": "Silver keys", "contact": "123456"})
        self.assertContains(response, "at least 11 characters")
        response = self.client.post(url + "?step=3", {
            "location": "Library", "location_detail": "Near entrance", "lat": "91", "lng": "181",
        })
        self.assertContains(response, "less than or equal to 90")
        self.assertContains(response, "less than or equal to 180")

    def test_create_prompt_omits_kind_for_blank_draft(self):
        Draft.objects.create(owner=self.a)
        response = self.client.get(reverse("create"))
        self.assertContains(response, "Continue the draft")
        self.assertNotContains(response, "Continue the Lost draft")

    def test_login_remember_me_and_safe_redirect(self):
        for remember, next_url, destination in [
            (False, "/reports/new/", "/reports/new/"),
            (True, "https://example.com/", "/reports/new/"),
        ]:
            with self.subTest(remember=remember):
                client = Client()
                data = {"username": "A@EXAMPLE.COM", "password": "Correct-horse-763!", "next": next_url}
                if remember:
                    data["remember_me"] = "on"
                response = client.post("/login/", data)
                self.assertRedirects(response, destination, fetch_redirect_response=False)
                self.assertEqual(client.session.get_expire_at_browser_close(), not remember)
                self.assertEqual(bool(response.cookies["sessionid"]["expires"]), remember)

    def test_first_user_flow_and_report_history_navigation(self):
        newcomer = User.objects.create_user(username="new@example.com", email="new@example.com", password="Correct-horse-763!")
        client = Client()
        response = client.post("/login/", {"username": newcomer.email, "password": "Correct-horse-763!"})
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)

        client.force_login(self.a)
        self.assertRedirects(client.get(reverse("dashboard")), reverse("create"), fetch_redirect_response=False)
        first = self.report(self.a, "Lost")
        dashboard = client.get(reverse("dashboard"))
        self.assertContains(dashboard, "Your active reports")
        self.assertNotContains(dashboard, ">My reports<")
        self.report(self.a, "Found")
        dashboard = client.get(reverse("dashboard"))
        self.assertContains(dashboard, ">My reports<")
        history = client.get(reverse("reports"), {"kind": "Lost", "q": "backpack"})
        self.assertContains(history, first.display_id)
        self.assertEqual(len(history.context["page_obj"]), 1)

    def test_dashboard_hides_completed_and_rejected_matches(self):
        lost = self.report(self.a, "Lost")
        possible = Match.objects.create(lost=lost, found=self.report(self.b, "Found"), score=100)
        rejected_found = self.report(self.c, "Found")
        rejected = Match.objects.create(lost=lost, found=rejected_found, score=90, state="Rejected", rejected_by=self.a)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, reverse("match", args=[possible.pk]))
        self.assertNotContains(response, reverse("match", args=[rejected.pk]))
        self.assertEqual(response.context["possible_count"], 1)

    def test_failed_login_keeps_email_and_errors_without_session(self):
        client = Client()
        response = client.post("/login/", {
            "username": "a@example.com", "password": "Wrong-password-456!",
            "remember_me": "on", "next": "/reports/new/",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="a@example.com"')
        self.assertContains(response, 'role="alert"')
        self.assertNotContains(response, "Wrong-password-456!")
        self.assertNotIn("_auth_user_id", client.session)
        self.assertContains(response, 'name="next" value="/reports/new/"')
        csrf_client = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf_client.post("/login/", {
            "username": "a@example.com", "password": "Correct-horse-763!",
        }).status_code, 403)

    def test_wallet_dependencies(self):
        data = {"colour": "Black", "material": "Leather", "logo": "No", "contents": ["CNIC", "Cash"], "cnic_suffix": "4210112345671", "cash_range": "Below Rs. 500", "cash_notes": "Mixed notes", "mark": "None"}
        form = MatchingForm(data, category="Wallet / Purse", selection=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("bank_count", form.fields)
        self.assertNotIn("logo_name", form.fields)
        data["cnic_suffix"] = "abc"
        self.assertFalse(MatchingForm(data, category="Wallet / Purse", selection=data).is_valid())

    def test_empty_wallet_and_multiple_cards(self):
        data = {"colour": "Black", "material": "Leather", "logo": "No", "contents": [], "mark": "None"}
        self.assertTrue(MatchingForm(data, category="Wallet / Purse", selection=data).is_valid())
        data.update(contents=["Bank cards"], bank_count=2, bank_1_issuer="Other", bank_1_other="Bank A", bank_1_suffix="4111111111111111", bank_2_issuer="Other", bank_2_other="Bank B", bank_2_suffix="4222222222222222")
        self.assertTrue(MatchingForm(data, category="Wallet / Purse", selection=data).is_valid())
        del data["bank_2_suffix"]
        self.assertFalse(MatchingForm(data, category="Wallet / Purse", selection=data).is_valid())

    def test_score_eligibility_and_bounds(self):
        lost, found = self.report(self.a, "Lost"), self.report(self.b, "Found")
        self.assertEqual(score(lost, found)[0], 100)
        found.owner = self.a
        self.assertIsNone(score(lost, found))
        found.owner = self.b
        lost.answers = found.answers = {"mark": "None", "logo": "No", "contents": []}
        self.assertIsNone(score(lost, found))

    def test_complete_handover_and_privacy(self):
        lost, found = self.report(self.a, "Lost"), self.report(self.b, "Found")
        match = Match.objects.create(lost=lost, found=found, score=100)
        response = self.client.get(reverse("match", args=[match.pk]))
        self.assertNotContains(response, self.b.email)
        transition(match.pk, self.a, "propose", {"meeting_place": "NED Security Office", "meeting_at": timezone.now() + timedelta(hours=1)})
        with self.assertRaises(ValidationError):
            transition(match.pk, self.a, "accept")
        transition(match.pk, self.b, "accept")
        self.assertContains(self.client.get(reverse("match", args=[match.pk])), self.b.email)
        with self.assertRaises(ValidationError):
            transition(match.pk, self.a, "returned")
        Match.objects.filter(pk=match.pk).update(meeting_at=timezone.now() - timedelta(minutes=1))
        transition(match.pk, self.b, "returned")
        lost.refresh_from_db()
        self.assertEqual(lost.status, "Returned")
        self.assertEqual(lost.event_set.count(), 3)

    def test_access_and_management(self):
        lost = self.report(self.b, "Lost")
        self.assertEqual(self.client.get(reverse("report", args=[lost.pk])).status_code, 404)
        self.assertEqual(self.client.get("/management/").status_code, 403)
        with self.assertRaises(ValidationError):
            moderate(lost, self.a, "close")
        self.a.is_staff = True
        self.a.save()
        response = self.client.get("/management/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.b.email)
        moderate(lost, self.a, "remove")
        lost.refresh_from_db()
        self.assertEqual(lost.status, "Removed")

    def test_validation_and_draft_ownership(self):
        draft = Draft.objects.create(owner=self.b)
        self.assertEqual(self.client.get(reverse("draft", args=[draft.pk])).status_code, 404)
        form = DetailsForm({"description": "contact a@example.com", "contact": "letters"})
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)
        self.assertIn("contact", form.errors)
        self.assertFalse(TypeForm({"kind": "Lost", "title": "123", "category": "Bag", "event_date": "31-02-2026"}).is_valid())

    def test_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.a)
        self.assertEqual(client.post("/reports/1/edit/").status_code, 403)

    def test_competing_handovers_and_locked_edit(self):
        lost = self.report(self.a, "Lost")
        first = Match.objects.create(lost=lost, found=self.report(self.b, "Found"), score=100)
        other = Match.objects.create(lost=lost, found=self.report(self.c, "Found"), score=100)
        meeting = {"meeting_place": "NED Security Office", "meeting_at": timezone.now() + timedelta(hours=1)}
        transition(first.pk, self.a, "propose", meeting)
        with self.assertRaises(ValidationError):
            transition(other.pk, self.c, "propose", meeting)
        self.client.post(reverse("edit", args=[lost.pk]))
        self.assertEqual(Draft.objects.filter(report=lost).count(), 0)
        transition(first.pk, self.b, "reject")
        transition(other.pk, self.c, "propose", meeting)

    def test_category_change_clears_old_answers(self):
        draft = Draft.objects.create(owner=self.a, data={"category": "Bag", "answers": self.answers})
        self.client.post(reverse("draft", args=[draft.pk]) + "?step=1", {"kind": "Lost", "title": "Wallet", "category": "Wallet / Purse", "event_date": timezone.localdate().strftime("%d-%m-%Y")})
        draft.refresh_from_db()
        self.assertNotIn("answers", draft.data)

    def test_review_escapes_text_and_invalid_submission_keeps_draft(self):
        draft = Draft.objects.create(owner=self.a, data={"kind": "Lost", "title": "<script>alert(1)</script>", "category": "Bag", "event_date": timezone.localdate().isoformat(), "description": "Backpack", "location": "Main Gate", "lat": "24.86", "lng": "67.001", "location_detail": "near gate", "answers": {}})
        url = reverse("draft", args=[draft.pk]) + "?step=5"
        response = self.client.get(url)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())
        self.assertEqual(Report.objects.count(), 0)

    def test_bank_card_order_does_not_affect_score(self):
        lost, found = self.report(self.a, "Lost"), self.report(self.b, "Found")
        lost.category = found.category = "Wallet / Purse"
        lost.answers = {"colour": "Black", "material": "Leather", "bank_1_issuer": "Other", "bank_1_other": "Bank A", "bank_1_suffix": "4111111111111111", "bank_2_issuer": "Other", "bank_2_other": "Bank B", "bank_2_suffix": "4222222222222222"}
        found.answers = {"colour": "Black", "material": "Leather", "bank_1_issuer": "Other", "bank_1_other": "Bank B", "bank_1_suffix": "4222222222222222", "bank_2_issuer": "Other", "bank_2_other": "Bank A", "bank_2_suffix": "4111111111111111"}
        self.assertEqual(score(lost, found)[0], 100)

    def test_recalculation_updates_existing_match_score(self):
        from .services import recalculate
        lost, found = self.report(self.a, "Lost"), self.report(self.b, "Found")
        match = Match.objects.create(lost=lost, found=found, score=100, breakdown={"old": 100})
        found.lat = "25.00000000"
        found.lng = "67.50000000"
        found.save(update_fields=["lat", "lng"])
        recalculate(lost)
        refreshed = Match.objects.get(lost=lost, found=found)
        self.assertNotEqual(refreshed.pk, match.pk)
        self.assertEqual(refreshed.score, score(lost, found)[0])

    def test_dismissed_match_can_only_be_restored_by_dismisser(self):
        lost, found = self.report(self.a, "Lost"), self.report(self.b, "Found")
        match = Match.objects.create(lost=lost, found=found, score=100)
        transition(match.pk, self.a, "reject")
        match.refresh_from_db()
        self.assertEqual(match.state, "Rejected")
        self.assertEqual(match.rejected_by_id, self.a.pk)
        transition(match.pk, self.a, "restore")
        match.refresh_from_db()
        self.assertEqual(match.state, "Possible Match")
        self.assertIsNone(match.rejected_by_id)
        transition(match.pk, self.b, "reject")
        with self.assertRaises(ValidationError):
            transition(match.pk, self.a, "restore")

    def test_meeting_form_uses_pakistan_date_format(self):
        meeting = (timezone.localtime(timezone.now()) + timedelta(hours=1)).strftime("%d-%m-%y %I:%M %p")
        form = MeetingForm({"meeting_place": "NED Security Office", "meeting_at": meeting})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(timezone.is_aware(form.cleaned_data["meeting_at"]))

    def test_meeting_time_requires_two_digits_everywhere(self):
        # Day, month and hour used to accept a single digit that was then read
        # as zero-padded, while minutes stayed strict. All five parts are strict
        # now, and the browser pattern and the server guard share one constant.
        when = (timezone.localtime(timezone.now()) + timedelta(days=30))
        full = when.strftime("%d-%m-%y %I:%M %p")

        def check(value, expected):
            form = MeetingForm({"meeting_place": "NED Security Office",
                                "meeting_at": value})
            self.assertEqual(form.is_valid(), expected, msg=f"{value!r} -> {form.errors}")

        check(full, True)
        for single in ("5-10-26 03:00 PM", "15-10-26 3:00 PM", "15-1-26 03:00 PM",
                       "15-10-26 03:5 PM", "5-1-26 3:5 PM"):
            check(single, False)
        for rejected in ("15-10-2026 03:00 PM", "15/10/26 03:00 PM",
                         "15-10-26 15:00", "15-10-26 03:00 XM"):
            check(rejected, False)
        # The meridiem is case-insensitive, matching %p on the parsing side.
        check(full[:-2] + "pm", True)
        check(full[:-2] + "Pm", True)

        field = MeetingForm().fields["meeting_at"]
        self.assertEqual(field.widget.attrs["pattern"], MEETING_TIME_PATTERN)
        self.assertEqual(field.widget.attrs["maxlength"], 18)

    def test_meeting_place_is_free_text_and_has_no_department(self):
        meeting = (timezone.localtime(timezone.now()) + timedelta(hours=1)).strftime("%d-%m-%y %I:%M %p")
        form = MeetingForm({"meeting_place": "Nazimabad Chowrangi, near the dry-fruit shop", "meeting_at": meeting})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("department", form.fields)
        self.assertEqual(form.cleaned_data["meeting_place"], "Nazimabad Chowrangi, near the dry-fruit shop")

    def test_location_score_uses_haversine_distance_bands(self):
        from .services import location_score
        lost = self.report(self.a, "Lost")
        found = self.report(self.b, "Found")
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
                self.assertEqual(location_score(lost, found), expected)
        lost.lat = lost.lng = None
        self.assertEqual(location_score(lost, found), 0)

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class QRScanTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner@example.com", email="owner@example.com", password="Correct-horse-763!")
        self.finder = User.objects.create_user(username="finder@example.com", email="finder@example.com", password="Correct-horse-763!")
        self.answers = {"colour": "Black", "kind": "Backpack", "material": "Fabric", "pockets": "2", "mark": "None"}

    def lost_report(self, **kwargs):
        defaults = dict(owner=self.owner, kind="Lost", title="Black backpack", category="Bag", description="Black backpack water bottle side pocket",
            location="Central Library", lat="24.86", lng="67.001", location_detail="Near entrance", event_date=timezone.localdate(), contact=self.owner.email, answers=self.answers)
        defaults.update(kwargs)
        return Report.objects.create(**defaults)

    def test_qr_view_returns_png(self):
        report = self.lost_report()
        response = self.client.get(reverse("report-qr", args=[report.public_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        from PIL import Image
        from io import BytesIO
        image = Image.open(BytesIO(response.content))
        self.assertEqual(image.format, "PNG")
        self.assertGreaterEqual(image.width, 200)
        self.assertEqual(image.width, image.height)

    def test_public_report_qr_scan_requires_login_then_preserves_return_destination(self):
        report = self.lost_report()
        scan_url = reverse("report-found", args=[report.public_id])
        response = self.client.get(scan_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/login/?next={scan_url}")

    def test_found_view_requires_login(self):
        report = self.lost_report()
        response = self.client.get(reverse("report-found", args=[report.public_id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_found_view_seeds_draft_with_public_fields(self):
        report = self.lost_report()
        self.client.force_login(self.finder)
        response = self.client.get(reverse("report-found", args=[report.public_id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("?step=3", response.url)
        draft = Draft.objects.get(owner=self.finder, report__isnull=True)
        self.assertEqual(draft.data["kind"], "Found")
        self.assertEqual(draft.data["category"], "Bag")
        self.assertEqual(draft.data["title"], "Black backpack")
        self.assertEqual(draft.data["location"], "Central Library")
        self.assertEqual(draft.data["event_date"], timezone.localdate().isoformat())

    def test_scan_does_not_copy_lost_coordinates(self):
        report = self.lost_report()
        self.client.force_login(self.finder)
        self.client.get(reverse("report-found", args=[report.public_id]))
        draft = Draft.objects.get(owner=self.finder, report__isnull=True)
        # The coarse place name stays as a confirmable hint, but the exact
        # pin does not. Asserting the hint too is the point: it stops a future
        # change quietly re-adding the coordinates.
        self.assertNotIn("lat", draft.data)
        self.assertNotIn("lng", draft.data)
        self.assertEqual(draft.data["location"], "Central Library")

    def test_owner_scanning_own_qr_gets_notice_and_no_draft(self):
        report = self.lost_report()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("report-found", args=[report.public_id]))
        self.assertRedirects(response, reverse("report", args=[report.pk]))
        self.assertFalse(Draft.objects.filter(owner=self.owner, report__isnull=True).exists())

    def test_second_unverified_account_can_seed_a_found_draft_from_the_same_qr(self):
        # Accounts are not real-world identities. The QR seeds a report but does
        # not prove possession, so a person controlling another account can do this.
        report = self.lost_report()
        second_account = User.objects.create_user(
            username="second-owner-identity@example.com",
            email="second-owner-identity@example.com",
            password="Correct-horse-763!",
        )
        self.client.force_login(second_account)
        response = self.client.get(reverse("report-found", args=[report.public_id]))
        self.assertEqual(response.status_code, 302)
        draft = Draft.objects.get(owner=second_account, report__isnull=True)
        self.assertEqual(draft.data["kind"], "Found")
        self.assertFalse(Report.objects.filter(owner=second_account).exists())

    def test_qr_box_only_renders_on_lost_reports(self):
        lost = self.lost_report()
        found = self.lost_report(kind="Found", title="Black backpack seen", contact=self.finder.email)
        self.client.force_login(self.owner)
        page = self.client.get(reverse("report", args=[lost.pk]))
        self.assertContains(page, reverse("report-qr", args=[lost.public_id]))
        self.assertContains(page, "Share this code with the finder")
        self.assertContains(page, "does not verify who has the item")
        page = self.client.get(reverse("report", args=[found.pk]))
        self.assertNotContains(page, reverse("report-qr", args=[found.public_id]))

    def test_competing_match_parked_while_reserved_and_usable_after(self):
        lost = self.lost_report()
        found1 = self.lost_report(kind="Found", title="Black backpack seen", contact=self.finder.email, owner=self.finder)
        third = User.objects.create_user(username="third@example.com", email="third@example.com", password="Correct-horse-763!")
        found2 = self.lost_report(kind="Found", title="Backpack at library", contact=third.email, owner=third)
        m1 = Match.objects.create(lost=lost, found=found1, score=80)
        m2 = Match.objects.create(lost=lost, found=found2, score=70)
        meeting = {"meeting_place": "NED Security Office", "meeting_at": timezone.now() + timedelta(days=1)}
        transition(m1.pk, self.owner, "propose", meeting=meeting)
        m2.refresh_from_db()
        self.assertEqual(m2.state, "Possible Match")
        self.client.force_login(third)
        self.assertNotContains(self.client.get(reverse("dashboard")), reverse("match", args=[m2.pk]))
        with self.assertRaises(ValidationError):
            transition(m2.pk, third, "propose", meeting=meeting)
        transition(m1.pk, self.finder, "reject")
        transition(m2.pk, self.owner, "propose", meeting=meeting)
        m2.refresh_from_db()
        self.assertEqual(m2.state, "Handover Proposed")

    def test_scan_into_used_draft_clears_stale_lost_fields(self):
        report = self.lost_report()
        self.client.force_login(self.finder)
        draft = Draft.objects.create(owner=self.finder, data={
            "kind": "Lost", "title": "My keys", "category": "Keys",
            "event_date": timezone.localdate().isoformat(),
            "description": "silver keys with red fob", "location": "Main Gate",
            "location_detail": "near the bench", "contact": self.finder.email,
            "answers": {"count": "3", "kind": "Home", "fob": "Red", "mark": "None"},
        })
        self.client.get(reverse("report-found", args=[report.public_id]))
        draft.refresh_from_db()
        self.assertEqual(draft.data["kind"], "Found")
        self.assertEqual(draft.data["title"], "Black backpack")
        self.assertNotIn("description", draft.data)
        self.assertNotIn("location_detail", draft.data)
        self.assertNotIn("contact", draft.data)
        self.assertNotIn("answers", draft.data)

    def test_closed_and_reserved_reports_show_notice(self):
        for kwargs in [{"status": "Returned"}, {"reserved": True}]:
            with self.subTest(kwargs=kwargs):
                report = self.lost_report(**kwargs)
                self.client.force_login(self.finder)
                response = self.client.get(reverse("report-found", args=[report.public_id]))
                self.assertContains(response, "already been resolved")
                self.assertFalse(Draft.objects.filter(owner=self.finder).exists())
