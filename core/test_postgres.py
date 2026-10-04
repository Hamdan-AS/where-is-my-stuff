"""Real transaction races: skipped on SQLite, exercised on PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless

from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from .models import Draft, Match, Report, User
from .services import publish, transition


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL transaction locks")
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PostgresConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner@example.com", email="owner@example.com")
        self.finder = User.objects.create_user(username="finder@example.com", email="finder@example.com")
        self.data = dict(title="Blue backpack", category="Bag", description="Blue fabric backpack with two front pockets", location="Central Library", location_detail="Beside entrance", event_date=timezone.localdate(), contact="03000000000", lat="24.9340", lng="67.1120", answers={"colour":"Blue", "kind":"Backpack", "material":"Fabric", "pockets":"2", "mark":"None"})

    def race(self, actions):
        start = Barrier(len(actions))
        def run(action):
            connections.close_all()
            try:
                start.wait(timeout=10)
                action()
                return "ok"
            except ValidationError:
                return "blocked"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as workers:
            return list(workers.map(run, actions))

    def test_competing_handovers_reserve_only_one_pair(self):
        lost = Report.objects.create(owner=self.owner, kind="Lost", **self.data)
        found = [Report.objects.create(owner=self.finder, kind="Found", **self.data) for _ in range(2)]
        matches = [Match.objects.create(lost=lost, found=item, score=100) for item in found]
        meeting = {"meeting_place":"Library entrance", "meeting_at":timezone.now() + timedelta(hours=1)}
        actions = [lambda match=match: transition(match.pk, self.owner, "propose", meeting) for match in matches]
        self.assertCountEqual(self.race(actions), ["ok", "blocked"])
        self.assertEqual(Match.objects.filter(state="Handover Proposed").count(), 1)
        self.assertEqual(Report.objects.filter(reserved=True).count(), 2)

    def test_duplicate_submission_publishes_only_once(self):
        draft = Draft.objects.create(owner=self.owner, data={**self.data, "kind":"Lost", "event_date":self.data["event_date"].isoformat()})
        self.assertCountEqual(self.race([lambda: publish(draft, self.owner), lambda: publish(draft, self.owner)]), ["ok", "blocked"])
        self.assertEqual(Report.objects.count(), 1)

    def test_simultaneous_opposite_reports_create_one_match(self):
        drafts = [Draft.objects.create(owner=user, data={**self.data, "kind":kind, "event_date":self.data["event_date"].isoformat()}) for user, kind in [(self.owner,"Lost"),(self.finder,"Found")]]
        actions = [lambda draft=draft: publish(draft, draft.owner) for draft in drafts]
        self.assertEqual(self.race(actions), ["ok", "ok"])
        self.assertEqual(Match.objects.count(), 1)
