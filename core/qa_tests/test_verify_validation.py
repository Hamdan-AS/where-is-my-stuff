from django.test import TestCase, override_settings
from django.urls import reverse
from core.forms import LocationForm, Registration
from core.models import Draft, Report, User


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class VerifyValidationReproductions(TestCase):
    def test_location_column_boundary_publication(self):
        owner = User.objects.create_user(username='verifier@example.org', email='verifier@example.org', password='Safe-pass-482!')
        self.client.force_login(owner)
        self.client.get(reverse('create'))
        draft = Draft.objects.get(owner=owner)
        url = reverse('draft', args=[draft.pk])
        steps = [
            {'kind': 'Lost', 'title': 'Black backpack', 'category': 'Bag', 'event_date': '01-01-2026'},
            {'description': 'Black canvas backpack beside the gate', 'contact': '03001234567'},
            {'location': 'A' * 80, 'lat': '24.86', 'lng': '67.0', 'location_detail': 'Main gate'},
            {'colour': 'Black', 'kind': 'Backpack', 'material': 'Canvas', 'pockets': '2', 'mark': 'Scratch'},
        ]
        for step, data in enumerate(steps, 1):
            self.assertEqual(self.client.post(f'{url}?step={step}', data).status_code, 302)
        self.client.raise_request_exception = False
        response = self.client.post(f'{url}?step=5')
        self.assertEqual(response.status_code, 302, f'80-char model-limit control should publish; exception={response.exc_info}')
        self.assertEqual(Report.objects.get(owner=owner).location, 'A' * 80)

    def test_81_char_location_passes_form_but_publish_errors(self):
        location = 'A' * 81
        form = LocationForm({'location': location, 'lat': '24.86', 'lng': '67.0', 'location_detail': 'Main gate'})
        self.assertTrue(form.is_valid(), form.errors)
        owner = User.objects.create_user(username='longplace@example.org', email='longplace@example.org', password='Safe-pass-482!')
        self.client.force_login(owner)
        self.client.get(reverse('create'))
        draft = Draft.objects.get(owner=owner)
        url = reverse('draft', args=[draft.pk])
        steps = [
            {'kind': 'Lost', 'title': 'Black backpack', 'category': 'Bag', 'event_date': '01-01-2026'},
            {'description': 'Black canvas backpack beside the gate', 'contact': '03001234567'},
            {'location': location, 'lat': '24.86', 'lng': '67.0', 'location_detail': 'Main gate'},
            {'colour': 'Black', 'kind': 'Backpack', 'material': 'Canvas', 'pockets': '2', 'mark': 'Scratch'},
        ]
        for step, data in enumerate(steps, 1):
            self.assertEqual(self.client.post(f'{url}?step={step}', data).status_code, 302)
        self.client.raise_request_exception = False
        response = self.client.post(f'{url}?step=5')
        self.assertEqual(response.status_code, 302, f'Form-accepted place should publish; exception={response.exc_info}')

    def test_email_150_char_control_registers(self):
        email = 'a' * 60 + '@' + 'b' * 60 + '.com'
        self.assertEqual(len(email), 125)
        data = {'email': email, 'first_name': 'Test Person', 'password1': 'Safe-pass-482!', 'password2': 'Safe-pass-482!'}
        form = Registration(data)
        self.assertTrue(form.is_valid(), form.errors)
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email=email).exists())

    def test_long_valid_email_form_passes_but_registration_errors(self):
        email = 'a' * 64 + '@' + 'b' * 63 + '.' + 'c' * 30 + '.com'
        self.assertEqual(len(email), 163)
        data = {'email': email, 'first_name': 'Test Person', 'password1': 'Safe-pass-482!', 'password2': 'Safe-pass-482!'}
        form = Registration(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.client.raise_request_exception = False
        response = self.client.post(reverse('register'), data)
        self.assertLess(response.status_code, 500, f'Valid email must not crash; exception={response.exc_info}')
