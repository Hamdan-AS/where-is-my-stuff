"""Shared fixtures for the layered test suite.

The suite is intentionally split by the question each layer asks:

* ``tests.unit``      - does each module's own logic hold in isolation?
* ``tests.blackbox``  - what does the HTTP contract look like from outside?
* ``tests.behavior``  - does a real user flow through the product correctly?
* ``tests.robustness``- do hostile, empty, and malformed inputs fail safely?

Every helper here builds real model rows. No view or service is mocked unless a
test is explicitly about a storage failure.
"""

from __future__ import annotations

import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import Draft, Match, Report, User

PASSWORD = "Correct-horse-battery-9!"

# One complete, valid answer set per category. Keeping them here means a flow
# test can loop over all categories without repeating form-shape knowledge.
BAG_ANSWERS = {
    "colour": "Blue",
    "kind": "Backpack",
    "material": "Fabric",
    "pockets": "2",
    "mark": "None",
}
WALLET_ANSWERS = {
    "colour": "Black",
    "material": "Leather",
    "logo": "No",
    "contents": [],
    "mark": "None",
}
KEYS_ANSWERS = {
    "colour": "Silver",
    "count": "3",
    "kind": "Home",
    "fob": "Plastic",
    "mark": "None",
}
CARDS_ANSWERS = {
    "colour": "Blue",
    "card_type": "CNIC",
    "issuer": "NADRA",
    "suffix": "4210112345671",
    "mark": "None",
}
ELECTRONICS_ANSWERS = {
    "colour": "Black",
    "kind": "Phone",
    "case": "None",
    "brand": "Samsung",
    "mark": "Scratch",
}
DOCUMENTS_ANSWERS = {
    "colour": "White",
    "kind": "Notebook",
    "holder": "Folder",
    "issuer": "NED University",
    "mark": "None",
}
CASH_ANSWERS = {
    "colour": "Green",
    "amount": "Below Rs. 500",
    "notes": "Mixed notes",
    "mark": "None",
}
OTHER_ANSWERS = {"colour": "Grey", "mark": "None"}

CATEGORY_ANSWERS = {
    "Wallet / Purse": WALLET_ANSWERS,
    "Cards / IDs": CARDS_ANSWERS,
    "Keys": KEYS_ANSWERS,
    "Electronics": ELECTRONICS_ANSWERS,
    "Bag": BAG_ANSWERS,
    "Documents": DOCUMENTS_ANSWERS,
    "Cash / Money": CASH_ANSWERS,
    "Other": OTHER_ANSWERS,
}


def make_user(email: str, *, password: str = PASSWORD, staff: bool = False,
              first_name: str = "Test") -> User:
    """Create a user whose username is the same lower-cased email."""
    email = email.lower()
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_staff=staff,
        first_name=first_name,
    )


def make_report(owner: User, kind: str = "Lost", *, answers=None, **overrides) -> Report:
    """Create a complete report, overriding only what a test cares about."""
    fields = {
        "kind": kind,
        "title": "Blue backpack",
        "category": "Bag",
        "description": "Blue fabric backpack with two front pockets near the library",
        "location": "Central Library",
        "lat": "24.86070000",
        "lng": "67.00110000",
        "location_detail": "Beside the entrance",
        "event_date": timezone.localdate(),
        "contact": "03001234567",
        "answers": dict(answers or BAG_ANSWERS),
    }
    fields.update(overrides)
    return Report.objects.create(owner=owner, **fields)


def make_match(lost: Report, found: Report, **overrides) -> Match:
    fields = {"lost": lost, "found": found, "score": 100}
    fields.update(overrides)
    return Match.objects.create(**fields)


def meeting(**overrides) -> dict:
    """A service-layer meeting payload that is always in the future."""
    value = {
        "meeting_place": "NED Security Office",
        "meeting_at": timezone.now() + timedelta(days=1),
    }
    value.update(overrides)
    return value


def meeting_field_value(days: int = 30) -> str:
    """A value in the exact ``DD-MM-YY hh:mm AM/PM`` format the form accepts."""
    moment = timezone.localtime(timezone.now()) + timedelta(days=days)
    return moment.strftime("%d-%m-%y %I:%M %p")


def draft_data(**overrides) -> dict:
    """A complete wizard payload in the JSON shape a ``Draft`` stores."""
    value = {
        "kind": "Lost",
        "title": "Blue backpack",
        "category": "Bag",
        "event_date": timezone.localdate().isoformat(),
        "description": "Blue fabric backpack with two front pockets",
        "contact": "03001234567",
        "location": "Central Library",
        "lat": "24.86",
        "lng": "67.001",
        "location_detail": "Beside the entrance",
        "answers": dict(BAG_ANSWERS),
    }
    value.update(overrides)
    return value


def png_upload(width: int = 64, height: int = 48, name: str = "item.png",
               colour=(28, 90, 40)) -> SimpleUploadedFile:
    """Build a real PNG so ImageField/Pillow validation is exercised."""
    from io import BytesIO

    from PIL import Image

    stream = BytesIO()
    Image.new("RGB", (width, height), colour).save(stream, format="PNG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/png")


class AppTestCase(TestCase):
    """Base class with the standard three-person cast used by flow tests."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("owner@example.test")
        cls.finder = make_user("finder@example.test")
        cls.outsider = make_user("outsider@example.test")
        cls.staff = make_user("staff@example.test", staff=True)

    def login(self, user=None):
        self.client.force_login(user or self.owner)
        return self.client


class TempMediaMixin:
    """Point MEDIA_ROOT at a throw-away directory for one test."""

    def setUp(self):
        super().setUp()
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self._media_override = override_settings(MEDIA_ROOT=self.media.name)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)


def start_wizard(client, user) -> tuple[Draft, str]:
    """Open a new report and return the draft plus its step-1 URL."""
    from django.urls import reverse

    client.force_login(user)
    response = client.get(reverse("create"))
    draft = Draft.objects.get(owner=user, report__isnull=True)
    return draft, reverse("draft", args=[draft.pk])


def submit_wizard(client, user, *, kind="Lost", title="Blue backpack",
                  category="Bag", description=None, contact="03001234567",
                  location="Central Library", location_detail="Beside the entrance",
                  lat="24.86", lng="67.001", answers=None) -> Report:
    """Walk the five wizard steps through HTTP and return the published report."""
    from django.urls import reverse

    draft, url = start_wizard(client, user)
    description = description or (
        "Blue fabric backpack with two front pockets near the library"
    )
    steps = [
        (1, {"kind": kind, "title": title, "category": category,
             "event_date": timezone.localdate().strftime("%d-%m-%Y")}),
        (2, {"description": description, "contact": contact}),
        (3, {"location": location, "lat": lat, "lng": lng,
             "location_detail": location_detail}),
        (4, dict(answers or CATEGORY_ANSWERS[category])),
        (5, {}),
    ]
    for step, payload in steps:
        response = client.post(f"{url}?step={step}", payload)
        assert response.status_code == 302, (step, response.status_code, response.content[:500])
    assert not Draft.objects.filter(pk=draft.pk).exists()
    return Report.objects.get(owner=user, title=title)
