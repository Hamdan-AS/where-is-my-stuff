"""Privacy boundaries: contacts, private answers, photos, QR codes, and cookies."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import QRLabel
from core.qr_labels import token_digest
from tests.support import (
    BAG_ANSWERS,
    AppTestCase,
    PASSWORD,
    TempMediaMixin,
    make_match,
    make_report,
    make_user,
)

SECRET_CNIC = "4210112345671"
SECRET_CARD = "4111111111111111"
OWNER_CONTACT = "03001234567"
FINDER_CONTACT = "03009876543"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ContactAndAnswerDisclosureTests(AppTestCase):
    def setUp(self):
        answers = {
            **BAG_ANSWERS,
            "cnic_suffix": SECRET_CNIC,
            "bank_1_suffix": SECRET_CARD,
        }
        self.lost = make_report(
            self.owner, "Lost", title="Blue backpack", answers=answers,
            contact=OWNER_CONTACT,
        )
        self.found = make_report(
            self.finder, "Found", title="Found blue backpack", answers=answers,
            contact=FINDER_CONTACT,
        )
        self.match = make_match(self.lost, self.found, score=95)

    def assert_private_material_is_absent(self, response):
        for value in (OWNER_CONTACT, FINDER_CONTACT, SECRET_CNIC, SECRET_CARD):
            with self.subTest(value=value):
                self.assertNotContains(response, value)
                self.assertNotContains(response, value, html=False)

    def test_owner_pages_never_render_contacts_or_private_answers(self):
        self.login(self.owner)
        paths = [
            reverse("dashboard"),
            reverse("reports"),
            reverse("report", args=[self.lost.pk]),
            reverse("match", args=[self.match.pk]),
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assert_private_material_is_absent(self.client.get(path))

    def test_management_never_renders_contacts_or_private_answers(self):
        self.login(self.staff)
        self.assert_private_material_is_absent(self.client.get(reverse("management")))

    def test_public_account_pages_never_render_any_report_data(self):
        self.logout()
        for path in (reverse("login"), reverse("register")):
            response = self.client.get(path)
            with self.subTest(path=path):
                self.assert_private_material_is_absent(response)
                self.assertNotContains(response, self.lost.title)
                self.assertNotContains(response, self.found.title)

    def test_contacts_appear_only_after_a_handover_is_scheduled(self):
        self.login(self.owner)
        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertNotContains(page, OWNER_CONTACT)
        self.assertNotContains(page, FINDER_CONTACT)

        from core.services import transition
        from tests.support import meeting

        transition(self.match.pk, self.owner, "propose", meeting())
        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertNotContains(page, OWNER_CONTACT)

        transition(self.match.pk, self.finder, "accept")
        page = self.client.get(reverse("match", args=[self.match.pk]))
        self.assertContains(page, OWNER_CONTACT)
        self.assertContains(page, FINDER_CONTACT)

    def logout(self):
        self.client.logout()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PhotoPrivacyTests(TempMediaMixin, AppTestCase):
    def setUp(self):
        super().setUp()
        self.report = make_report(self.owner, answers=BAG_ANSWERS)
        self.report.photo.save("secret.jpg", ContentFile(b"private-jpeg-bytes"), save=True)
        self.found = make_report(self.finder, "Found", answers=BAG_ANSWERS)
        self.match = make_match(self.report, self.found)

    def test_report_photo_is_owner_and_match_participant_only(self):
        url = reverse("report-photo", args=[self.report.pk])
        self.login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        b"".join(response.streaming_content)

        self.login(self.finder)
        participant = self.client.get(url)
        self.assertEqual(participant.status_code, 200)
        b"".join(participant.streaming_content)
        self.login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_photo_urls_are_not_embedded_in_public_pages(self):
        for path in (reverse("login"), reverse("register")):
            with self.subTest(path=path):
                self.assertNotContains(
                    self.client.get(path),
                    reverse("report-photo", args=[self.report.pk]),
                )


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class QrPrivacyTests(TempMediaMixin, AppTestCase):
    def setUp(self):
        super().setUp()
        self.token = "privacy-label-token"
        self.label = QRLabel.objects.create(
            owner=self.owner,
            item_name="Blue backpack",
            contact_phone=OWNER_CONTACT,
            token_hash=token_digest(self.token),
            qr_image="private_qr_labels/missing.png",
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.label.qr_image.save(
            "label.png", ContentFile(b"private-qr-bytes"), save=True,
        )

    def test_public_label_page_shows_only_the_active_phone(self):
        response = self.client.get(reverse("qr-label-public", args=[self.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, OWNER_CONTACT)
        self.assertNotContains(response, self.owner.email)
        self.assertNotContains(response, self.owner.first_name)
        self.assertNotContains(response, self.label.token_hash)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Referrer-Policy"], "no-referrer")

    def test_private_qr_image_is_owner_only_and_never_public(self):
        url = reverse("qr-label-image", args=[self.label.pk])
        self.login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        b"".join(response.streaming_content)

        download = self.client.get(url, {"download": "1"})
        self.assertIn("attachment", download["Content-Disposition"])
        self.assertIn(f"item-qr-{self.label.pk}.png", download["Content-Disposition"])
        b"".join(download.streaming_content)

        self.login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_a_token_is_stored_only_as_a_digest(self):
        self.assertNotEqual(self.label.token_hash, self.token)
        self.assertEqual(self.label.token_hash, token_digest(self.token))
        self.assertEqual(len(self.label.token_hash), 64)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class RedirectAndCookiePrivacyTests(AppTestCase):
    def test_login_next_cannot_be_used_as_an_open_redirect(self):
        self.assertTrue(self.owner.check_password(PASSWORD))
        for next_url in (
            "https://evil.example/phish",
            "//evil.example/phish",
            "/\\evil.example/phish",
            "javascript:alert(1)",
        ):
            with self.subTest(next_url=next_url):
                client = Client()
                response = client.post(reverse("login"), {
                    "username": self.owner.email,
                    "password": PASSWORD,
                    "next": next_url,
                })
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("create"))

    def test_session_and_csrf_cookies_use_defensive_defaults(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        client = Client()
        response = client.post(reverse("login"), {
            "username": self.owner.email, "password": PASSWORD,
        })
        session_cookie = response.cookies["sessionid"]
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(session_cookie["samesite"], "Lax")

    def test_private_views_do_not_invite_shared_caching(self):
        self.login(self.owner)
        report = make_report(self.owner)
        page = self.client.get(reverse("report", args=[report.pk]))
        cache_control = page.get("Cache-Control", "")
        self.assertNotIn("public", cache_control.lower())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AnonymousSurfaceTests(AppTestCase):
    def test_report_data_is_not_reachable_without_authentication(self):
        report = make_report(self.owner)
        for path in (
            reverse("report", args=[report.pk]),
            reverse("report-photo", args=[report.pk]),
            reverse("reports"),
            reverse("dashboard"),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse("login")))

    def test_making_a_user_does_not_expose_their_password(self):
        user = make_user("password-check@example.test")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_") or "$" in user.password)
