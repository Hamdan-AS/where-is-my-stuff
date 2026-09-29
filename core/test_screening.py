"""Table-driven boundary sweeps for the form layer.

Every case states the expected verdict, so a screen that stops rejecting a
private identifier and a screen that starts rejecting honest text are both
failures. Runs without touching the database.
"""

import unicodedata
from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from .forms import (
    BAD_CHARS,
    DetailsForm,
    LocationForm,
    MatchingForm,
    MeetingForm,
    TypeForm,
)

# Ranges wide enough to hold every codepoint BAD_CHARS can match, plus the
# bidi-control and byte-order-mark planes. The blocklist decides what is
# inside; this sweep only checks that whatever is inside gets rejected.
SWEEP_RANGES = ((0x00, 0x100), (0x2000, 0x2100), (0xFE00, 0xFF00), (0xFFF9, 0xFFFD))


def type_data(**over):
    data = {"kind": "Lost", "title": "Wallet", "category": "Wallet / Purse",
            "event_date": "01-06-2026"}
    data.update(over)
    return data


def details_data(**over):
    data = {"description": "plain description", "contact": "03001234567"}
    data.update(over)
    return data


def location_data(**over):
    data = {"location": "Main Gate", "lat": "24.8607", "lng": "67.0011",
            "location_detail": "near stairs"}
    data.update(over)
    return data


def meeting_data(**over):
    soon = timezone.localdate() + timedelta(days=30)
    data = {"meeting_place": "Gulshan Chowrangi",
            "meeting_at": soon.strftime("%d-%m-%y %I:%M %p")}
    data.update(over)
    return data


class BlocklistCoverageTests(SimpleTestCase):
    def test_every_blocklisted_codepoint_is_rejected_by_every_public_field(self):
        probed = 0
        for low, high in SWEEP_RANGES:
            for cp in range(low, high):
                char = chr(cp)
                if not BAD_CHARS.search(char):
                    continue
                probed += 1
                when = meeting_data()["meeting_at"]
                forms = {
                    "title": TypeForm(type_data(title=f"wal{char}let")),
                    "description": DetailsForm(details_data(description=f"wal{char}let")),
                    "location": LocationForm(location_data(location=f"wal{char}let")),
                    "location_detail": LocationForm(location_data(location_detail=f"wal{char}let")),
                    "meeting_place": MeetingForm({"meeting_place": f"wal{char}let",
                                                  "meeting_at": when}),
                }
                for field, form in forms.items():
                    with self.subTest(codepoint=f"U+{cp:04X}", field=field,
                                      name=unicodedata.name(char, "unassigned")):
                        self.assertFalse(form.is_valid(), msg=form.errors)
        self.assertGreater(probed, 50)

    def test_allowed_whitespace_and_punctuation_still_pass(self):
        for char in [" ", "\t", "\n", "\u00a0"]:
            with self.subTest(codepoint=f"U+{ord(char):04X}"):
                self.assertTrue(TypeForm(type_data(title=f"wal{char}let")).is_valid())
        self.assertTrue(TypeForm(type_data(title="Wallet (black) - 100% mine!")).is_valid())
        self.assertTrue(TypeForm(type_data(title="محفظة 🔑")).is_valid())


class EventDateTests(SimpleTestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def day(self, offset):
        return (self.today + timedelta(days=offset)).strftime("%d-%m-%Y")

    def test_accepted_dates(self):
        cases = {
            "today": self.day(0),
            "yesterday": self.day(-1),
            "year 2000 floor": "01-01-2000",
            "leap day": "29-02-2024",
            "unpadded is read as padded": "1-1-2024",
            "end of month": "31-01-2024",
        }
        for label, value in cases.items():
            with self.subTest(case=label):
                self.assertTrue(TypeForm(type_data(event_date=value)).is_valid())

    def test_rejected_dates(self):
        cases = {
            "tomorrow": self.day(1),
            "400 days ahead": self.day(400),
            "year 1999": "01-01-1999",
            "february 31": "31-02-2024",
            "february 29 in a common year": "29-02-2023",
            "month 13": "01-13-2024",
            "month 00": "00-01-2024",
            "day 00": "00-01-2024",
            "iso order": "2024-01-01",
            "us order": "01/01/2024",
            "empty": "",
            "trailing text": "01-01-2024abc",
            "negative year": "-01-01-2024",
            "five digit year": "01-01-99999",
            "year 2050": "01-01-2050",
        }
        for label, value in cases.items():
            with self.subTest(case=label):
                self.assertFalse(TypeForm(type_data(event_date=value)).is_valid())


class ContactFieldTests(SimpleTestCase):
    def test_accepted_contacts(self):
        for value in ["03001234567", "+92 300 1234567", "+92-300-1234567",
                      "(0300) 1234567", "1234567", "a@b.com"]:
            with self.subTest(contact=value):
                self.assertTrue(DetailsForm(details_data(contact=value)).is_valid())

    def test_rejected_contacts(self):
        cases = {
            "six digits": "123456",
            "sixteen digits": "1234567890123456",
            "letters": "abc",
            "empty": "",
            "zero width space": "0300\u200b1234567",
            "right to left override": "0300\u202e1234567",
            "newline": "0300\n1234567",
            "digits then letters": "0300abc1234567",
            "plus alone": "+",
            "email without tld": "a@b",
            "email with space": "a b@c.com",
            "markup": "<script>alert(1)</script>",
            "dotted phone": "0300.1234567",
            "arabic indic digits": "٠٣٠٠١٢٣٤٥٦٧",
        }
        for label, value in cases.items():
            with self.subTest(case=label):
                self.assertFalse(DetailsForm(details_data(contact=value)).is_valid())


class CoordinateFieldTests(SimpleTestCase):
    def test_accepted_coordinates(self):
        cases = {
            "zero": {"lat": "0"},
            "latitude at 90": {"lat": "90"},
            "latitude at -90": {"lat": "-90"},
            "longitude at 180": {"lng": "180"},
            "longitude at -180": {"lng": "-180"},
            "eight decimals": {"lat": "24.86070000", "lng": "67.00110000"},
            "leading plus": {"lat": "+24.8607"},
            "surrounding space": {"lat": " 24.8607 "},
        }
        for label, over in cases.items():
            with self.subTest(case=label):
                self.assertTrue(LocationForm(location_data(**over)).is_valid())

    def test_rejected_coordinates(self):
        cases = {
            "just past 90": {"lat": "90.00000001"},
            "latitude 91": {"lat": "91"},
            "latitude -91": {"lat": "-91"},
            "latitude empty": {"lat": ""},
            "latitude text": {"lat": "abc"},
            "latitude exponent": {"lat": "1e5"},
            "nine decimals": {"lat": "24.860700001"},
            "ten integer digits": {"lat": "1234567890"},
            "latitude infinity": {"lat": "Infinity"},
            "latitude not a number": {"lat": "NaN"},
            "latitude hex": {"lat": "0x10"},
            "longitude 180.1": {"lng": "180.1"},
            "longitude 181": {"lng": "181"},
            "longitude nine decimals": {"lng": "67.001100001"},
            "comma decimal": {"lat": "24,8607"},
            "unit suffix": {"lat": "24.8607deg"},
            "internal space": {"lat": "24 .8607"},
        }
        for label, over in cases.items():
            with self.subTest(case=label):
                self.assertFalse(LocationForm(location_data(**over)).is_valid())


class MatchingDependencyTests(SimpleTestCase):
    WALLET = {"colour": "Black", "material": "Leather", "logo": "No",
              "contents": [], "mark": "Scratch"}

    def matching(self, data, selection=None, category="Wallet / Purse"):
        return MatchingForm(data, category=category, selection=selection or {})

    def test_wallet_without_contents_needs_only_the_base_fields(self):
        form = self.matching(self.WALLET)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("cnic_suffix", form.fields)
        self.assertNotIn("bank_count", form.fields)

    def test_cnic_answer_is_the_full_thirteen_digits(self):
        selection = {"contents": ["CNIC"]}
        for value, expect in [("4210112345671", True), ("0000000000000", True),
                              ("421011234567", False), ("42101123456712", False),
                              ("42101-1234567-1", False), ("abc", False), ("", False)]:
            with self.subTest(suffix=value):
                form = self.matching({**self.WALLET, "contents": ["CNIC"],
                                      "cnic_suffix": value}, selection)
                self.assertEqual(form.is_valid(), expect, form.errors)

    def test_bank_card_count_is_between_one_and_five(self):
        selection = {"contents": ["Bank cards"]}
        for count, expect in [("1", True), ("5", True), ("0", False), ("6", False), ("99", False)]:
            with self.subTest(bank_count=count):
                form = self.matching({**self.WALLET, "contents": ["Bank cards"],
                                      "bank_count": count, "bank_1_issuer": "HBL",
                                      "bank_1_suffix": "4111111111111111"}, selection)
                self.assertEqual(form.is_valid(), expect, form.errors)

    def test_bank_card_answer_is_the_full_sixteen_digits(self):
        selection = {"contents": ["Bank cards"]}
        for suffix, expect in [("4111111111111111", True), ("0000000000000000", True),
                               ("411111111111111", False), ("41111111111111111", False),
                               ("4111-1111-1111-1111", False), ("abcdefghijklmnop", False),
                               ("", False)]:
            with self.subTest(suffix=suffix):
                form = self.matching({**self.WALLET, "contents": ["Bank cards"],
                                      "bank_count": "1", "bank_1_issuer": "HBL",
                                      "bank_1_suffix": suffix}, selection)
                self.assertEqual(form.is_valid(), expect, form.errors)

    def test_card_issuer_must_match_the_card_type(self):
        for card_type, issuer, suffix, expect in [("CNIC", "NADRA", "4210112345671", True),
                                                 ("CNIC", "HBL", "4210112345671", False),
                                                 ("CNIC", "Computer Science & Information Technology (CSIT)", "4210112345671", False),
                                                 ("NED Student Card", "Computer Science & Information Technology (CSIT)", "1234", True),
                                                 ("NED Student Card", "NADRA", "1234", False),
                                                 ("Bank Card", "JazzCash", "4111111111111111", True),
                                                 ("Bank Card", "NADRA", "4111111111111111", False),
                                                 ("Bank Card", "NayaPay", "411111111111111", False)]:
            with self.subTest(card_type=card_type, issuer=issuer):
                form = self.matching({"colour": "Blue", "card_type": card_type, "issuer": issuer,
                                      "suffix": suffix, "mark": "None"},
                                     {"card_type": card_type}, "Cards / IDs")
                self.assertEqual(form.is_valid(), expect, form.errors)

    def test_bogus_choices_are_rejected(self):
        form = self.matching({**self.WALLET, "contents": ["Unobtanium"]}, {"contents": []})
        self.assertFalse(form.is_valid())
        form = self.matching({**self.WALLET, "colour": "Invisible"})
        self.assertFalse(form.is_valid())

    def test_free_text_answers_reject_invisible_characters(self):
        form = self.matching({**self.WALLET, "logo": "Yes", "logo_name": "Na\u202eme"},
                             {"logo": "Yes"})
        self.assertFalse(form.is_valid())
        form = self.matching({**self.WALLET, "logo": "Yes", "logo_name": "N" + "a" * 81},
                             {"logo": "Yes"})
        self.assertFalse(form.is_valid())


class MeetingFormSweepTests(SimpleTestCase):
    def test_accepted_meetings(self):
        day = (timezone.localdate() + timedelta(days=30)).strftime("%d-%m-%y")
        for place, when in [("Gulshan Chowrangi", f"{day} 03:00 PM"),
                            ("Gulshan Chowrangi, near the fountain", f"{day} 09:25 PM"),
                            ("a" * 255, f"{day} 12:00 AM")]:
            with self.subTest(place=place[:20], when=when):
                self.assertTrue(MeetingForm(meeting_data(meeting_place=place,
                                                         meeting_at=when)).is_valid())

    def test_rejected_meetings(self):
        past = (timezone.localdate() - timedelta(days=1)).strftime("%d-%m-%y %I:%M %p")
        soon = (timezone.localdate() + timedelta(days=30)).strftime("%d-%m-%y %I:%M %p")
        cases = {
            "place 256 chars": {"meeting_place": "a" * 256},
            "empty place": {"meeting_place": ""},
            "place without letters": {"meeting_place": "12345"},
            "past time": {"meeting_at": past},
            "iso order time": {"meeting_at": "2026-09-27 15:00"},
            "impossible date": {"meeting_at": "31-02-26 03:00 PM"},
            "empty time": {"meeting_at": ""},
            "markup in time": {"meeting_at": "27-09-26 <b>03:00</b> PM"},
        }
        for label, over in cases.items():
            with self.subTest(case=label):
                data = meeting_data(meeting_at=soon)
                data.update(over)
                self.assertFalse(MeetingForm(data).is_valid())
