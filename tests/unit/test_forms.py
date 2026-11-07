"""Unit tests for ``core.forms``: validators, per-category schemas, and forms."""

from datetime import timedelta
from io import BytesIO

from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from core.forms import (
    BAD_CHARS,
    CATEGORIES,
    DetailsForm,
    EmailLogin,
    LocationForm,
    MatchingForm,
    MeetingForm,
    QRLabelForm,
    Registration,
    TypeForm,
    choices,
    public_short,
    public_text,
    schema,
    words,
)
from tests.support import (
    BAG_ANSWERS,
    CATEGORY_ANSWERS,
    PASSWORD,
    make_user,
    meeting_field_value,
    png_upload,
)


def type_data(**overrides):
    value = {
        "kind": "Lost",
        "title": "Blue backpack",
        "category": "Bag",
        "event_date": timezone.localdate().strftime("%d-%m-%Y"),
    }
    value.update(overrides)
    return value


def details_data(**overrides):
    value = {
        "description": "Blue fabric backpack with two front pockets",
        "contact": "03001234567",
    }
    value.update(overrides)
    return value


def location_data(**overrides):
    value = {
        "location": "Central Library",
        "lat": "24.86",
        "lng": "67.001",
        "location_detail": "Beside the entrance",
    }
    value.update(overrides)
    return value


class TextScreeningTests(TestCase):
    def test_words_strips_surrounding_whitespace(self):
        self.assertEqual(words("  Blue backpack  "), "Blue backpack")

    def test_words_rejects_invisible_and_control_characters(self):
        for value in ("Blue\u200bbackpack", "Blue\u202ebackpack", "\ufeffBlue", "Blue\x00bag"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValidationError):
                    words(value)

    def test_words_allows_newlines_and_tabs(self):
        self.assertEqual(words("Blue bag\nwith\tzip"), "Blue bag\nwith\tzip")

    def test_words_requires_at_least_one_letter(self):
        for value in ("12345", "---", "  "):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    words(value)

    def test_public_short_rejects_phones_emails_and_ids(self):
        for value in (
            "call 03001234567",
            "0300-1234567",
            "sara@example.test",
            "CNIC 42101-1234567-1",
            "4210112345671",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    public_short(value)

    def test_public_short_accepts_item_labels(self):
        for value in ("Blue backpack", "Block 7", "Keys 2", "NED Student Card"):
            with self.subTest(value=value):
                self.assertEqual(public_short(value), value)

    def test_public_text_rejects_identifiers(self):
        for value in (
            "email sara@example.test",
            "sara at example dot com",
            "roll number 2023-ME-123",
            "registration no 98765",
            "card ending 1234",
            "last 4 digits 1234",
            "call me on 03001234567",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    public_text(value)

    def test_public_text_accepts_plain_descriptions(self):
        for value in (
            "Blue fabric backpack with two front pockets",
            "Black wallet, small scratch near the clasp",
            "Silver keys on a plastic fob",
        ):
            with self.subTest(value=value):
                self.assertEqual(public_text(value), value)

    def test_bad_chars_does_not_flag_ordinary_punctuation(self):
        self.assertFalse(BAD_CHARS.search("Wallet / Purse, Rs. 500 (approx.)"))

    def test_choices_builds_value_label_pairs(self):
        self.assertEqual(choices(["Lost", "Found"]), [("Lost", "Lost"), ("Found", "Found")])


class TypeFormTests(TestCase):
    def test_a_complete_type_step_is_valid(self):
        form = TypeForm(type_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["event_date"], timezone.localdate())

    def test_found_reports_are_valid(self):
        self.assertTrue(TypeForm(type_data(kind="Found")).is_valid())

    def test_a_future_event_date_is_rejected(self):
        future = timezone.localdate() + timedelta(days=1)
        form = TypeForm(type_data(event_date=future.strftime("%d-%m-%Y")))
        self.assertFalse(form.is_valid())
        self.assertIn("between 2000 and today", form.errors["event_date"][0])

    def test_dates_before_2000_are_rejected(self):
        form = TypeForm(type_data(event_date="31-12-1999"))
        self.assertFalse(form.is_valid())
        self.assertIn("between 2000 and today", form.errors["event_date"][0])

    def test_an_impossible_calendar_date_is_rejected(self):
        form = TypeForm(type_data(event_date="31-02-2026"))
        self.assertFalse(form.is_valid())
        self.assertIn("event_date", form.errors)

    def test_the_date_must_use_day_month_year(self):
        form = TypeForm(type_data(event_date="2026-01-15"))
        self.assertFalse(form.is_valid())
        self.assertIn("event_date", form.errors)

    def test_the_title_rejects_contact_details(self):
        form = TypeForm(type_data(title="Call 03001234567"))
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_the_title_has_a_length_limit(self):
        form = TypeForm(type_data(title="b" * 121))
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_the_title_must_contain_words(self):
        form = TypeForm(type_data(title="12345"))
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)


class DetailsFormTests(TestCase):
    def test_a_complete_details_step_is_valid(self):
        form = DetailsForm(details_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_phone_numbers_must_be_eleven_digits_starting_with_zero(self):
        for value in ("0300123456", "030012345678", "13001234567", "0300-1234567", "0300123456a"):
            with self.subTest(value=value):
                form = DetailsForm(details_data(contact=value))
                self.assertFalse(form.is_valid())
                self.assertIn("contact", form.errors)

    def test_the_public_description_rejects_private_identifiers(self):
        form = DetailsForm(details_data(description="call me on 03001234567"))
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)

    def test_the_description_has_a_length_limit(self):
        form = DetailsForm(details_data(description="b" * 2001))
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)

    def test_a_valid_photo_is_accepted(self):
        upload = png_upload()
        form = DetailsForm(details_data(), {"photo": upload})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["photo"], upload)

    def test_an_oversized_image_is_rejected(self):
        form = DetailsForm(details_data(), {"photo": png_upload(width=6001, height=1)})
        self.assertFalse(form.is_valid())
        self.assertIn("too large", form.errors["photo"][0])

    def test_a_non_jpeg_png_or_webp_image_is_rejected(self):
        buffer = BytesIO()
        Image.new("P", (10, 10)).save(buffer, format="GIF")
        upload = SimpleUploadedFile("item.gif", buffer.getvalue(), content_type="image/gif")
        form = DetailsForm(details_data(), {"photo": upload})
        self.assertFalse(form.is_valid())
        self.assertIn("JPEG, PNG, or WebP", form.errors["photo"][0])

    def test_bytes_that_are_not_an_image_are_rejected(self):
        upload = SimpleUploadedFile("item.png", b"not an image", content_type="image/png")
        form = DetailsForm(details_data(), {"photo": upload})
        self.assertFalse(form.is_valid())
        self.assertIn("photo", form.errors)

    def test_removing_a_photo_is_optional_and_needs_no_upload(self):
        form = DetailsForm(details_data(remove_photo=True))
        self.assertTrue(form.is_valid(), form.errors)


class QRLabelFormTests(TestCase):
    def test_a_valid_label_is_accepted(self):
        form = QRLabelForm({"item_name": "Blue backpack", "contact_phone": "03001234567"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_the_label_phone_must_be_eleven_digits_starting_with_zero(self):
        for value in ("0300123456", "030012345678", "0300123456a"):
            with self.subTest(value=value):
                form = QRLabelForm({"item_name": "Bag", "contact_phone": value})
                self.assertFalse(form.is_valid())
                self.assertIn("contact_phone", form.errors)

    def test_the_item_name_rejects_contact_details(self):
        form = QRLabelForm({"item_name": "Call 03001234567", "contact_phone": "03001234567"})
        self.assertFalse(form.is_valid())
        self.assertIn("item_name", form.errors)


class LocationFormTests(TestCase):
    def test_a_complete_location_step_is_valid(self):
        form = LocationForm(location_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_coordinates_must_stay_within_the_globe(self):
        for field, value in (
            ("lat", "90.1"), ("lat", "-90.1"), ("lng", "180.1"), ("lng", "-180.1"),
        ):
            with self.subTest(field=field, value=value):
                form = LocationForm(location_data(**{field: value}))
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_the_extremes_of_latitude_and_longitude_are_allowed(self):
        for field, value in (
            ("lat", "90"), ("lat", "-90"), ("lng", "180"), ("lng", "-180"),
        ):
            with self.subTest(field=field, value=value):
                form = LocationForm(location_data(**{field: value}))
                self.assertTrue(form.is_valid(), form.errors)

    def test_coordinates_are_required(self):
        form = LocationForm(location_data(lat="", lng=""))
        self.assertFalse(form.is_valid())
        self.assertIn("lat", form.errors)
        self.assertIn("lng", form.errors)

    def test_the_place_and_detail_reject_contact_details(self):
        for field in ("location", "location_detail"):
            with self.subTest(field=field):
                form = LocationForm(location_data(**{field: "sara@example.test"}))
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_the_location_description_has_a_length_limit(self):
        form = LocationForm(location_data(location_detail="b" * 256))
        self.assertFalse(form.is_valid())
        self.assertIn("location_detail", form.errors)


class CategorySchemaTests(TestCase):
    def test_every_category_has_a_colour_and_a_mark(self):
        for category in CATEGORIES:
            with self.subTest(category=category):
                fields = schema(category, {})
                self.assertIn("colour", fields)
                self.assertIn("mark", fields)

    def test_wallet_questions_follow_the_selected_contents_and_logo(self):
        fields = schema("Wallet / Purse", {
            "logo": "Yes",
            "contents": ["CNIC", "Bank cards", "Cash", "Driving licence", "Other items"],
            "bank_count": 3,
            "bank_1_issuer": "Other",
        })
        for key in (
            "material", "logo", "logo_name", "contents", "cnic_suffix", "bank_count",
            "bank_1_issuer", "bank_1_suffix", "bank_1_other", "bank_2_suffix",
            "bank_3_suffix", "cash_range", "cash_notes", "licence_issuer",
            "other_contents",
        ):
            with self.subTest(key=key):
                self.assertIn(key, fields)

    def test_a_wallet_without_contents_only_asks_the_common_questions(self):
        fields = schema("Wallet / Purse", {"contents": []})
        self.assertNotIn("cnic_suffix", fields)
        self.assertNotIn("bank_count", fields)
        self.assertNotIn("cash_range", fields)

    def test_the_bank_card_count_is_clamped_to_the_supported_range(self):
        for raw, expected in (("abc", 1), (0, 1), (9, 5), (2, 2)):
            with self.subTest(raw=raw):
                fields = schema("Wallet / Purse", {
                    "contents": ["Bank cards"], "bank_count": raw,
                })
                suffixes = [key for key in fields if key.endswith("_suffix")]
                self.assertEqual(len(suffixes), expected)

    def test_card_issuers_and_suffix_lengths_depend_on_the_card_type(self):
        cnic = schema("Cards / IDs", {"card_type": "CNIC"})
        self.assertEqual(cnic["suffix"].widget.attrs["maxlength"], 13)
        self.assertEqual(
            [value for value, _ in cnic["issuer"].choices], ["", "NADRA", "Other"],
        )

        student = schema("Cards / IDs", {"card_type": "NED Student Card"})
        self.assertEqual(student["suffix"].widget.attrs["maxlength"], 4)
        self.assertIn("Computer Science & Information Technology (CSIT)",
                      [value for value, _ in student["issuer"].choices])

        bank = schema("Cards / IDs", {"card_type": "Bank Card"})
        self.assertEqual(bank["suffix"].widget.attrs["maxlength"], 16)
        self.assertIn("HBL", [value for value, _ in bank["issuer"].choices])

    def test_an_other_issuer_adds_a_free_text_name(self):
        fields = schema("Cards / IDs", {"card_type": "CNIC", "issuer": "Other"})
        self.assertIn("issuer_other", fields)

    def test_the_remaining_categories_ask_their_own_questions(self):
        expected = {
            "Keys": {"count", "kind", "fob"},
            "Bag": {"kind", "material", "pockets"},
            "Electronics": {"kind", "case", "brand"},
            "Documents": {"kind", "holder", "issuer"},
            "Cash / Money": {"amount", "notes"},
            "Other": set(),
        }
        for category, keys in expected.items():
            with self.subTest(category=category):
                fields = schema(category, {})
                self.assertTrue(keys.issubset(fields))
                if category == "Other":
                    self.assertEqual(set(fields), {"colour", "mark"})


class MatchingFormTests(TestCase):
    def test_every_category_accepts_its_complete_answers(self):
        for category, answers in CATEGORY_ANSWERS.items():
            with self.subTest(category=category):
                form = MatchingForm(answers, category=category, selection=answers)
                self.assertTrue(form.is_valid(), form.errors)

    def test_missing_answers_are_rejected(self):
        form = MatchingForm({}, category="Bag")
        self.assertFalse(form.is_valid())
        for key in BAG_ANSWERS:
            self.assertIn(key, form.errors)

    def test_every_question_explains_that_answers_stay_private(self):
        form = MatchingForm({}, category="Bag")
        for name, field in form.fields.items():
            with self.subTest(field=name):
                self.assertIn("not visible to other users or staff",
                              field.widget.attrs["title"])

    def test_unknown_keys_are_not_added_to_the_form(self):
        form = MatchingForm({**BAG_ANSWERS, "secret": "x"}, category="Bag")
        self.assertNotIn("secret", form.fields)


class MeetingFormTests(TestCase):
    def test_the_shared_pattern_matches_the_documented_format(self):
        from core.forms import MEETING_TIME_PATTERN
        import re

        self.assertRegex(meeting_field_value(), "^" + MEETING_TIME_PATTERN + "$")

    def test_a_future_meeting_is_accepted_and_made_aware(self):
        form = MeetingForm({
            "meeting_place": "NED Security Office",
            "meeting_at": meeting_field_value(),
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(timezone.is_aware(form.cleaned_data["meeting_at"]))

    def test_lower_case_am_and_pm_are_accepted(self):
        form = MeetingForm({
            "meeting_place": "NED Security Office",
            "meeting_at": meeting_field_value().lower(),
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_a_past_meeting_is_rejected(self):
        form = MeetingForm({
            "meeting_place": "NED Security Office",
            "meeting_at": meeting_field_value(days=-30),
        })
        self.assertFalse(form.is_valid())
        self.assertIn("future meeting", form.errors["meeting_at"][0])

    def test_single_digit_hours_and_minutes_are_rejected(self):
        for value in ("1-09-26 09:25 PM", "01-09-26 9:25 PM", "01-09-26 09:5 PM"):
            with self.subTest(value=value):
                form = MeetingForm({"meeting_place": "Office", "meeting_at": value})
                self.assertFalse(form.is_valid())
                self.assertIn("DD-MM-YY hh:mm AM/PM", form.errors["meeting_at"][0])

    def test_an_impossible_date_is_rejected(self):
        form = MeetingForm({"meeting_place": "Office", "meeting_at": "32-13-26 09:25 PM"})
        self.assertFalse(form.is_valid())
        self.assertIn("meeting_at", form.errors)

    def test_the_place_must_contain_words(self):
        form = MeetingForm({"meeting_place": "12345", "meeting_at": meeting_field_value()})
        self.assertFalse(form.is_valid())
        self.assertIn("meeting_place", form.errors)


class RegistrationTests(TestCase):
    def registration_data(self, **overrides):
        value = {
            "first_name": "Sara Ahmed",
            "email": "Sara@Example.Test",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        value.update(overrides)
        return value

    def test_saving_lower_cases_the_email_and_uses_it_as_the_username(self):
        form = Registration(self.registration_data())
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "sara@example.test")
        self.assertEqual(user.username, "sara@example.test")
        self.assertTrue(user.check_password(PASSWORD))

    def test_an_email_is_unique_without_regard_to_case(self):
        make_user("sara@example.test")
        form = Registration(self.registration_data(email="SARA@EXAMPLE.TEST"))
        self.assertFalse(form.is_valid())
        self.assertIn("already registered", form.errors["email"][0])

    def test_an_email_already_used_as_a_username_is_rejected(self):
        from core.models import User

        User.objects.create_user(username="taken@example.test", email="other@example.test")
        form = Registration(self.registration_data(email="taken@example.test"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_mismatched_passwords_are_rejected(self):
        form = Registration(self.registration_data(password2="Different-pass-9!"))
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_a_weak_password_is_rejected(self):
        form = Registration(self.registration_data(password1="12345678", password2="12345678"))
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_the_name_must_contain_words(self):
        form = Registration(self.registration_data(first_name="12345"))
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)

    def test_invalid_fields_are_marked_for_screen_readers(self):
        form = Registration({})
        self.assertFalse(form.is_valid())
        email = form.fields["email"].widget.attrs
        self.assertEqual(email["aria-invalid"], "true")
        self.assertEqual(email["aria-describedby"], "id_email_error")


class EmailLoginTests(TestCase):
    def test_the_email_is_stripped_and_lower_cased(self):
        # AuthenticationForm takes ``request`` first, so pass ``data`` by name.
        form = EmailLogin(data={"username": " Owner@Example.Test ", "password": "wrong"})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.cleaned_data["username"], "owner@example.test")

    def test_the_password_field_has_a_placeholder(self):
        form = EmailLogin()
        self.assertEqual(
            form.fields["password"].widget.attrs["placeholder"], "Enter your password",
        )

    def test_invalid_credentials_mark_the_fields_for_screen_readers(self):
        form = EmailLogin(data={})
        self.assertFalse(form.is_valid())
        for name in ("username", "password"):
            with self.subTest(field=name):
                attrs = form.fields[name].widget.attrs
                self.assertEqual(attrs["aria-invalid"], "true")
                self.assertEqual(attrs["aria-describedby"], f"id_{name}_error")
