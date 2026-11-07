"""QA reproductions; synchronization pauses requests without changing their data."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, current_thread
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, connections
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from core.models import Draft, Report, User


@skipUnless(connection.vendor == "postgresql", "SQLite locks the whole table during these races")
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class StateRaceTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='race@example.com', email='race@example.com')
        self.clients = [Client(), Client()]
        for client in self.clients:
            client.force_login(self.user)
        self.data = dict(kind='Lost', title='Blue backpack', category='Bag',
            description='Blue fabric backpack with two front pockets',
            location='Central Library', location_detail='Beside entrance',
            event_date=timezone.localdate().isoformat(), contact='03000000000',
            lat='24.9340', lng='67.1120', answers={'colour':'Blue', 'kind':'Backpack',
            'material':'Fabric', 'pockets':'2', 'mark':'None'})

    def worker(self, action):
        connections.close_all()
        try:
            return action()
        finally:
            connections.close_all()

    def test_late_step_save_cannot_resurrect_published_draft(self):
        draft = Draft.objects.create(owner=self.user, data=self.data)
        url = reverse('draft', args=[draft.pk])
        ready, release = Event(), Event()
        original_save = Draft.save
        def delayed_save(instance, *args, **kwargs):
            if current_thread().name.startswith('late-step'):
                ready.set()
                if not release.wait(15):
                    raise AssertionError('publish did not complete')
            return original_save(instance, *args, **kwargs)
        with patch.object(Draft, 'save', delayed_save), ThreadPoolExecutor(max_workers=1, thread_name_prefix='late-step') as pool:
            pending = pool.submit(self.worker, lambda: self.clients[0].post(url+'?step=2',
                {'description': 'Blue fabric backpack with two front pockets', 'contact':'03000000000'}))
            try:
                self.assertTrue(ready.wait(15), 'step save never reached')
                published = self.clients[1].post(url+'?step=5')
                self.assertEqual(published.status_code, 302)
                self.assertEqual(Report.objects.count(), 1)
            finally:
                release.set()
            self.assertEqual(pending.result().status_code, 302)
        replay = self.clients[1].post(url+'?step=5')
        print('late-save replay status:', replay.status_code, 'report count:', Report.objects.count())
        self.assertEqual(Report.objects.count(), 1, 'late step save resurrected draft and allowed duplicate publication')

    def test_concurrent_new_requests_keep_one_active_draft(self):
        barrier = Barrier(2)
        def first_visit(client):
            barrier.wait(15)
            return client.get(reverse('create'))
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.worker, lambda c=c: first_visit(c)) for c in self.clients]
            statuses = [future.result().status_code for future in futures]
        print('concurrent create statuses:', statuses, 'draft count:', Draft.objects.count())
        self.assertEqual(Draft.objects.filter(owner=self.user, report__isnull=True).count(), 1)
        self.assertTrue(all(status in (200, 302) for status in statuses))
        other = User.objects.create_user(username='other@example.com', email='other@example.com')
        report = Report.objects.create(owner=other, **self.data)
        self.clients[0].raise_request_exception = False
        scanned = self.clients[0].get(reverse('report-found', args=[report.public_id]))
        print('subsequent report QR scan status:', scanned.status_code)
        self.assertLess(scanned.status_code, 500, 'duplicate drafts make report QR scan crash')

    def test_new_report_and_qr_scan_share_one_active_draft(self):
        other = User.objects.create_user(username='scan-owner@example.com', email='scan-owner@example.com')
        report = Report.objects.create(owner=other, **self.data)
        start = Barrier(2)
        def visit(client, url):
            start.wait(15)
            return client.get(url)
        urls = [reverse('create'), reverse('report-found', args=[report.public_id])]
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(self.worker, lambda c=c, url=url: visit(c, url))
                       for c, url in zip(self.clients, urls)]
            self.assertTrue(all(p.result().status_code in (200, 302) for p in pending))
        draft = Draft.objects.get(owner=self.user, report__isnull=True)
        self.assertEqual(draft.data['kind'], 'Found')
        self.assertEqual(draft.data['title'], report.title)

    def test_concurrent_edits_share_one_report_draft(self):
        report = Report.objects.create(owner=self.user, **self.data)
        start = Barrier(2)
        def edit(client):
            start.wait(15)
            return client.post(reverse('edit', args=[report.pk]))
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(self.worker, lambda c=c: edit(c)) for c in self.clients]
            responses = [p.result() for p in pending]
        self.assertTrue(all(response.status_code == 302 for response in responses))
        self.assertEqual(Draft.objects.filter(owner=self.user, report=report).count(), 1)
        self.assertEqual(responses[0].url, responses[1].url)
