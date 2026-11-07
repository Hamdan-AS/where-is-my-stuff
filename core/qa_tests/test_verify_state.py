from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, connections
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Draft, Report, User


@skipUnless(connection.vendor == "postgresql", "SQLite locks the whole table during these races")
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class IndependentStateVerification(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='verify@example.test', email='verify@example.test')
        self.clients = [Client(), Client()]
        for client in self.clients:
            client.force_login(self.user)

    @staticmethod
    def request(client, method, *args, **kwargs):
        connections.close_all()
        try:
            return getattr(client, method)(*args, **kwargs)
        finally:
            connections.close_all()

    def test_first_visit_race_reuses_one_draft_and_keeps_qr_scan_working(self):
        rendezvous = Barrier(2)
        def first_visit(client):
            rendezvous.wait(timeout=15)
            return self.request(client, 'get', reverse('create'))
        with ThreadPoolExecutor(2) as pool:
            results = [pool.submit(first_visit, c) for c in self.clients]
            statuses = [f.result(timeout=30).status_code for f in results]
        count = Draft.objects.filter(owner=self.user, report__isnull=True).count()
        print('independent GET interleave:', statuses, 'active drafts:', count)
        self.assertEqual(count, 1)
        self.assertTrue(all(status in (200, 302) for status in statuses))

        owner = User.objects.create_user(username='qr-owner@example.test', email='qr-owner@example.test')
        report = Report.objects.create(owner=owner, kind='Lost', title='Blue bag', category='Bag',
            description='Blue bag', location='Library', location_detail='entrance',
            contact='03000000000', event_date=timezone.localdate(), lat=24.9, lng=67.1)
        self.clients[0].raise_request_exception = False
        response = self.clients[0].get(reverse('report-found', args=[report.public_id]))
        print('QR scan after duplicate drafts:', response.status_code)
        self.assertLess(response.status_code, 500)

    def test_step_post_overlapping_publish_does_not_restore_draft(self):
        payload = {'kind': 'Lost', 'title': 'Blue backpack', 'category': 'Bag',
            'description': 'Blue fabric backpack with two front pockets',
            'location': 'Central Library', 'location_detail': 'Beside entrance',
            'event_date': timezone.localdate().isoformat(), 'contact': '03000000000',
            'lat': '24.9340', 'lng': '67.1120',
            'answers': {'colour': 'Blue', 'kind': 'Backpack', 'material': 'Fabric', 'pockets': '2', 'mark': 'None'}}
        draft = Draft.objects.create(owner=self.user, data=payload)
        step_started, publish_done = Event(), Event()
        save = Draft.save

        def pause_after_step_has_loaded(instance, *args, **kwargs):
            if instance.pk == draft.pk and not publish_done.is_set():
                step_started.set()
                if not publish_done.wait(15):
                    raise AssertionError('publish request did not finish')
            return save(instance, *args, **kwargs)

        with patch.object(Draft, 'save', pause_after_step_has_loaded), ThreadPoolExecutor(1) as pool:
            delayed = pool.submit(self.request, self.clients[0], 'post',
                reverse('draft', args=[draft.pk]) + '?step=2',
                {'description': payload['description'], 'contact': payload['contact']})
            self.assertTrue(step_started.wait(15), 'step request did not reach save point')
            published = self.clients[1].post(reverse('draft', args=[draft.pk]) + '?step=5')
            publish_done.set()
            late_response = delayed.result(timeout=30)

        live_drafts = Draft.objects.filter(pk=draft.pk).count()
        report_count = Report.objects.filter(owner=self.user).count()
        replay = self.clients[1].post(reverse('draft', args=[draft.pk]) + '?step=5')
        print('overlap outcomes:', published.status_code, late_response.status_code,
              'draft remains:', live_drafts, 'reports:', report_count, 'replay:', replay.status_code)
        self.assertEqual(live_drafts, 0, 'late step save recreated the published draft')
        self.assertEqual(Report.objects.filter(owner=self.user).count(), 1)
