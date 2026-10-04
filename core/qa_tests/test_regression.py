"""QA checks for current auth UI; deliberately avoid obsolete artwork selectors."""
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from core.models import User
from core.test_browser import _launch_browser

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CurrentAuthBrowserTests(StaticLiveServerTestCase):
    def test_current_login_controls_and_failed_login_retry(self):
        from playwright.sync_api import sync_playwright, expect
        User.objects.create_user(username='qa-browser@example.test', email='qa-browser@example.test', password='Strong-test-password-887!')
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright)
            page = browser.new_page()
            page.set_default_timeout(6000)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + '/login/?next=/reports/new/')
            expect(page.get_by_role('heading', name='Welcome back')).to_be_visible()
            for width in [320, 390, 768, 1280]:
                page.set_viewport_size({'width': width, 'height': 900})
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width)
                expect(page.get_by_role('button', name='Log in', exact=True)).to_be_visible()
            page.get_by_label('Email', exact=True).fill('qa-browser@example.test')
            password = page.get_by_label('Password', exact=True)
            password.fill('Wrong-password-887!')
            page.get_by_role('button', name='Log in', exact=True).click()
            expect(page.get_by_role('alert')).to_be_visible()
            expect(page.get_by_label('Email', exact=True)).to_have_value('qa-browser@example.test')
            password.fill('Strong-test-password-887!')
            page.get_by_role('button', name='Show password', exact=True).click()
            expect(password).to_have_attribute('type', 'text')
            page.get_by_role('button', name='Hide password', exact=True).click()
            expect(password).to_have_attribute('type', 'password')
            page.get_by_label('Remember me', exact=True).check()
            page.get_by_role('button', name='Log in', exact=True).click()
            expect(page.get_by_role('heading', name='What happened to your item?', exact=True)).to_be_visible()
            page.get_by_role('button', name='Log out', exact=True).click()
            page.get_by_role('link', name='Register', exact=True).click()
            expect(page.get_by_label('Full name', exact=True)).to_be_visible()
            for width in [320, 390, 768, 1280]:
                page.set_viewport_size({'width': width, 'height': 900})
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width)
            self.assertEqual(errors, [])
            browser.close()
