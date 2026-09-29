"""Optional real-browser check; runs against Django's isolated test database."""
import importlib.util
import unittest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings


@unittest.skipUnless(importlib.util.find_spec("playwright"), "Install requirements-dev.txt for browser checks")
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BrowserFlow(StaticLiveServerTestCase):
    def test_login_design_and_controls(self):
        from playwright.sync_api import sync_playwright, expect
        from .models import User

        User.objects.create_user(username="login@example.com", email="login@example.com", password="Strong-test-password-887!")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/login/?next=/reports/new/")
            expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
            page.evaluate("document.fonts.ready")
            self.assertTrue(page.evaluate("document.fonts.check('500 52px Fraunces') && document.fonts.check('400 14px Inter')"))
            self.assertTrue(page.evaluate(r"""async () => {
                const css = getComputedStyle(document.querySelector('.stage')).backgroundImage;
                const url = css.match(/url\("?([^"\)]+)"?\)/)[1];
                const image = new Image(); image.src = url;
                await image.decode(); return image.naturalWidth > 0;
            }"""))
            for width, height, name in [(1280, 900, "desktop"), (390, 844, "mobile"), (320, 720, "narrow")]:
                page.set_viewport_size({"width": width, "height": height})
                self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                self.assertTrue(page.evaluate("""() => {
                    const footer = document.querySelector('.auth-footer').getBoundingClientRect();
                    const main = document.querySelector('main').getBoundingClientRect();
                    return footer.top >= main.bottom - 1;
                }"""))
                page.screenshot(path=f"/tmp/wims-login-{name}.png", full_page=True)
            page.get_by_label("Email", exact=True).fill("login@example.com")
            password = page.get_by_label("Password", exact=True)
            password.fill("Strong-test-password-887!")
            page.get_by_role("button", name="Show password", exact=True).click()
            expect(password).to_have_attribute("type", "text")
            page.get_by_role("button", name="Hide password", exact=True).click()
            expect(password).to_have_attribute("type", "password")
            page.get_by_label("Remember me", exact=True).check()
            page.get_by_role("button", name="Log in", exact=True).click()
            expect(page.get_by_role("heading", name="What happened to your item?", exact=True)).to_be_visible()
            page.set_viewport_size({"width": 1280, "height": 900})
            page.get_by_role("button", name="Log out", exact=True).click()
            page.get_by_role("link", name="Register", exact=True).click()
            expect(page.get_by_label("Full name", exact=True)).to_be_visible()
            page.set_viewport_size({"width": 390, "height": 844})
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            page.screenshot(path="/tmp/wims-register-mobile.png", full_page=True)
            self.assertEqual(errors, [])
            browser.close()

    def test_wallet_wizard_desktop_and_mobile(self):
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/register/")
            page.get_by_label("Full name").fill("Browser Student")
            page.locator("#id_email").fill("browser@example.com")
            page.locator("#id_password1").fill("Strong-test-password-887!")
            page.locator("#id_password2").fill("Strong-test-password-887!")
            page.get_by_role("button", name="Register", exact=True).click()
            expect(page.get_by_role("heading", name="What happened to your item?", exact=True)).to_be_visible()
            page.get_by_label("Lost", exact=True).check()
            page.locator("#id_title").fill("Black wallet")
            page.get_by_role("button", name="Save and next").click()
            page.locator("#id_description").fill("Black leather wallet near library entrance")
            page.locator("#id_contact").fill("03001234567")
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("heading", name="3. Location", exact=True)).to_be_visible()
            page.locator("#id_location").fill("Central Library")
            page.locator("#id_lat").fill("24.86")
            page.locator("#id_lng").fill("67.001")
            page.get_by_label("Location description").fill("Near entrance")
            page.get_by_role("button", name="Save and next").click()
            page.locator("#id_colour").select_option("Black")
            page.get_by_label("Wallet material").select_option("Leather")
            page.get_by_label("Visible logo?").select_option("No")
            page.wait_for_load_state("networkidle")
            page.get_by_label("CNIC", exact=True).check()
            expect(page.get_by_label("Full 13-digit CNIC")).to_be_visible()
            page.get_by_label("Cash", exact=True).check()
            expect(page.get_by_label("Cash approximate amount")).to_be_visible()
            expect(page.get_by_label("Number of bank cards")).to_have_count(0)
            expect(page.get_by_role("button", name="Update questions from my selections")).to_have_count(0)
            page.get_by_label("Full 13-digit CNIC").fill("4210112345671")
            page.get_by_label("Cash approximate amount").select_option("Below Rs. 500")
            page.get_by_label("Cash denominations").select_option("Mixed notes")
            page.get_by_label("Wallet distinguishing mark").select_option("None")
            page.set_viewport_size({"width": 390, "height": 844})
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            page.screenshot(path="/tmp/wims-django-wallet-mobile.png", full_page=True)
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("button", name="Submit report", exact=True)).to_have_count(1)
            page.screenshot(path="/tmp/wims-django-review-mobile.png", full_page=True)
            page.get_by_role("button", name="Submit report", exact=True).click()
            expect(page.get_by_role("heading", name="Black wallet")).to_be_visible()
            self.assertEqual(errors, [])
            browser.close()
