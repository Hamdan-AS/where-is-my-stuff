"""Regression coverage for private item photos and owner-managed QR labels."""
import hashlib
import tempfile
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import DetailsForm
from .images import normalize_photo
from .models import Draft, Match, QRLabel, Report, User
from .qr_labels import expiry_after_months, token_digest


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ItemPhotoTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings = override_settings(MEDIA_ROOT=self.media.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.owner = User.objects.create_user(
            username="photo-owner@example.test", email="photo-owner@example.test",
            password="Safe-test-password-751!",
        )
        self.finder = User.objects.create_user(
            username="photo-finder@example.test", email="photo-finder@example.test",
            password="Safe-test-password-751!",
        )
        self.outsider = User.objects.create_user(
            username="photo-outsider@example.test", email="photo-outsider@example.test",
            password="Safe-test-password-751!",
        )

    @staticmethod
    def png_upload(width=2400, height=1200, name="item.png"):
        stream = BytesIO()
        Image.new("RGB", (width, height), (28, 90, 40)).save(stream, format="PNG")
        return SimpleUploadedFile(name, stream.getvalue(), content_type="image/png")

    def test_optional_photo_form_rejects_non_image_and_huge_dimensions(self):
        fields = {"description": "Blue backpack with a stitched patch", "contact": "03001234567"}
        invalid = SimpleUploadedFile("picture.png", b"not an image", content_type="image/png")
        self.assertFalse(DetailsForm(fields, {"photo": invalid}).is_valid())
        oversized = self.png_upload(width=6001, height=2)
        form = DetailsForm(fields, {"photo": oversized})
        self.assertFalse(form.is_valid())
        self.assertIn("photo", form.errors)

    def test_photo_size_and_dimension_boundaries_are_explicit(self):
        fields = {"description": "Blue backpack with a stitched patch", "contact": "03001234567"}
        # The pixel cap allows exactly 24 megapixels and rejects the next pixel.
        at_limit = self.png_upload(width=6000, height=4000, name="limit.png")
        form = DetailsForm(fields, {"photo": at_limit})
        self.assertTrue(form.is_valid(), form.errors)
        too_many_pixels = self.png_upload(width=6000, height=4001, name="too-many.png")
        form = DetailsForm(fields, {"photo": too_many_pixels})
        self.assertFalse(form.is_valid())
        self.assertIn("photo", form.errors)

        # Valid PNG bytes padded after the image test both sides of the exact byte cap.
        max_bytes = 5 * 1024 * 1024
        image_bytes = self.png_upload(width=8, height=8).read()
        exact_limit = SimpleUploadedFile(
            "exact-limit.png", image_bytes + b"\x00" * (max_bytes - len(image_bytes)),
            content_type="image/png",
        )
        form = DetailsForm(fields, {"photo": exact_limit})
        self.assertTrue(form.is_valid(), form.errors)
        oversized = SimpleUploadedFile(
            "over-limit.png", image_bytes + b"\x00" * (max_bytes + 1 - len(image_bytes)),
            content_type="image/png",
        )
        form = DetailsForm(fields, {"photo": oversized})
        self.assertFalse(form.is_valid())
        self.assertIn("no larger than 5 MiB", str(form.errors))

        gif_data = BytesIO()
        Image.new("RGB", (32, 32), "green").save(gif_data, format="GIF")
        gif = SimpleUploadedFile("unsupported.gif", gif_data.getvalue(), content_type="image/gif")
        form = DetailsForm(fields, {"photo": gif})
        self.assertFalse(form.is_valid())
        self.assertIn("photo", form.errors)

    def test_portrait_transparency_is_kept_uncropped_and_flattened_for_jpeg(self):
        stream = BytesIO()
        image = Image.new("RGBA", (1200, 2400), (20, 80, 160, 128))
        image.save(stream, format="PNG")
        upload = SimpleUploadedFile("portrait.png", stream.getvalue(), content_type="image/png")
        normalized = normalize_photo(upload)
        with Image.open(normalized) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (900, 1800))
            self.assertEqual(image.mode, "RGB")
            self.assertFalse(image.getexif())

    def test_photo_is_optional_resized_without_cropping_and_private_to_owner_or_match(self):
        self.client.force_login(self.owner)
        self.client.get(reverse("create"))
        draft = Draft.objects.get(owner=self.owner, report__isnull=True)
        url = reverse("draft", args=[draft.pk])
        self.client.post(url + "?step=1", {
            "kind": "Lost", "title": "Blue backpack", "category": "Bag",
            "event_date": timezone.localdate().strftime("%d-%m-%Y"),
        })
        response = self.client.post(url + "?step=2", {
            "description": "Blue backpack with a stitched patch",
            "contact": "03001234567", "action": "next",
        })
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertFalse(draft.photo)

        response = self.client.get(url + "?step=2")
        self.assertContains(response, "JPEG, PNG or WebP")
        response = self.client.post(url + "?step=2", {
            "description": "Blue backpack with a stitched patch",
            "contact": "03001234567", "action": "next",
            "photo": self.png_upload(),
        })
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        with Image.open(Path(self.media.name) / draft.photo.name) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (1800, 900))
            self.assertFalse(image.getexif())
        draft.photo.close()

        draft_photo_url = reverse("draft-photo", args=[draft.pk])
        draft_preview = self.client.get(draft_photo_url)
        self.assertEqual(draft_preview.status_code, 200)
        self.assertEqual(draft_preview["Content-Type"], "image/jpeg")
        self.assertEqual(draft_preview["Cache-Control"], "private, no-store")
        self.assertEqual(draft_preview["X-Content-Type-Options"], "nosniff")
        list(draft_preview.streaming_content)  # Test client closes streamed files without closing the test transaction.
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(draft_photo_url).status_code, 404)

        report = Report.objects.create(
            owner=self.owner, kind="Lost", title="Blue backpack", category="Bag",
            description="Blue backpack with a stitched patch", location="Library",
            location_detail="Near entrance", event_date=timezone.localdate(),
            contact="03001234567", answers={}, photo=draft.photo.name,
        )
        photo_url = reverse("report-photo", args=[report.pk])
        self.client.force_login(self.owner)
        photo_response = self.client.get(photo_url)
        self.assertEqual(photo_response.status_code, 200)
        self.assertEqual(photo_response["Content-Type"], "image/jpeg")
        self.assertEqual(photo_response["Cache-Control"], "private, no-store")
        self.assertEqual(photo_response["X-Content-Type-Options"], "nosniff")
        list(photo_response.streaming_content)  # Test client closes streamed files without closing the test transaction.
        self.client.logout()
        self.assertEqual(self.client.get(photo_url).status_code, 302)
        self.client.force_login(self.outsider)
        denied_response = self.client.get(photo_url)
        self.assertEqual(denied_response.status_code, 404)
        self.client.force_login(self.finder)
        denied_response = self.client.get(photo_url)
        self.assertEqual(denied_response.status_code, 404)
        Match.objects.create(lost=report, found=Report.objects.create(
            owner=self.finder, kind="Found", title="Blue backpack found",
            category="Bag", description="Blue backpack with a stitched patch",
            location="Library", location_detail="Near entrance",
            event_date=timezone.localdate(), contact="03001112222", answers={},
        ), score=80)
        photo_response = self.client.get(photo_url)
        self.assertEqual(photo_response.status_code, 200)
        self.assertEqual(photo_response["Cache-Control"], "private, no-store")
        self.assertEqual(photo_response["X-Content-Type-Options"], "nosniff")
        list(photo_response.streaming_content)  # Test client closes streamed files without closing the test transaction.

    def test_photo_wizard_accepts_actual_image_bytes_and_rejects_executable_text(self):
        fields = {"description": "Black bag with a silver zipper", "contact": "03001234567"}
        fake = SimpleUploadedFile("image.jpg", b"<script>alert(1)</script>", content_type="image/jpeg")
        self.assertFalse(DetailsForm(fields, {"photo": fake}).is_valid())

    def test_webp_and_exif_rotated_images_are_accepted_and_normalized(self):
        fields = {"description": "Black bag with a silver zipper", "contact": "03001234567"}
        webp_data = BytesIO()
        Image.new("RGB", (64, 32), "blue").save(webp_data, format="WEBP")
        webp = SimpleUploadedFile("item.webp", webp_data.getvalue(), content_type="image/webp")
        form = DetailsForm(fields, {"photo": webp})
        self.assertTrue(form.is_valid(), form.errors)
        with Image.open(normalize_photo(form.cleaned_data["photo"])) as normalized:
            self.assertEqual(normalized.format, "JPEG")

        jpeg_data = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (120, 80), "red").save(jpeg_data, format="JPEG", exif=exif)
        rotated = SimpleUploadedFile("rotated.jpg", jpeg_data.getvalue(), content_type="image/jpeg")
        normalized = normalize_photo(rotated)
        with Image.open(normalized) as image:
            self.assertEqual(image.size, (80, 120))
            self.assertFalse(image.getexif())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PersonalQRLabelTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings = override_settings(MEDIA_ROOT=self.media.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.owner = User.objects.create_user(
            username="label-owner@example.test", email="label-owner@example.test",
            password="Safe-test-password-751!",
        )
        self.outsider = User.objects.create_user(
            username="label-outsider@example.test", email="label-outsider@example.test",
            password="Safe-test-password-751!",
        )
        self.token = "fixed-random-test-token-A9q5"
        self.client.force_login(self.owner)

    def create_label(self):
        with patch("core.views.new_label_token", return_value=self.token):
            response = self.client.post(reverse("qr-labels"), {
                "item_name": "Blue backpack", "contact_phone": "03001234567",
            })
        self.assertRedirects(response, reverse("qr-labels"))
        return QRLabel.objects.get(owner=self.owner)

    def test_create_stores_only_sha256_token_digest_and_owner_private_qr_png(self):
        label = self.create_label()
        self.assertEqual(label.token_hash, hashlib.sha256(self.token.encode()).hexdigest())
        self.assertNotIn(self.token, label.token_hash)
        self.assertEqual(len(label.token_hash), 64)
        with label.qr_image.open("rb") as image_file:
            self.assertTrue(image_file.read(8).startswith(b"\x89PNG"))
        image_url = reverse("qr-label-image", args=[label.pk])
        image_response = self.client.get(image_url)
        self.assertEqual(image_response.status_code, 200)
        list(image_response.streaming_content)  # Test client closes streamed files without closing the test transaction.
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(image_url).status_code, 404)
        self.assertEqual(self.client.get(reverse("qr-labels")).status_code, 200)

    def test_scan_shows_call_details_while_active_and_hides_them_after_expiry(self):
        label = self.create_label()
        public_url = reverse("qr-label-public", args=[self.token])
        self.client.logout()
        response = self.client.get(public_url)
        self.assertContains(response, "Call 03001234567")
        self.assertContains(response, "responsible for agreeing how to return")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Referrer-Policy"], "no-referrer")
        label.expires_at = timezone.now() - timedelta(seconds=1)
        label.save(update_fields=["expires_at"])
        response = self.client.get(public_url)
        self.assertContains(response, "This QR label is inactive")
        self.assertNotContains(response, "03001234567")
        self.assertNotContains(response, "Blue backpack")

    def test_reactivation_keeps_printed_token_and_qr_image_and_adds_six_months(self):
        label = self.create_label()
        label.expires_at = timezone.now() - timedelta(days=5)
        label.revoked = True
        label.save(update_fields=["expires_at", "revoked"])
        original_hash, original_image = label.token_hash, label.qr_image.name
        before = timezone.now()
        response = self.client.post(reverse("qr-label-reactivate", args=[label.pk]))
        self.assertRedirects(response, reverse("qr-labels"))
        label.refresh_from_db()
        self.assertEqual(label.token_hash, original_hash)
        self.assertEqual(label.qr_image.name, original_image)
        self.assertFalse(label.revoked)
        self.assertLess(abs((label.expires_at - expiry_after_months(before)).total_seconds()), 1)
        self.client.logout()
        self.assertContains(self.client.get(reverse("qr-label-public", args=[self.token])), "Call 03001234567")

    def test_other_users_cannot_reactivate_or_deactivate_owner_label(self):
        label = self.create_label()
        self.client.force_login(self.outsider)
        for name in ("qr-label-reactivate", "qr-label-deactivate"):
            response = self.client.post(reverse(name, args=[label.pk]))
            self.assertEqual(response.status_code, 404)
        label.refresh_from_db()
        self.assertFalse(label.revoked)

    def test_deactivation_is_post_only_and_stops_public_contact(self):
        label = self.create_label()
        get_response = self.client.get(reverse("qr-label-deactivate", args=[label.pk]))
        self.assertEqual(get_response.status_code, 405)
        self.client.post(reverse("qr-label-deactivate", args=[label.pk]))
        label.refresh_from_db()
        self.assertTrue(label.revoked)
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("qr-label-public", args=[self.token])), "03001234567")

    def test_calendar_expiry_clamps_end_of_month(self):
        starts = datetime(2026, 8, 31, 12, tzinfo=timezone.get_current_timezone())
        self.assertEqual(expiry_after_months(starts).date().isoformat(), "2027-02-28")
