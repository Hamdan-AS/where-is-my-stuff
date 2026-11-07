"""Normal account behaviour: registration, sign-in, sessions, and sign-out."""

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.models import Draft, User
from tests.support import PASSWORD, make_user, make_report


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class RegistrationTests(TestCase):
    def valid_payload(self, **overrides):
        payload = {
            "first_name": "Sara Ahmed",
            "email": "Sara@Example.test",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        payload.update(overrides)
        return payload

    def test_valid_registration_creates_a_lowercase_email_identity_and_signs_in(self):
        response = self.client.post(reverse("register"), self.valid_payload())
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)
        user = User.objects.get(email="sara@example.test")
        self.assertEqual(user.username, "sara@example.test")
        self.assertEqual(user.first_name, "Sara Ahmed")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_registration_rejects_an_email_that_already_exists_in_any_case(self):
        make_user("taken@example.test")
        response = self.client.post(reverse("register"), self.valid_payload(
            email="TAKEN@example.test",
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")
        self.assertEqual(User.objects.count(), 1)

    def test_registration_enforces_password_validators(self):
        weak_passwords = [
            "short",
            "123456789012345",
            "password",
        ]
        for password in weak_passwords:
            with self.subTest(password=password):
                response = self.client.post(reverse("register"), self.valid_payload(
                    email=f"weak-{password[:4]}@example.test",
                    password1=password,
                    password2=password,
                ))
                self.assertEqual(response.status_code, 200)
                self.assertFalse(User.objects.filter(
                    email=f"weak-{password[:4]}@example.test",
                ).exists())

    def test_registration_requires_a_human_name(self):
        response = self.client.post(reverse("register"), self.valid_payload(
            first_name="12345",
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Include words")
        self.assertFalse(User.objects.filter(email="sara@example.test").exists())

    def test_register_page_links_back_to_login(self):
        response = self.client.get(reverse("register"))
        self.assertContains(response, 'href="/login/"')
        self.assertContains(response, "Create an account")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class LoginTests(TestCase):
    def setUp(self):
        self.user = make_user("login@example.test", first_name="Login Person")

    def post_login(self, client=None, **overrides):
        client = client or self.client
        payload = {"username": self.user.email, "password": PASSWORD}
        payload.update(overrides)
        return client.post(reverse("login"), payload)

    def test_login_accepts_email_in_any_case_and_with_surrounding_space(self):
        response = self.post_login(username="  LOGIN@EXAMPLE.TEST ")
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)

    def test_failed_login_keeps_the_email_visible_but_never_the_password(self):
        response = self.post_login(password="Wrong-password-123!")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="login@example.test"')
        self.assertContains(response, 'role="alert"')
        self.assertNotContains(response, "Wrong-password-123!")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_remember_me_controls_whether_the_session_survives_browser_close(self):
        for remember in (False, True):
            with self.subTest(remember=remember):
                client = Client()
                payload = {"username": self.user.email, "password": PASSWORD}
                if remember:
                    payload["remember_me"] = "on"
                response = client.post(reverse("login"), payload)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    client.session.get_expire_at_browser_close(), not remember,
                )
                self.assertEqual(
                    bool(response.cookies["sessionid"]["expires"]), remember,
                )

    def test_internal_next_destination_is_honoured(self):
        response = self.post_login(next=reverse("qr-labels"))
        self.assertRedirects(
            response, reverse("qr-labels"), fetch_redirect_response=False,
        )

    def test_external_next_destination_is_ignored(self):
        response = self.post_login(next="https://evil.example/phish")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("create"))

    def test_first_login_goes_to_report_creation_but_returning_users_go_to_dashboard(self):
        new_user = make_user("fresh@example.test")
        client = Client()
        response = client.post(reverse("login"), {
            "username": new_user.email, "password": PASSWORD,
        })
        self.assertRedirects(response, reverse("create"), fetch_redirect_response=False)

        make_report(self.user)
        client = Client()
        response = client.post(reverse("login"), {
            "username": self.user.email, "password": PASSWORD,
        })
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_first_login_resumes_the_newest_draft(self):
        draft = Draft.objects.create(owner=self.user, data={"title": "Saved draft"})
        response = self.post_login()
        self.assertRedirects(
            response, reverse("draft", args=[draft.pk]), fetch_redirect_response=False,
        )

    def test_logout_clears_the_authenticated_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
