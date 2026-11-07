"""Private item photos: validation, normalisation, and access control."""

from datetime import timezone as dt_timezone
from io import BytesIO
from pathlib import Path

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.forms import DetailsForm
from core.models import Draft, Match, Report
from core.images import MAX_EDGE, normalize_photo
from tests.support import (
    BAG_ANSWERS,
    AppTestCase,
    TempMediaMixin,
    make_match,
    make_report,
    png_upload,
    start_wizard,
)


def image_upload(fmt="PNG", size=(64, 48), name=None, **save_kwargs):
    stream = BytesIO()
    Image.new("RGB", size, (30, 90, 160)).save(stream, format=fmt, **save_kwargs)
    name = name or f"item.{fmt.lower()}"
    return SimpleUploadedFile(name, stream.getvalue(), content_type=f"image/{fmt.lower()}")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PhotoValidationTests(TestCase):
    def form(self, photo=None, **overrides):
        data = {"description": "Blue backpack with a stitched patch",
                "contact": "03001234567"}
        data.update(overrides)
        files = {"photo": photo} if photo is not None else None
        return DetailsForm(data, files)

    def test_photo_is_optional(self):
        self.assertTrue(self.form().is_valid())

    def test_supported_formats_are_accepted(self):
        for fmt in ("JPEG", "PNG", "WEBP"):
            with self.subTest(format=fmt):
                form = self.form(image_upload(fmt))
                self.assertTrue(form.is_valid(), form.errors)

    def test_unsupported_or_fake_images_are_rejected(self):
        payloads = [
            ("empty.png", b""),
            ("fake.png", b"<svg onload=alert(1)>"),
            ("header-only.png", b"\x89PNG\r\n\x1a\n"),
            ("script.jpg", b"<script>alert(1)</script>"),
        ]
        for name, payload in payloads:
            with self.subTest(name=name):
                form = self.form(SimpleUploadedFile(name, payload, content_type="image/png"))
                self.assertFalse(form.is_valid())
                self.assertIn("photo", form.errors)

        gif = image_upload("GIF", name="item.gif")
        form = self.form(gif)
        self.assertFalse(form.is_valid())
        self.assertIn("photo", form.errors)

    def test_the_exact_byte_limit_is_accepted_and_one_byte_more_is_not(self):
        max_bytes = 5 * 1024 * 1024
        image_bytes = png_upload(width=8, height=8).read()
        exact = SimpleUploadedFile(
            "exact.png", image_bytes + b"\0" * (max_bytes - len(image_bytes)),
            content_type="image/png",
        )
        self.assertTrue(self.form(exact).is_valid())

        over = SimpleUploadedFile(
            "over.png", image_bytes + b"\0" * (max_bytes + 1 - len(image_bytes)),
            content_type="image/png",
        )
        form = self.form(over)
        self.assertFalse(form.is_valid())
        self.assertIn("no larger than 5 MiB", str(form.errors))

    def test_exactly_twenty_four_megapixels_is_allowed_and_one_pixel_more_is_not(self):
        at_limit = png_upload(width=6000, height=4000, name="limit.png")
        self.assertTrue(self.form(at_limit).is_valid())
        too_many = png_upload(width=6000, height=4001, name="too-many.png")
        self.assertFalse(self.form(too_many).is_valid())

    def test_a_single_edge_longer_than_six_thousand_pixels_is_rejected(self):
        form = self.form(png_upload(width=6001, height=2))
        self.assertFalse(form.is_valid())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PhotoNormalisationTests(TestCase):
    def test_large_images_are_resized_to_the_longest_edge_without_cropping(self):
        normalized = normalize_photo(png_upload(width=2400, height=1200))
        with Image.open(normalized) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (MAX_EDGE, MAX_EDGE // 2))
            self.assertEqual(image.mode, "RGB")

    def test_portrait_images_keep_their_aspect_ratio(self):
        stream = BytesIO()
        Image.new("RGBA", (1200, 2400), (20, 80, 160, 128)).save(stream, format="PNG")
        upload = SimpleUploadedFile("portrait.png", stream.getvalue(), content_type="image/png")
        with Image.open(normalize_photo(upload)) as image:
            self.assertEqual(image.size, (900, 1800))
            self.assertEqual(image.mode, "RGB")

    def test_exif_orientation_is_applied_and_metadata_is_discarded(self):
        stream = BytesIO()
        exif = Image.Exif()
        exif[274] = 6  # rotate 90 degrees on display
        exif[271] = "Test Camera"
        Image.new("RGB", (120, 80), "red").save(stream, format="JPEG", exif=exif)
        upload = SimpleUploadedFile("rotated.jpg", stream.getvalue(), content_type="image/jpeg")
        with Image.open(normalize_photo(upload)) as image:
            self.assertEqual(image.size, (80, 120))
            self.assertFalse(image.getexif())

    def test_transparency_is_flattened_onto_white(self):
        stream = BytesIO()
        Image.new("RGBA", (40, 40), (0, 0, 0, 0)).save(stream, format="PNG")
        upload = SimpleUploadedFile("clear.png", stream.getvalue(), content_type="image/png")
        with Image.open(normalize_photo(upload)) as image:
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PhotoAccessTests(TempMediaMixin, AppTestCase):
    def save_draft_photo(self):
        draft, url = start_wizard(self.client, self.owner)
        self.client.post(url + "?step=1", {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": "01-01-2026",
        })
        response = self.client.post(url + "?step=2", {
            "description": "Blue backpack with a stitched patch",
            "contact": "03001234567",
            "photo": png_upload(width=2400, height=1200),
        })
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertTrue(draft.photo)
        return draft

    def make_report_with_photo(self, draft, owner=None):
        return make_report(
            owner or self.owner, photo=draft.photo.name,
            answers=BAG_ANSWERS,
        )

    def test_a_draft_photo_is_visible_only_to_its_owner(self):
        draft = self.save_draft_photo()
        url = reverse("draft-photo", args=[draft.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        list(response.streaming_content)

        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_a_report_photo_is_visible_to_the_owner_and_match_participants_only(self):
        draft = self.save_draft_photo()
        report = self.make_report_with_photo(draft)
        url = reverse("report-photo", args=[report.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"], "image/jpeg",
        )
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        list(response.streaming_content)

        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)

        self.client.force_login(self.finder)
        self.assertEqual(self.client.get(url).status_code, 404)
        found = make_report(self.finder, "Found", answers=BAG_ANSWERS)
        make_match(report, found)
        participant = self.client.get(url)
        self.assertEqual(participant.status_code, 200)
        list(participant.streaming_content)

    def test_publishing_moves_the_normalised_photo_onto_the_report(self):
        draft = self.save_draft_photo()
        url = reverse("draft", args=[draft.pk])
        self.client.post(url + "?step=3", {
            "location": "Central Library", "lat": "24.86", "lng": "67.001",
            "location_detail": "Beside the entrance",
        })
        self.client.post(url + "?step=4", BAG_ANSWERS)
        response = self.client.post(url + "?step=5")
        self.assertEqual(response.status_code, 302)
        report = Report.objects.get(owner=self.owner)
        self.assertTrue(report.photo)
        with Image.open(Path(self.media.name) / report.photo.name) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (1800, 900))
            self.assertFalse(image.getexif())

    def test_a_missing_file_on_disk_returns_404_not_500(self):
        report = make_report(self.owner, photo="report_photos/missing.jpg")
        draft = Draft.objects.create(owner=self.owner, photo="draft_photos/missing.jpg")
        self.login()
        self.client.raise_request_exception = False
        for url in (
            reverse("report-photo", args=[report.pk]),
            reverse("draft-photo", args=[draft.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_a_report_without_a_photo_returns_404(self):
        report = make_report(self.owner)
        self.login()
        self.assertEqual(
            self.client.get(reverse("report-photo", args=[report.pk])).status_code,
            404,
        )
