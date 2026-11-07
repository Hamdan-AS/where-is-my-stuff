"""Dashboard, report history, report detail, and account-scoped visibility."""

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Event, Report
from core.services import transition
from tests.support import (
    AppTestCase,
    make_match,
    make_report,
    make_user,
    meeting,
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DashboardTests(AppTestCase):
    def test_a_brand_new_account_is_sent_to_create_a_report(self):
        self.login()
        self.assertRedirects(
            self.client.get(reverse("dashboard")), reverse("create"),
            fetch_redirect_response=False,
        )

    def test_a_saved_draft_is_resumed_before_an_empty_dashboard(self):
        from core.models import Draft

        draft = Draft.objects.create(owner=self.owner, data={"title": "Draft"})
        self.login()
        self.assertRedirects(
            self.client.get(reverse("dashboard")),
            reverse("draft", args=[draft.pk]),
            fetch_redirect_response=False,
        )

    def test_counts_and_sections_reflect_the_users_own_work(self):
        open_report = make_report(self.owner, title="Open backpack")
        make_report(self.owner, title="Returned keys", status="Returned")
        make_report(self.owner, title="Removed wallet", status="Removed")
        found = make_report(self.finder, "Found", title="Someone else's found item")
        make_match(open_report, found, score=92)

        self.login()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_count"], 2)
        self.assertEqual(response.context["open_count"], 1)
        self.assertEqual(response.context["returned_count"], 1)
        self.assertEqual(response.context["possible_count"], 1)
        self.assertContains(response, "Open backpack")
        self.assertContains(response, "Returned items")
        self.assertNotContains(response, "Removed wallet")

    def test_only_the_three_newest_open_reports_fit_the_active_card(self):
        for index in range(5):
            Report.objects.create(
                owner=self.owner, kind="Lost", title=f"Backpack {index}",
                category="Bag", description="Blue backpack", location="Library",
                location_detail="Entrance", event_date=timezone.localdate(),
                contact="03001234567", answers={},
            )
        self.login()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(len(response.context["reports"]), 3)
        self.assertContains(response, "Backpack 4")
        self.assertNotContains(response, "Backpack 0")

    def test_a_proposal_from_the_other_participant_is_the_hero_match(self):
        lost = make_report(self.owner, title="Lost backpack")
        found = make_report(self.finder, "Found", title="Found backpack")
        possible = make_match(lost, found, score=88)
        second_finder = make_user("second-finder@example.test")
        second_found = make_report(
            second_finder, "Found", title="Second found",
        )
        proposed = make_match(lost, second_found, score=91)
        transition(proposed.pk, second_finder, "propose", meeting())
        self.login()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["hero"].pk, proposed.pk)
        # The proposal reserves the lost report, so the remaining suggestion
        # for that report is intentionally hidden until the handover resolves.
        self.assertNotIn(possible, response.context["other_matches"])
        self.assertContains(response, "Respond to proposal")

    def test_dismissed_matches_never_reach_the_dashboard(self):
        lost = make_report(self.owner, title="Lost backpack")
        found = make_report(self.finder, "Found", title="Found backpack")
        match = make_match(lost, found, state="Rejected", rejected_by=self.owner)
        self.login()
        self.assertNotContains(
            self.client.get(reverse("dashboard")),
            reverse("match", args=[match.pk]),
        )

    def test_a_possible_match_is_hidden_when_either_report_is_reserved(self):
        lost = make_report(self.owner, title="Lost backpack", reserved=True)
        found = make_report(self.finder, "Found", title="Found backpack")
        make_match(lost, found)
        self.login()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["possible_count"], 0)
        self.assertIsNone(response.context["hero"])


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ReportHistoryTests(AppTestCase):
    def test_search_matches_title_or_location(self):
        by_title = make_report(self.owner, title="Silver keyring")
        by_location = make_report(self.owner, title="Umbrella", location="Saddar")
        make_report(self.owner, title="Laptop", location="Gulshan")
        self.login()

        for query, expected in (("keyring", by_title), ("saddar", by_location)):
            with self.subTest(query=query):
                response = self.client.get(reverse("reports"), {"q": query})
                self.assertIn(expected, list(response.context["page_obj"]))
                self.assertEqual(len(response.context["page_obj"]), 1)

        response = self.client.get(reverse("reports"), {"q": "nothing-matches"})
        self.assertEqual(len(response.context["page_obj"]), 0)
        self.assertContains(response, "No reports found")

    def test_kind_and_status_filters_can_be_combined(self):
        lost = make_report(self.owner, "Lost", title="Lost backpack")
        found = make_report(self.owner, "Found", title="Found backpack")
        returned = make_report(
            self.owner, "Lost", title="Returned backpack", status="Returned",
        )
        self.login()

        response = self.client.get(reverse("reports"), {"kind": "Lost", "status": "Open"})
        self.assertEqual(list(response.context["page_obj"]), [lost])
        response = self.client.get(reverse("reports"), {"kind": "Found"})
        self.assertEqual(list(response.context["page_obj"]), [found])
        response = self.client.get(reverse("reports"), {"status": "Returned"})
        self.assertEqual(list(response.context["page_obj"]), [returned])

    def test_invalid_filter_values_are_ignored(self):
        report = make_report(self.owner)
        self.login()
        response = self.client.get(reverse("reports"), {
            "kind": "Nonsense", "status": "Nonsense", "q": "backpack",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"]), [report])

    def test_history_is_paginated_ten_per_page_and_newest_first(self):
        reports = []
        for index in range(12):
            reports.append(Report.objects.create(
                owner=self.owner, kind="Lost", title=f"Backpack {index}",
                category="Bag", description="Blue backpack", location="Library",
                location_detail="Entrance", event_date=timezone.localdate(),
                contact="03001234567", answers={},
            ))
        self.login()
        first = self.client.get(reverse("reports"))
        second = self.client.get(reverse("reports"), {"page": 2})
        self.assertEqual(len(first.context["page_obj"]), 10)
        self.assertEqual(len(second.context["page_obj"]), 2)
        self.assertEqual(first.context["page_obj"][0], reports[-1])
        self.assertContains(first, "Page 1 of 2")

    def test_a_non_numeric_page_falls_back_to_the_first_page(self):
        for index in range(11):
            make_report(self.owner, title=f"Backpack {index}")
        self.login()
        response = self.client.get(reverse("reports"), {"page": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_out_of_range_pages_fall_back_to_the_last_page(self):
        for index in range(11):
            make_report(self.owner, title=f"Backpack {index}")
        self.login()
        for value in ("0", "-2", "999999999999999999999"):
            with self.subTest(value=value):
                response = self.client.get(reverse("reports"), {"page": value})
                self.assertEqual(response.status_code, 200)
                page = response.context["page_obj"]
                self.assertEqual(page.number, page.paginator.num_pages)

    def test_invisible_or_control_characters_in_the_search_are_rejected(self):
        self.login()
        for value in ("backpack\u200b", "\x00", "wallet\u202e"):
            with self.subTest(value=repr(value)):
                response = self.client.get(reverse("reports"), {"q": value})
                self.assertEqual(response.status_code, 400)
                self.assertContains(
                    response,
                    "Remove special or invisible characters from your search.",
                    status_code=400,
                )

    def test_removed_reports_never_appear_in_history(self):
        make_report(self.owner, title="Visible backpack")
        make_report(self.owner, title="Removed backpack", status="Removed")
        self.login()
        response = self.client.get(reverse("reports"))
        self.assertContains(response, "Visible backpack")
        self.assertNotContains(response, "Removed backpack")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ReportDetailTests(AppTestCase):
    def test_only_the_owner_can_open_a_report(self):
        report = make_report(self.finder)
        self.login(self.owner)
        self.assertEqual(
            self.client.get(reverse("report", args=[report.pk])).status_code, 404,
        )

    def test_detail_shows_the_report_its_matches_and_its_activity(self):
        report = make_report(self.owner, title="Blue backpack")
        found = make_report(self.finder, "Found", title="Found backpack")
        match = make_match(report, found, score=91)
        Event.objects.create(report=report, actor=self.owner, text="Report created")
        Event.objects.create(report=report, actor=self.finder, text="Handover Proposed")
        self.login()
        response = self.client.get(reverse("report", args=[report.pk]))
        self.assertContains(response, report.display_id)
        self.assertContains(response, "Blue backpack")
        self.assertContains(response, "Matches for this report")
        self.assertContains(response, "91/100")
        self.assertContains(response, "Report created")
        self.assertContains(response, "Handover Proposed")
        self.assertContains(response, reverse("match", args=[match.pk]))

    def test_dismissed_matches_are_omitted_from_report_detail(self):
        report = make_report(self.owner)
        rejected = make_match(
            report, make_report(self.finder, "Found"),
            state="Rejected", rejected_by=self.owner,
        )
        self.login()
        response = self.client.get(reverse("report", args=[report.pk]))
        self.assertNotContains(response, reverse("match", args=[rejected.pk]))

    def test_display_ids_are_readable_and_kind_specific(self):
        lost = make_report(self.owner, "Lost")
        found = make_report(self.owner, "Found")
        self.assertEqual(lost.display_id, f"LFD-{lost.pk:03d}")
        self.assertEqual(found.display_id, f"FND-{found.pk:03d}")

    def test_qr_box_only_appears_for_an_owners_open_lost_report(self):
        lost = make_report(self.owner, "Lost")
        found = make_report(self.owner, "Found")
        self.login()
        lost_page = self.client.get(reverse("report", args=[lost.pk]))
        self.assertContains(lost_page, "Share this code with the finder")
        self.assertContains(lost_page, reverse("report-qr", args=[lost.public_id]))
        found_page = self.client.get(reverse("report", args=[found.pk]))
        self.assertNotContains(found_page, "Share this code with the finder")

    def test_a_reserved_report_explains_why_editing_is_locked(self):
        report = make_report(self.owner, reserved=True)
        self.login()
        response = self.client.get(reverse("report", args=[report.pk]))
        self.assertContains(response, "Editing is locked while a handover is in progress.")
        self.assertNotContains(response, "Edit report</button>")
