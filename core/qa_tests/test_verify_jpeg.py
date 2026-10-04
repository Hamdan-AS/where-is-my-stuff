from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from PIL import Image, ImageFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from core.models import User, Draft


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class IndependentJpegVerification(TestCase):
    def test_intact_control_and_multiple_truncations(self):
        owner = User.objects.create_user(username='jpegverify@example.test', email='jpegverify@example.test')
        self.client.force_login(owner)
        self.client.raise_request_exception = False
        stream = BytesIO()
        Image.new('RGB', (173, 91), (32, 80, 170)).save(stream, format='JPEG', quality=87)
        jpeg = stream.getvalue()
        self.assertFalse(ImageFile.LOAD_TRUNCATED_IMAGES)
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            outcomes = []
            for cut in (0, 2, 8, 24, 64):
                with self.subTest(bytes_removed=cut):
                    draft = Draft.objects.create(owner=owner, data={'kind':'Lost', 'title':'Blue satchel', 'category':'Bag', 'event_date':date.today().isoformat()})
                    upload = SimpleUploadedFile('fresh.jpg', jpeg if cut == 0 else jpeg[:-cut], content_type='image/jpeg')
                    response = self.client.post(reverse('draft', args=[draft.pk])+'?step=2', {'description':'Blue satchel found beside library', 'contact':'03111234567', 'photo':upload})
                    outcomes.append((cut, response.status_code, str(response.exc_info[1]) if response.exc_info else None))
                    if cut == 0:
                        self.assertEqual(response.status_code, 302)
                        draft.refresh_from_db()
                        self.assertTrue(draft.photo)
                    else:
                        self.assertLess(response.status_code, 500, f'truncated JPEG should receive form error; outcomes={outcomes}')
