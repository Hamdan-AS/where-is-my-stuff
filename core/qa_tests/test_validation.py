from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from core.forms import TypeForm, DetailsForm, LocationForm, MatchingForm, Registration
from core.models import User, Draft, Report


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ValidationRequestTests(TestCase):
    def test_accepted_long_place_can_be_published(self):
        user = User.objects.create_user(username='qa@example.org', email='qa@example.org', password='Safe-pass-482!')
        self.client.force_login(user)
        response = self.client.get(reverse('create'))
        self.assertEqual(response.status_code, 302)
        draft = Draft.objects.get(owner=user)
        url = reverse('draft', args=[draft.pk])
        steps = [
            {'kind': 'Lost', 'title': 'Black backpack', 'category': 'Bag', 'event_date': '01-01-2026'},
            {'description': 'Black canvas backpack beside the gate', 'contact': '03001234567'},
            {'location': 'A' * 81, 'lat': '24.86', 'lng': '67.0', 'location_detail': 'Main gate'},
            {'colour': 'Black', 'kind': 'Backpack', 'material': 'Canvas', 'pockets': '2', 'mark': 'Scratch'},
        ]
        for step, data in enumerate(steps, 1):
            self.assertEqual(self.client.post(f'{url}?step={step}', data).status_code, 302)
        self.client.raise_request_exception = False
        response = self.client.post(f'{url}?step=5')
        self.assertEqual(response.status_code, 302, f'A place accepted by the wizard must publish without HTTP 500; exception={response.exc_info}')
        self.assertEqual(Report.objects.get(owner=user).location, 'A' * 81)

    def test_long_valid_email_registration_does_not_crash(self):
        email = 'a' * 64 + '@' + 'b' * 63 + '.' + 'c' * 30 + '.com'
        data = {'email': email, 'first_name': 'Test Person', 'password1': 'Safe-pass-482!', 'password2': 'Safe-pass-482!'}
        form = Registration(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.client.raise_request_exception = False
        response = self.client.post(reverse('register'), data)
        self.assertLess(response.status_code, 500, f'Valid long email must register or produce a form error, not HTTP 500; exception={response.exc_info}')


class ValidationBoundaryTests(SimpleTestCase):
    def test_malformed_coordinate_values_rejected(self):
        for value in ['', 'NaN', '-NaN', 'sNaN', 'Infinity', '-Infinity', '1e999999', '1e-999999', '90.00000001', '-90.00000001', '9' * 10000, '\x00', '<script>alert(1)</script>']:
            form = LocationForm({'location': 'Main Gate', 'lat': value, 'lng': '67', 'location_detail': 'Near stairs'})
            with self.subTest(value=value[:30]):
                self.assertFalse(form.is_valid())

    def test_dynamic_wallet_count_boundaries_rejected(self):
        for count in ['', '-1', '0', '6', '2147483647', '9' * 10000, 'NaN', '1.5', '\x00']:
            data = {'colour': 'Black', 'material': 'Leather', 'logo': 'No', 'contents': ['Bank cards'], 'mark': 'Scratch', 'bank_count': count, 'bank_1_issuer': 'HBL', 'bank_1_suffix': '1' * 16}
            with self.subTest(count=count[:30]):
                form = MatchingForm(data, category='Wallet / Purse', selection=data)
                self.assertFalse(form.is_valid())

    def test_contact_and_description_boundaries_rejected(self):
        for value in ['', '0' * 10, '0' * 12, '0' + '\u0661' * 10, '0' + '\uff11' * 10, '0300\x00123456', '0' * 10000]:
            with self.subTest(value=value[:30]):
                self.assertFalse(DetailsForm({'description': 'Black bag', 'contact': value}).is_valid())
        for description in ['', 'x' * 2001, 'bag\x00', 'bag\u202e']:
            with self.subTest(description=description[:30]):
                self.assertFalse(DetailsForm({'description': description, 'contact': '03001234567'}).is_valid())
