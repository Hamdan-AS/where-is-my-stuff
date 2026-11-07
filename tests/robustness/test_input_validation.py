"""Hostile and boundary input: invisible characters, identifiers, limits, dates.

These tests ask a different question from the behaviour layer: not "does the
happy path work?" but "what happens when someone deliberately sends the worst
value the field accepts?". Validation is exercised through the real forms and,
where the browser is the boundary, through HTTP.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.forms import (
    DetailsForm,
    LocationForm,
    MatchingForm,
    MeetingForm,
    QRLabelForm,
    Registration,
    TypeForm,
)
from core.models import Draft, QRLabel, Report
from tests.support import PASSWORD, make_user, meeting_field_value, start_wizard


def type_data(**overrides):
    data = {
        "kind": "Lost",
        "title": "Blue backpack",
        "category": "Bag",
        "event_date": timezone.localdate().strftime("%d-%m-%Y"),
    }
    data.update(overrides)
    return data


def details_data(**overrides):
    data = {
        "description": "Blue fabric backpack with two front pockets",
        "contact": "03001234567",
    }
    data.update(overrides)
    return data


def location_data(**overrides):
    data = {
        "location": "Central Library",
        "lat": "24.8607",
        "lng": "67.0011",
        "location_detail": "Beside the entrance",
    }
    data.update(overrides)
    return data


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class InvisibleCharacterTests(TestCase):
    """Control, zero-width, and bidi characters must be rejected, never cleaned."""

    HOSTILE = [
        "Blue\u200bbackpack",   # zero-width space
        "Blue\u202ebackpack",   # right-to-left override
        "Blue\x00backpack",     # NUL
        "Blue\x07backpack",     # bell
        "Blue\ufeffbackpack",   # BOM
    ]

    def test_public_short_fields_reject_invisible_characters(self):
        for value in self.HOSTILE:
            with self.subTest(value=repr(value)):
                form = TypeForm(type_data(title=value))
                self.assertFalse(form.is_valid())
                self.assertIn("special or invisible characters", str(form.errors))

    def test_public_text_fields_reject_invisible_characters(self):
        for value in self.HOSTILE:
            with self.subTest(value=repr(value)):
                form = DetailsForm(details_data(description=value))
                self.assertFalse(form.is_valid())
                self.assertIn("special or invisible characters", str(form.errors))

    def test_location_and_qr_names_reject_invisible_characters(self):
        self.assertFalse(LocationForm(location_data(location="Library\u200b")).is_valid())
        self.assertFalse(
            LocationForm(location_data(location_detail="Entrance\u202e")).is_valid()
        )
        self.assertFalse(
            QRLabelForm({"item_name": "Bag\u2066", "contact_phone": "03001234567"}).is_valid()
        )

    def test_registration_rejects_an_invisible_character_in_the_name(self):
        form = Registration({
            "first_name": "Sara\u200bAhmed",
            "email": "sara@example.test",
            "password1": PASSWORD,
            "password2": PASSWORD,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)

    def test_newlines_and_tabs_remain_legal_in_a_multi_line_description(self):
        form = DetailsForm(details_data(
            description="Blue backpack\nwith a stitched patch\tand a silver zip",
        ))
        self.assertTrue(form.is_valid(), form.errors)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PublicIdentifierTests(TestCase):
    """Phone numbers, emails, and IDs belong in private fields only.

    Short fields (title and place) deliberately screen only unmistakable
    personal data: a bare roll number such as ``2023-ME-123`` is also a
    plausible item label. The long public description uses the fuller
    phrase-aware screen. This split is covered by ``core.tests``.
    """

    UNMISTAKABLE = [
        "call me on 03001234567",
        "0300-1234567",
        "0300.123.4567",
        "sara@example.test",
        "CNIC 42101-1234567-1",
    ]
    PHRASE_IDENTIFIERS = [
        "sara at example dot com",
        "roll number 2023-ME-123",
        "registration no 98765",
        "card ending 1234",
        "last 4 digits 1234",
    ]
    IDENTIFIERS = UNMISTAKABLE + PHRASE_IDENTIFIERS

    def test_public_title_rejects_unmistakable_identifiers(self):
        for value in self.UNMISTAKABLE:
            with self.subTest(value=value):
                form = TypeForm(type_data(title=value))
                self.assertFalse(form.is_valid(), value)

    def test_public_description_rejects_identifiers(self):
        for value in self.IDENTIFIERS:
            with self.subTest(value=value):
                form = DetailsForm(details_data(description=value))
                self.assertFalse(form.is_valid(), value)

    def test_public_location_rejects_unmistakable_identifiers(self):
        for value in self.UNMISTAKABLE:
            with self.subTest(value=value):
                form = LocationForm(location_data(location=value))
                self.assertFalse(form.is_valid(), value)

    def test_the_same_values_are_accepted_in_private_fields(self):
        # The contact field and matching answers are where these identifiers
        # are allowed to live.
        form = DetailsForm(details_data(contact="03001234567"))
        self.assertTrue(form.is_valid(), form.errors)
        matching = MatchingForm(
            {"colour": "Blue", "kind": "Backpack", "material": "Fabric",
             "pockets": "2", "mark": "Scratch"},
            category="Bag",
        )
        self.assertTrue(matching.is_valid(), matching.errors)

    def test_a_title_must_contain_words_not_only_numbers_or_punctuation(self):
        for value in ("12345", "!!!", "---", "    "):
            with self.subTest(value=repr(value)):
                self.assertFalse(TypeForm(type_data(title=value)).is_valid())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class LengthAndFormatBoundaryTests(TestCase):
    def test_title_length_boundary(self):
        self.assertTrue(TypeForm(type_data(title="a" * 120)).is_valid())
        self.assertFalse(TypeForm(type_data(title="a" * 121)).is_valid())

    def test_description_length_boundary(self):
        self.assertTrue(DetailsForm(details_data(description="a" * 2000)).is_valid())
        self.assertFalse(DetailsForm(details_data(description="a" * 2001)).is_valid())

    def test_location_length_boundaries(self):
        self.assertTrue(LocationForm(location_data(location="a" * 100)).is_valid())
        self.assertFalse(LocationForm(location_data(location="a" * 101)).is_valid())
        self.assertTrue(
            LocationForm(location_data(location_detail="a" * 255)).is_valid()
        )
        self.assertFalse(
            LocationForm(location_data(location_detail="a" * 256)).is_valid()
        )

    def test_contact_must_be_exactly_eleven_digits_starting_with_zero(self):
        for value in (
            "03001234567",   # valid
        ):
            self.assertTrue(DetailsForm(details_data(contact=value)).is_valid(), value)
        for value in (
            "0300123456",    # ten digits
            "030012345678",  # twelve digits
            "13001234567",   # does not start with zero
            "0300-1234567",
            "0300123456a",
        ):
            with self.subTest(value=value):
                self.assertFalse(DetailsForm(details_data(contact=value)).is_valid())

    def test_qr_label_name_and_phone_use_the_same_public_rules(self):
        self.assertTrue(QRLabelForm({
            "item_name": "Blue backpack", "contact_phone": "03001234567",
        }).is_valid())
        self.assertFalse(QRLabelForm({
            "item_name": "03001234567", "contact_phone": "03001234567",
        }).is_valid())
        self.assertFalse(QRLabelForm({
            "item_name": "Blue backpack", "contact_phone": "12345",
        }).is_valid())

    def test_email_must_be_a_real_address(self):
        for email in ("not-an-email", "a@b", "@example.test", "a b@example.test"):
            with self.subTest(email=email):
                form = Registration({
                    "first_name": "Sara Ahmed",
                    "email": email,
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                })
                self.assertFalse(form.is_valid())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DateBoundaryTests(TestCase):
    def test_dates_before_2000_and_in_the_future_are_rejected(self):
        today = timezone.localdate()
        cases = [
            ("31-12-1999", False),
            ("01-01-2000", True),
            (today.strftime("%d-%m-%Y"), True),
            ((today + timedelta(days=1)).strftime("%d-%m-%Y"), False),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                form = TypeForm(type_data(event_date=value))
                self.assertEqual(form.is_valid(), expected, form.errors)

    def test_impossible_or_misformatted_dates_are_rejected(self):
        for value in ("31-02-2025", "2025-01-01", "01/01/2025", "", "not a date"):
            with self.subTest(value=value):
                self.assertFalse(TypeForm(type_data(event_date=value)).is_valid())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CoordinateBoundaryTests(TestCase):
    def test_the_exact_coordinate_limits_are_accepted(self):
        for lat, lng in (
            ("90", "180"),
            ("-90", "-180"),
            ("0", "0"),
            ("24.86070000", "67.00110000"),
        ):
            with self.subTest(lat=lat, lng=lng):
                form = LocationForm(location_data(lat=lat, lng=lng))
                self.assertTrue(form.is_valid(), form.errors)

    def test_values_just_outside_the_coordinate_limits_are_rejected(self):
        for lat, lng in (
            ("90.00000001", "67.0011"),
            ("-90.00000001", "67.0011"),
            ("24.8607", "180.00000001"),
            ("24.8607", "-180.00000001"),
        ):
            with self.subTest(lat=lat, lng=lng):
                self.assertFalse(LocationForm(location_data(lat=lat, lng=lng)).is_valid())

    def test_non_numeric_and_non_finite_coordinates_are_rejected(self):
        for value in ("abc", "NaN", "Infinity", "-Infinity", "", "12,34"):
            with self.subTest(value=value):
                self.assertFalse(LocationForm(location_data(lat=value)).is_valid())
                self.assertFalse(LocationForm(location_data(lng=value)).is_valid())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MeetingTimeBoundaryTests(TestCase):
    def valid_payload(self, **overrides):
        data = {
            "meeting_place": "NED Security Office",
            "meeting_at": meeting_field_value(),
        }
        data.update(overrides)
        return data

    def test_a_future_time_in_the_exact_format_is_accepted(self):
        self.assertTrue(MeetingForm(self.valid_payload()).is_valid())

    def test_formatting_must_match_the_browser_and_server_pattern(self):
        for value in (
            "1-1-26 9:00 AM",
            "01/01/26 09:00 AM",
            "01-01-26 09:00",
            "01-01-26 13:00 PM",
            "01-13-26 09:00 AM",
            "32-01-26 09:00 AM",
            "01-01-26 09:60 AM",
            "tomorrow at noon",
            "",
        ):
            with self.subTest(value=value):
                self.assertFalse(MeetingForm(self.valid_payload(meeting_at=value)).is_valid())

    def test_past_times_are_rejected(self):
        form = MeetingForm(self.valid_payload(meeting_at=meeting_field_value(days=-1)))
        self.assertFalse(form.is_valid())
        self.assertIn("future meeting time", str(form.errors))

    def test_place_needs_readable_words(self):
        for value in ("12345", "\u202e", "   "):
            with self.subTest(value=repr(value)):
                self.assertFalse(MeetingForm(self.valid_payload(meeting_place=value)).is_valid())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class HttpValidationTests(TestCase):
    """Invalid values sent over HTTP must produce a form error, not a 500."""

    def setUp(self):
        self.user = make_user("validation@example.test")

    def test_hostile_step_one_values_are_rejected_and_never_saved(self):
        draft, url = start_wizard(self.client, self.user)
        payloads = [
            type_data(title="Blue\u202ebackpack"),
            type_data(title="call 03001234567"),
            type_data(title="12345"),
            type_data(event_date=(timezone.localdate() + timedelta(days=2)).strftime("%d-%m-%Y")),
            type_data(kind="Removed"),
            type_data(category="Not a category"),
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post(url + "?step=1", payload)
                self.assertEqual(response.status_code, 200)
                draft.refresh_from_db()
                self.assertNotIn("title", draft.data)
                self.assertNotIn("category", draft.data)

    def test_hostile_details_values_are_rejected_and_never_saved(self):
        draft, url = start_wizard(self.client, self.user)
        self.client.post(url + "?step=1", type_data())
        payloads = [
            details_data(description="call 03001234567"),
            details_data(description="sara@example.test"),
            details_data(contact="12345"),
            details_data(contact="0300-1234567"),
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post(url + "?step=2", payload)
                self.assertEqual(response.status_code, 200)
                draft.refresh_from_db()
                self.assertNotIn("description", draft.data)
                self.assertNotIn("contact", draft.data)

    def test_out_of_range_coordinates_are_rejected_over_http(self):
        draft, url = start_wizard(self.client, self.user)
        self.client.post(url + "?step=1", type_data())
        self.client.post(url + "?step=2", details_data())
        for lat, lng in (("91", "0"), ("0", "181"), ("NaN", "0")):
            with self.subTest(lat=lat, lng=lng):
                response = self.client.post(
                    url + "?step=3", location_data(lat=lat, lng=lng),
                )
                self.assertEqual(response.status_code, 200)
                draft.refresh_from_db()
                self.assertNotIn("lat", draft.data)

    def test_search_rejects_invisible_characters_but_accepts_unicode_words(self):
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(reverse("reports"), {"q": "back\u200bpack"}).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(reverse("reports"), {"q": "بیگ"}).status_code, 200,
        )

    def test_qr_label_form_errors_do_not_create_a_row(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("qr-labels"), {
            "item_name": "03001234567", "contact_phone": "03001234567",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(QRLabel.objects.filter(owner=self.user).exists())

    def test_tampered_draft_answers_are_a_validation_error_not_a_crash(self):
        draft, url = start_wizard(self.client, self.user)
        draft.data = {
            "kind": "Lost",
            "title": "Blue backpack",
            "category": "Bag",
            "event_date": timezone.localdate().isoformat(),
            "description": "Blue fabric backpack",
            "contact": "03001234567",
            "location": "Central Library",
            "lat": "24.86",
            "lng": "67.001",
            "location_detail": "Entrance",
            "answers": ["not", "a", "mapping"],
        }
        draft.save(update_fields=["data"])
        self.client.raise_request_exception = False
        response = self.client.post(url + "?step=5")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())
        self.assertFalse(Report.objects.filter(owner=self.user).exists())

    def test_tampered_event_date_is_a_validation_error_not_a_crash(self):
        draft, url = start_wizard(self.client, self.user)
        draft.data = {
            "kind": "Lost",
            "title": "Blue backpack",
            "category": "Bag",
            "event_date": "not-an-iso-date",
            "description": "Blue fabric backpack",
            "contact": "03001234567",
            "location": "Central Library",
            "lat": "24.86",
            "lng": "67.001",
            "location_detail": "Entrance",
            "answers": {"colour": "Blue", "kind": "Backpack", "material": "Fabric",
                        "pockets": "2", "mark": "None"},
        }
        draft.save(update_fields=["data"])
        self.client.raise_request_exception = False
        response = self.client.post(url + "?step=5")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())
        self.assertFalse(Report.objects.filter(owner=self.user).exists())
