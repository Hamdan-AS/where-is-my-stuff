from datetime import date

from django.test import TestCase, override_settings
from core.models import User, Report


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SearchNulVerification(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='search-check@example.test',
            email='search-check@example.test', password='Safe-pass-482!',
        )
        Report.objects.create(
            owner=cls.user, kind='Lost', title='Blue backpack', category='Bag',
            event_date=date.today(), location='North campus', contact='03001234567',
        )

    def test_nul_and_control_search_requests(self):
        self.client.force_login(self.user)
        self.client.raise_request_exception = False

        # The percent-encoded URL becomes an actual NUL in request.GET after
        # Django parses the query string.
        nul_response = self.client.get('/reports/?q=%00')
        print('NUL status:', nul_response.status_code)
        print('NUL exception:', repr(nul_response.exc_info))

        empty_response = self.client.get('/reports/?q=')
        self.assertEqual(empty_response.status_code, 200)
        valid_response = self.client.get('/reports/?q=backpack')
        self.assertEqual(valid_response.status_code, 200)
        self.assertEqual(len(valid_response.context['page_obj']), 1)
        self.assertNotEqual(nul_response.status_code, 500)
