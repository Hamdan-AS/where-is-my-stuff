import tempfile
from datetime import date
from io import BytesIO
from unittest.mock import patch
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from core.forms import DetailsForm
from core.models import User, Draft, Report, QRLabel

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ErrorHandlingTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create_user(username='errors', email='errors@example.test', is_staff=True)
        self.client.force_login(self.user)
        self.client.raise_request_exception = False

    def test_missing_private_media_returns_404(self):
        report = Report.objects.create(owner=self.user, kind='Lost', title='Bag', category='Bag', event_date=date.today(), photo='report_photos/missing.jpg')
        draft = Draft.objects.create(owner=self.user, photo='draft_photos/missing.jpg')
        label = QRLabel.objects.create(owner=self.user, item_name='Bag', contact_phone='03001234567', token_hash='a'*64, expires_at=timezone.now(), qr_image='private_qr_labels/missing.png')
        for name, pk in [('report-photo', report.pk), ('draft-photo', draft.pk), ('qr-label-image', label.pk)]:
            with self.subTest(endpoint=name):
                self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 404)

    def test_malformed_management_report_id_is_client_error(self):
        for report_id in ['abc', '', '1.5', '?a', "1 OR 1=1"]:
            with self.subTest(report_id=report_id):
                response = self.client.post(reverse('management'), {'report': report_id, 'action': 'remove'})
                self.assertIn(response.status_code, (400, 404))

    def test_truncated_jpeg_is_form_error_not_server_error(self):
        stream = BytesIO()
        Image.new('RGB', (100, 100), 'red').save(stream, format='JPEG')
        upload = SimpleUploadedFile('truncated.jpg', stream.getvalue()[:-40], content_type='image/jpeg')
        draft = Draft.objects.create(owner=self.user, data={'kind':'Lost', 'title':'Bag', 'category':'Bag', 'event_date':date.today().isoformat()})
        response = self.client.post(reverse('draft', args=[draft.pk])+'?step=2', {'description':'Blue backpack with a stitched patch', 'contact':'03001234567', 'photo':upload})
        self.assertEqual(response.status_code, 200)
        self.assertIn('photo', response.context['form'].errors)

    def test_qr_generation_failure_rolls_back_row(self):
        with patch('core.views.make_label_qr', side_effect=OSError('storage unavailable')):
            response = self.client.post(reverse('qr-labels'), {'item_name':'Blue bag', 'contact_phone':'03001234567'})
        self.assertEqual(response.status_code, 500)
        self.assertFalse(QRLabel.objects.exists())

    def test_malformed_path_ids_return_404(self):
        for path in ['/reports/nope/photo/', '/drafts/-1/photo/', '/labels/1.5/image/', '/r/nope/qr/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_non_image_bytes_rejected(self):
        for payload in [b'', b'<svg onload="alert(1)">', b'\x89PNG\r\n\x1a\n']:
            with self.subTest(payload=payload):
                form = DetailsForm({'description':'Blue backpack', 'contact':'03001234567'}, {'photo':SimpleUploadedFile('image.png', payload, content_type='image/png')})
                self.assertFalse(form.is_valid())
                self.assertIn('photo', form.errors)

    def test_qr_storage_permission_failure_rolls_back_row(self):
        with patch('django.core.files.storage.FileSystemStorage._save', side_effect=PermissionError('read-only media')):
            response = self.client.post(reverse('qr-labels'), {'item_name':'Blue bag', 'contact_phone':'03001234567'})
        self.assertEqual(response.status_code, 500)
        self.assertFalse(QRLabel.objects.exists())
