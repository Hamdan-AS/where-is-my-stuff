import tempfile
from datetime import date
from io import BytesIO
from PIL import Image, ImageDraw
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from core.models import User, Draft


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TruncatedJpegWizardVerification(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.user = User.objects.create_user(username='media-check', email='media-check@example.test', password='Password123!')
        self.client.force_login(self.user)
        self.client.raise_request_exception = False
        self.draft = Draft.objects.create(owner=self.user, data={
            'kind': 'Lost', 'title': 'Blue backpack', 'category': 'Bag',
            'event_date': date.today().isoformat(),
        })

    def jpeg_bytes(self):
        image = Image.new('RGB', (180, 120), '#2874a6')
        draw = ImageDraw.Draw(image)
        for x in range(0, 180, 12):
            draw.line((x, 0, 179 - x // 2, 119), fill='#f2c94c', width=3)
        output = BytesIO()
        image.save(output, format='JPEG', quality=93)
        return output.getvalue()

    def wizard_post(self, data):
        return self.client.post(
            reverse('draft', args=[self.draft.pk]) + '?step=2',
            {'description': 'Blue backpack with yellow diagonal pattern', 'contact': '03001234567', 'photo': SimpleUploadedFile('pattern.jpg', data, content_type='image/jpeg')},
        )

    def test_intact_control_is_accepted(self):
        response = self.wizard_post(self.jpeg_bytes())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Draft.objects.get(pk=self.draft.pk).photo.name)

    def test_truncated_jpeg_is_rejected_without_server_error(self):
        payload = self.jpeg_bytes()
        self.assertGreater(len(payload), 200)
        response = self.wizard_post(payload[:-173])
        self.assertEqual(response.status_code, 200)
        self.assertIn('photo', response.context['form'].errors)
