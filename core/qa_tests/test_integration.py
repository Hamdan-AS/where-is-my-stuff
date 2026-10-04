from datetime import date
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from core.models import User, Report, Draft, Match


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class IntegrationContractTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='integration@example.test', email='integration@example.test', password='Safe-pass-482!')
        self.other = User.objects.create_user(username='other@example.test', email='other@example.test')
        self.report = Report.objects.create(owner=self.owner, kind='Lost', title='Black bag', category='Bag', event_date=date.today(), contact='03001234567', answers={'brand': 'PRIVATE_SENTINEL_482'})
        self.draft = Draft.objects.create(owner=self.owner)
        found = Report.objects.create(owner=self.other, kind='Found', title='Black bag', category='Bag', event_date=date.today())
        self.match = Match.objects.create(lost=self.report, found=found, score=90)
        self.client.force_login(self.owner)

    def test_null_search_is_rejected_or_returns_results_without_500(self):
        self.client.raise_request_exception = False
        response = self.client.get(reverse('reports'), {'q': '\x00'})
        self.assertIn(response.status_code, (200, 400), f'Untrusted search must not crash; exception={response.exc_info}')

    def test_pagination_and_filter_inputs_do_not_crash(self):
        for value in ['', '0', '-1', '999999999999999999999999999999999', '1.5', 'NaN', '<script>alert(1)</script>', '9' * 5000]:
            with self.subTest(value=value[:30]):
                response = self.client.get(reverse('reports'), {'page': value, 'kind': value, 'status': value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context['page_obj']), [self.report])

    def test_csrf_enforced_for_workflow_mutations(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for url, data in [(reverse('draft', args=[self.draft.pk])+'?step=1', {'kind': 'Lost'}), (reverse('edit', args=[self.report.pk]), {}), (reverse('match', args=[self.match.pk]), {'action': 'reject'}), (reverse('qr-labels'), {'item_name':'Bag', 'contact_phone':'03001234567'})]:
            with self.subTest(url=url):
                self.assertEqual(client.post(url, data).status_code, 403)
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, 'Possible Match')

    def test_cross_owner_access_and_methods(self):
        self.client.force_login(self.other)
        for name, pk in [('report', self.report.pk), ('draft', self.draft.pk), ('draft-photo', self.draft.pk), ('report-photo', self.report.pk)]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name,args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('edit',args=[self.report.pk])).status_code, 404)
        self.client.force_login(self.owner)
        for name in ['edit', 'qr-label-reactivate', 'qr-label-deactivate']:
            self.assertEqual(self.client.get(reverse(name,args=[self.report.pk])).status_code, 405)

    def test_private_answers_hidden_from_match_and_management(self):
        self.assertNotContains(self.client.get(reverse('match',args=[self.match.pk])), 'PRIVATE_SENTINEL_482')
        self.owner.is_staff = True
        self.owner.save(update_fields=['is_staff'])
        self.assertNotContains(self.client.get(reverse('management')), 'PRIVATE_SENTINEL_482')

    def test_external_login_redirect_blocked(self):
        self.client.logout()
        response = self.client.post(reverse('login')+'?next=https://evil.example/', {'username': self.owner.email, 'password': 'Safe-pass-482!'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.url.startswith('https://evil.example'))
