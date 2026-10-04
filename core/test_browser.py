"""Optional real-browser check; runs against Django's isolated test database."""
import importlib.util
import os
import re
import tempfile
import unittest
from datetime import timedelta
from unittest.mock import patch
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.utils import timezone


def _launch_browser(playwright):
    """Use installed Chrome when available, otherwise Playwright's browser."""
    chrome_paths = (
        os.environ.get("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
    )
    executable = next((path for path in chrome_paths if path and os.path.exists(path)), None)
    options = {"headless": True}
    if executable:
        options["executable_path"] = executable
    return playwright.chromium.launch(**options)


@unittest.skipUnless(importlib.util.find_spec("playwright"), "Install requirements-dev.txt for browser checks")
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BrowserFlow(StaticLiveServerTestCase):
    def test_responsive_pages_and_drawer(self):
        from playwright.sync_api import sync_playwright, expect
        from .models import User, Report, Match, Draft
        owner = User.objects.create_user(username="responsive@example.com", email="responsive@example.com", password="test", is_staff=True)
        finder = User.objects.create_user(username="responsive-finder@example.com", email="responsive-finder@example.com", password="test")
        common = dict(title="Blue backpack with a distinctive stitched patch", category="Bag", description="A blue backpack with a stitched patch and a long shoulder strap.", location="Central Library", location_detail="Beside the entrance", event_date=timezone.localdate(), contact="03001234567", answers={})
        lost = Report.objects.create(owner=owner, kind="Lost", **common)
        found = Report.objects.create(owner=finder, kind="Found", **common)
        Report.objects.create(owner=owner, kind="Found", **common)
        match = Match.objects.create(lost=lost, found=found, score=90)
        draft = Draft.objects.create(owner=owner, data={**common, "kind":"Lost", "event_date":timezone.localdate().isoformat(), "lat":"24.8607", "lng":"67.0011", "answers":{"colour":"Blue", "kind":"Backpack", "material":"Fabric", "pockets":"2", "mark":"Stitched patch"}})
        self.client.force_login(owner)
        with sync_playwright() as p:
            browser = _launch_browser(p)
            context = browser.new_context()
            context.add_cookies([{"name":"sessionid", "value":self.client.cookies["sessionid"].value, "url":self.live_server_url}])
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            paths = ["/", "/reports/", f"/reports/{lost.pk}/", f"/matches/{match.pk}/", "/labels/", "/management/"]
            paths += [f"/drafts/{draft.pk}/?step={step}" for step in range(1, 6)]
            for width in [320, 390, 768, 900, 1024, 1440]:
                page.set_viewport_size({"width":width, "height":844})
                for path in paths:
                    page.goto(self.live_server_url + path)
                    self.assertEqual(page.locator("h1").count(), 1, (width, path))
                    if "?step=" in path:
                        self.assertEqual(page.url, self.live_server_url + path)
                    self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, path))
                    if width == 390:
                        name = path.strip("/").replace("/", "-").replace("?", "-").replace("=", "-")
                        page.screenshot(path=os.path.join(tempfile.gettempdir(), "wims-responsive-" + name + ".png"), full_page=True)
                page.goto(self.live_server_url + "/reports/")
                if width <= 900:
                    self.assertTrue(page.locator("#app-sidebar").evaluate("element => element.inert"))
                    page.get_by_role("button", name="Menu", exact=True).click()
                    expect(page.get_by_role("button", name="Close menu")).to_be_focused()
                    expect(page.locator(".sidebar-account button")).to_be_visible()
                    page.keyboard.press("Shift+Tab")
                    expect(page.locator(".sidebar-account button")).to_be_focused()
                    page.keyboard.press("Tab")
                    expect(page.get_by_role("button", name="Close menu")).to_be_focused()
                    page.keyboard.press("Escape")
                    expect(page.get_by_role("button", name="Menu", exact=True)).to_be_focused()
                    page.get_by_role("button", name="Menu", exact=True).click()
                    page.set_viewport_size({"width":1200, "height":844})
                    expect(page.locator("body")).not_to_have_class(re.compile(r".*sidebar-open.*"))
                    self.assertFalse(page.locator(".workspace").evaluate("element => element.inert"))
                if width <= 760:
                    page.set_viewport_size({"width":width, "height":844})
                    expect(page.locator(".data-table td[data-label='Reported']").first).to_be_visible()
                    self.assertTrue(page.locator(".table-wrap").evaluate("element => element.scrollWidth <= element.clientWidth"))
            self.assertEqual(errors, [])
            browser.close()

    def setUp(self):
        super().setUp()
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        media_settings = override_settings(MEDIA_ROOT=media.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

    def test_login_design_and_controls(self):
        from playwright.sync_api import sync_playwright, expect
        from .models import User

        User.objects.create_user(username="login@example.com", email="login@example.com", password="Strong-test-password-887!")
        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.set_default_timeout(6000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/login/?next=/reports/new/")
            expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
            page.evaluate("document.fonts.ready")
            self.assertTrue(page.evaluate("document.fonts.check('500 50px Fraunces') && document.fonts.check('400 16px Inter')"))
            expect(page.get_by_role("list", name="How it works")).to_be_visible()
            for width, height, name in [(1280, 900, "desktop"), (390, 844, "mobile"), (320, 720, "narrow")]:
                page.set_viewport_size({"width": width, "height": height})
                self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                expect(page.get_by_role("button", name="Log in", exact=True)).to_be_visible()
                page.screenshot(path=os.path.join(tempfile.gettempdir(), f"wims-login-{name}.png"), full_page=True)
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
            page.screenshot(path=os.path.join(tempfile.gettempdir(), "wims-register-mobile.png"), full_page=True)
            self.assertEqual(errors, [])
            browser.close()

    def test_wallet_wizard_desktop_and_mobile(self):
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            browser = _launch_browser(p)
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
            page.screenshot(path=os.path.join(tempfile.gettempdir(), "wims-django-wallet-mobile.png"), full_page=True)
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("button", name="Submit report", exact=True)).to_have_count(1)
            page.screenshot(path=os.path.join(tempfile.gettempdir(), "wims-django-review-mobile.png"), full_page=True)
            page.get_by_role("button", name="Submit report", exact=True).click()
            expect(page.get_by_role("link", name="Black wallet", exact=True)).to_be_visible()
            self.assertEqual(errors, [])
            browser.close()

    def test_discard_draft_requires_confirmation_with_and_without_javascript(self):
        from playwright.sync_api import sync_playwright, expect
        from django.db import connections
        from .models import User, Draft

        owner = User.objects.create_user(username="discard@example.com", email="discard@example.com", password="test")
        self.client.force_login(owner)
        with patch.dict(os.environ, {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"}), sync_playwright() as p:
            browser = _launch_browser(p)
            for javascript in (True, False):
                draft = Draft.objects.create(owner=owner, data={"title": "Saved blue backpack"})
                context = browser.new_context(java_script_enabled=javascript, viewport={"width": 390, "height": 844})
                context.add_cookies([{"name": "sessionid", "value": self.client.cookies["sessionid"].value, "url": self.live_server_url}])
                page = context.new_page()
                page.goto(self.live_server_url + "/reports/new/")
                expect(page.get_by_text("permanently discards this saved draft and its photo", exact=False)).to_be_visible()
                confirmation = page.get_by_role("checkbox", name="I understand that this saved draft will be permanently discarded.")
                discard = page.get_by_role("button", name="Discard draft and start new", exact=True)
                discard.click()
                expect(confirmation).not_to_be_checked()
                self.assertTrue(Draft.objects.filter(pk=draft.pk).exists())
                self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                page.screenshot(path=os.path.join(tempfile.gettempdir(), f"wims-discard-javascript-{javascript}.png"), full_page=True)
                page.get_by_role("link", name="Continue the draft", exact=True).click()
                self.assertIn(f"/drafts/{draft.pk}/", page.url)
                page.goto(self.live_server_url + "/reports/new/")
                confirmation.check()
                discard.click()
                expect(page.get_by_role("heading", name="What happened to your item?", exact=True)).to_be_visible()
                self.assertFalse(Draft.objects.filter(pk=draft.pk).exists())
                replacement = Draft.objects.get(owner=owner, report__isnull=True)
                self.assertEqual(replacement.data, {})
                replacement.delete()
                context.close()
                connections.close_all()
            browser.close()

    def test_report_photo_upload_render_edit_replace_remove_and_match_access(self):
        from io import BytesIO
        from pathlib import Path
        from PIL import Image
        from playwright.sync_api import sync_playwright, expect
        from .models import Match, Report, User

        owner = User.objects.create_user(
            username="photo-flow@example.com", email="photo-flow@example.com",
            password="Strong-test-password-887!",
        )
        finder = User.objects.create_user(
            username="photo-finder@example.com", email="photo-finder@example.com",
            password="Strong-test-password-887!",
        )
        outsider = User.objects.create_user(
            username="photo-outsider@example.com", email="photo-outsider@example.com",
            password="Strong-test-password-887!",
        )
        images = tempfile.TemporaryDirectory()
        self.addCleanup(images.cleanup)
        original_path = Path(images.name) / "backpack.png"
        replacement_path = Path(images.name) / "replacement.webp"
        Image.new("RGB", (2400, 1200), (28, 90, 40)).save(original_path, "PNG")
        Image.new("RGB", (640, 480), (30, 60, 210)).save(replacement_path, "WEBP")

        # Phase one: publish through the browser, then leave Playwright before ORM access.
        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(self.live_server_url + "/login/")
            page.get_by_label("Email", exact=True).fill(owner.email)
            page.get_by_label("Password", exact=True).fill("Strong-test-password-887!")
            page.get_by_role("button", name="Log in", exact=True).click()

            # Upload a full landscape PNG through the actual report wizard.
            page.get_by_label("Lost", exact=True).check()
            page.locator("#id_title").fill("Green backpack")
            page.locator("#id_category").select_option("Bag")
            page.get_by_role("button", name="Save and next").click()
            photo_input = page.locator("#id_photo")
            expect(photo_input).to_have_attribute("accept", "image/jpeg,image/png,image/webp")
            page.locator("#id_description").fill("Green backpack with a stitched silver patch")
            page.locator("#id_contact").fill("03001234567")
            page.locator("#id_photo").set_input_files(str(original_path))
            expect(page.locator("[data-photo-preview]")).to_be_visible()
            self.assertTrue(page.locator("[data-photo-preview-image]").evaluate("img => img.complete && img.naturalWidth === 2400 && img.naturalHeight === 1200"))
            self.assertEqual(page.locator("[data-photo-preview-name]").inner_text(), "backpack.png")
            page.get_by_role("button", name="Save and next").click()
            page.get_by_role("link", name="Back").click()
            saved_draft_image = page.locator(".existing-photo img")
            expect(saved_draft_image).to_be_visible()
            self.assertTrue(saved_draft_image.evaluate("img => img.complete && img.naturalWidth === 1800 && img.naturalHeight === 900"))
            page.get_by_role("button", name="Save and next").click()
            page.locator("#id_location").fill("Central Library")
            page.locator("#id_lat").fill("24.8607")
            page.locator("#id_lng").fill("67.0011")
            page.get_by_label("Location description").fill("Near entrance")
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("heading", name="4. Private matching details")).to_be_visible()
            page.locator("#id_colour").select_option("Green")
            page.locator("#id_kind").select_option("Backpack")
            page.locator("#id_material").select_option("Fabric")
            page.locator("#id_pockets").select_option("2")
            page.locator("#id_mark").select_option("None")
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("heading", name="5. Review your report")).to_be_visible()
            expect(page.locator(".review-photo img")).to_be_visible()
            self.assertTrue(page.locator(".review-photo img").evaluate("img => img.complete && img.naturalWidth === 1800 && img.naturalHeight === 900"))
            page.get_by_role("button", name="Submit report").click()
            match_id = re.search(r"#report-(\d+)", page.url)
            self.assertIsNotNone(match_id, page.url)
            report_id = int(match_id.group(1))
            browser.close()

        report = Report.objects.get(pk=report_id, owner=owner, title="Green backpack")
        found = Report.objects.create(
            owner=finder, kind="Found", title="Green backpack recovered", category="Bag",
            description="Green backpack with a stitched silver patch", location="Central Library",
            location_detail="Near entrance", event_date=report.event_date,
            contact="03001112222", answers={"colour": "Green", "kind": "Backpack", "material": "Fabric", "pockets": "2", "mark": "None"},
        )
        match = Match.objects.create(lost=report, found=found, score=90)

        # Phase two: inspect rendering and authorization across owner/finder accounts,
        # then use the edit flow to verify preserve, replace, and remove.
        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            browser_errors = []
            page.on("pageerror", lambda error: browser_errors.append(str(error)))
            page.goto(self.live_server_url + "/login/")
            page.get_by_label("Email", exact=True).fill(owner.email)
            page.get_by_label("Password", exact=True).fill("Strong-test-password-887!")
            page.get_by_role("button", name="Log in", exact=True).click()
            page.goto(self.live_server_url + f"/reports/{report.pk}/")
            report_image = page.locator(".report-photo img")
            expect(report_image).to_be_visible()
            self.assertTrue(report_image.evaluate("img => img.complete && img.naturalWidth === 1800 && img.naturalHeight === 900"))
            self.assertLessEqual(report_image.evaluate("img => img.getBoundingClientRect().height"), 420)
            self.assertEqual(page.locator(".report-photo figcaption").inner_text(), "Visible to you and people in this report’s match.")
            for width in (1024, 1366, 1920):
                page.set_viewport_size({"width": width, "height": 1080})
                self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                desktop_box = report_image.evaluate("img => ({width: img.getBoundingClientRect().width, height: img.getBoundingClientRect().height, parent: img.parentElement.getBoundingClientRect().width})")
                self.assertLessEqual(desktop_box["width"], desktop_box["parent"])
                self.assertLessEqual(desktop_box["height"], 420)
            page.set_viewport_size({"width": 1280, "height": 900})

            # Photo URLs are not public to signed-out users or unrelated accounts.
            photo_url = report_image.get_attribute("src")
            context = browser.new_context()
            outsider_page = context.new_page()
            outsider_page.goto(self.live_server_url + "/login/")
            outsider_page.get_by_label("Email", exact=True).fill(outsider.email)
            outsider_page.get_by_label("Password", exact=True).fill("Strong-test-password-887!")
            outsider_page.get_by_role("button", name="Log in", exact=True).click()
            outsider_page.goto(self.live_server_url + photo_url)
            expect(outsider_page.locator("body")).to_contain_text("Not Found")
            outsider_page.close()
            context.close()

            # A legitimate match participant sees the same normalized photo on match review.
            finder_context = browser.new_context()
            finder_page = finder_context.new_page()
            finder_page.goto(self.live_server_url + "/login/")
            finder_page.get_by_label("Email", exact=True).fill(finder.email)
            finder_page.get_by_label("Password", exact=True).fill("Strong-test-password-887!")
            finder_page.get_by_role("button", name="Log in", exact=True).click()
            finder_page.goto(self.live_server_url + f"/matches/{match.pk}/")
            match_image = finder_page.locator(".match-item-photo").first
            expect(match_image).to_be_visible()
            self.assertTrue(match_image.evaluate("img => img.complete && img.naturalWidth === 1800 && img.naturalHeight === 900"))
            finder_context.close()

            # Editing without a new file preserves the image; replacement works; removal clears it.
            page.goto(self.live_server_url + f"/reports/{report.pk}/")
            page.get_by_role("button", name="Edit report").click()
            edit_draft_url = page.url.split("?", 1)[0]
            page.goto(edit_draft_url + "?step=2")
            expect(page.locator(".existing-photo img")).to_be_visible()
            page.locator("#id_description").fill("Green backpack near entrance, updated")
            page.get_by_role("button", name="Save and next").click()
            page.get_by_role("link", name="Back").click()
            expect(page.locator(".existing-photo img")).to_be_visible()
            page.locator("#id_photo").set_input_files(str(replacement_path))
            expect(page.locator("[data-photo-preview]")).to_be_visible()
            expect(page.locator(".existing-photo")).to_be_hidden()
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("heading", name="3. Location")).to_be_visible()
            expect(page.locator("#id_location")).to_have_value("Central Library")
            expect(page.locator("#id_lat")).to_have_value("24.860700")
            expect(page.locator("#id_lng")).to_have_value("67.001100")
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("heading", name="4. Private matching details")).to_be_visible()
            expect(page.locator("#id_colour")).to_have_value("Green")
            expect(page.locator("#id_kind")).to_have_value("Backpack")
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("heading", name="5. Review your report")).to_be_visible()
            expect(page.locator(".review-photo img")).to_be_visible()
            review_image = page.locator(".review-photo img")
            review_image_state = review_image.evaluate("img => ({complete: img.complete, width: img.naturalWidth, height: img.naturalHeight, src: img.src})")
            self.assertEqual((review_image_state["complete"], review_image_state["width"], review_image_state["height"]), (True, 640, 480), review_image_state)
            page.get_by_role("button", name="Submit report").click()
            page.goto(self.live_server_url + f"/reports/{report.pk}/")
            replaced_image = page.locator(".report-photo img")
            expect(replaced_image).to_be_visible()
            self.assertTrue(replaced_image.evaluate("img => img.complete && img.naturalWidth === 640 && img.naturalHeight === 480"))
            page.get_by_role("button", name="Edit report").click()
            edit_draft_url = page.url.split("?", 1)[0]
            page.goto(edit_draft_url + "?step=2")
            page.get_by_label("Remove the current photo").check()
            expect(page.locator(".existing-photo")).to_be_hidden()
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("heading", name="3. Location")).to_be_visible()
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("heading", name="4. Private matching details")).to_be_visible()
            page.get_by_role("button", name="Save and next").click()
            expect(page.get_by_role("heading", name="5. Review your report")).to_be_visible()
            self.assertEqual(page.locator(".review-photo img").count(), 0)
            page.get_by_role("button", name="Submit report").click()
            self.assertEqual(browser_errors, [])
            browser.close()

        report.refresh_from_db()
        # A final edit/removal cycle is completed in a browser above; DB state confirms removal.
        self.assertFalse(report.photo)

    def test_next_meeting_hour_is_a_valid_pakistan_time(self):
        from playwright.sync_api import sync_playwright, expect
        from .models import Match, Report, User

        owner = User.objects.create_user(
            username="meeting-owner@example.com", email="meeting-owner@example.com",
            password="Strong-test-password-887!",
        )
        finder = User.objects.create_user(
            username="meeting-finder@example.com", email="meeting-finder@example.com",
            password="Strong-test-password-887!",
        )
        answers = {"colour": "Black", "kind": "Backpack", "material": "Fabric",
                   "pockets": "2", "mark": "None"}
        common = {
            "title": "Black backpack", "category": "Bag",
            "description": "Black backpack with blue patch near library",
            "location": "Central Library", "lat": "24.86070000",
            "lng": "67.00110000", "location_detail": "Near entrance",
            "event_date": timezone.localdate(), "contact": "03001234567",
            "answers": answers,
        }
        lost = Report.objects.create(owner=owner, kind="Lost", **common)
        found = Report.objects.create(owner=finder, kind="Found", **common)
        match = Match.objects.create(lost=lost, found=found, score=100)

        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(self.live_server_url + "/login/")
            page.get_by_label("Email", exact=True).fill(finder.email)
            page.get_by_label("Password", exact=True).fill("Strong-test-password-887!")
            page.get_by_role("button", name="Log in", exact=True).click()
            page.goto(self.live_server_url + f"/matches/{match.pk}/")
            page.get_by_role("button", name="Use next available hour").click()
            meeting_time = page.locator('[name="meeting_at"]')
            expect(meeting_time).to_have_value(
                re.compile(r"\d{2}-\d{2}-\d{2} \d{2}:\d{2} (AM|PM)")
            )
            self.assertTrue(meeting_time.evaluate("input => input.checkValidity()"))
            page.get_by_label("Meeting place").fill("NED Security Office")
            page.get_by_role("button", name="Propose handover").click()
            expect(page.get_by_role("heading", name="Handover Proposed")).to_be_visible()
            self.assertFalse(page.get_by_text("Participant contact details").count())
            browser.close()

    def test_personal_qr_label_creation_expiry_and_same_code_reactivation(self):
        from playwright.sync_api import sync_playwright, expect
        from .models import QRLabel, User
        from .qr_labels import token_digest

        owner = User.objects.create_user(
            username="qr-browser@example.com", email="qr-browser@example.com",
            password="Strong-test-password-887!",
        )
        token = "browser-fixed-random-token-A79"
        session_state = None
        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport={"width": 1100, "height": 850})
            page.goto(self.live_server_url + "/labels/")
            page.get_by_label("Email", exact=True).fill(owner.email)
            page.get_by_label("Password", exact=True).fill("Strong-test-password-887!")
            page.get_by_role("button", name="Log in", exact=True).click()
            expect(page.get_by_role("heading", name="QR labels for your things")).to_be_visible()

            page.get_by_label("Item name:").fill("Blue backpack")
            page.get_by_label("Phone number shown to a finder:").fill("03001234567")
            with patch("core.views.new_label_token", return_value=token):
                page.get_by_role("button", name="Create QR label").click()

            image = page.locator(".qr-label-image")
            expect(image).to_be_visible()
            self.assertTrue(image.evaluate("image => image.complete && image.naturalWidth > 0"))
            expect(page.get_by_text("Active until", exact=False)).to_be_visible()
            session_state = page.context.storage_state()
            browser.close()

        label = QRLabel.objects.get(owner=owner)
        self.assertEqual(label.token_hash, token_digest(token))
        original_hash, original_image = label.token_hash, label.qr_image.name
        label.expires_at = timezone.now() - timedelta(seconds=1)
        label.save(update_fields=["expires_at"])

        public_url = self.live_server_url + "/tag/" + token + "/"
        with sync_playwright() as p:
            browser = _launch_browser(p)
            context = browser.new_context(storage_state=session_state)
            page = context.new_page()
            page.goto(public_url)
            expect(page.get_by_role("heading", name="This QR label is inactive")).to_be_visible()
            expect(page.get_by_text("03001234567")).to_have_count(0)

            page.goto(self.live_server_url + "/labels/")
            page.get_by_role("button", name="Reactivate for six months").click()
            page.goto(public_url)
            expect(page.get_by_role("link", name="Call 03001234567")).to_be_visible()
            expect(page.get_by_text("responsible for agreeing how to return")).to_be_visible()
            browser.close()

        label.refresh_from_db()
        self.assertEqual(label.token_hash, original_hash)
        self.assertEqual(label.qr_image.name, original_image)
