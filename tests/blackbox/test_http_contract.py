"""Black-box HTTP contract: routes, auth boundaries, methods, and CSRF.

These tests deliberately do not call services or forms. They treat the Django
project as a web server and describe what an anonymous or signed-in caller sees.
"""

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from tests.support import PASSWORD, make_user, make_report

PUBLIC_GET_PATHS = ["/login/", "/register/"]
PROTECTED_GET_PATHS = [
    "/",
    "/reports/",
    "/reports/new/",
    "/reports/1/",
    "/reports/1/edit/",
    "/matches/1/",
    "/labels/",
    "/management/",
]


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AnonymousAccessTests(TestCase):
    def test_public_pages_are_reachable_without_an_account(self):
        for path in PUBLIC_GET_PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_private_pages_redirect_to_login_and_preserve_destination(self):
        for path in PROTECTED_GET_PATHS:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith("/login/"), response.url)
                self.assertIn("next=", response.url)

    def test_unknown_url_is_a_404(self):
        self.assertEqual(self.client.get("/does-not-exist/").status_code, 404)
        self.assertEqual(self.client.get("/reports/not-a-number/").status_code, 404)

    def test_unknown_qr_token_is_a_404(self):
        self.assertEqual(self.client.get("/tag/not-a-real-token/").status_code, 404)

    def test_public_report_qr_scan_requires_login(self):
        owner = make_user("contract-owner@example.test")
        report = make_report(owner)
        response = self.client.get(reverse("report-found", args=[report.public_id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"/login/?next={reverse('report-found', args=[report.public_id])}",
        )


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthenticatedRouteTests(TestCase):
    def setUp(self):
        self.user = make_user("routes@example.test")
        self.report = make_report(self.user)
        self.found = make_report(
            make_user("routes-finder@example.test"), "Found",
            title="Blue backpack found",
        )
        from core.models import Match

        self.match = Match.objects.create(
            lost=self.report, found=self.found, score=100,
        )
        self.client.force_login(self.user)

    def test_every_primary_page_renders_for_its_owner(self):
        paths = [
            reverse("dashboard"),
            reverse("reports"),
            reverse("report", args=[self.report.pk]),
            reverse("match", args=[self.match.pk]),
            reverse("qr-labels"),
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "<h1", count=1)

    def test_staff_management_page_renders_and_is_forbidden_to_others(self):
        self.assertEqual(self.client.get(reverse("management")).status_code, 403)
        self.client.force_login(make_user("contract-staff@example.test", staff=True))
        self.assertEqual(self.client.get(reverse("management")).status_code, 200)

    def test_write_endpoints_reject_get(self):
        write_paths = [
            reverse("edit", args=[self.report.pk]),
            reverse("qr-label-reactivate", args=[1]),
            reverse("qr-label-deactivate", args=[1]),
        ]
        for path in write_paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 405)

    def test_logout_is_post_only(self):
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CsrfContractTests(TestCase):
    def setUp(self):
        self.user = make_user("csrf@example.test")
        self.report = make_report(self.user)
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

    def test_state_changing_endpoints_reject_requests_without_a_token(self):
        from core.models import Draft

        draft = Draft.objects.create(owner=self.user)
        endpoints = [
            (reverse("create") + "?step=1", {"kind": "Lost"}),
            (reverse("draft", args=[draft.pk]) + "?step=1", {"kind": "Lost"}),
            (reverse("edit", args=[self.report.pk]), {}),
            (reverse("qr-labels"), {"item_name": "Bag", "contact_phone": "03001234567"}),
            (reverse("logout"), {}),
        ]
        if self.report.lost_matches.exists():
            match = self.report.lost_matches.first()
            endpoints.append((reverse("match", args=[match.pk]), {"action": "reject"}))
        for path, payload in endpoints:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, payload).status_code, 403)

    def test_login_and_registration_reject_requests_without_a_token(self):
        anonymous = Client(enforce_csrf_checks=True)
        self.assertEqual(anonymous.post(reverse("login"), {
            "username": self.user.email, "password": PASSWORD,
        }).status_code, 403)
        self.assertEqual(anonymous.post(reverse("register"), {
            "first_name": "New Person", "email": "new@example.test",
            "password1": PASSWORD, "password2": PASSWORD,
        }).status_code, 403)
