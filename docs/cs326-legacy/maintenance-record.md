# Software Maintenance Record

Where Is My Stuff? GPS-enabled Lost and Found System. CS-326 evidence for the types of software maintenance and the maintenance process model.

Reference: scope-freeze.md saved coding progress; verification-and-validation.md defect log.

## 1. Maintenance process model

The process follows the five IEEE 1219 stages adapted for a student project:

```text
Identification -> Plan -> Implement and verify -> Regression check -> Record and review
```

- Identification comes from an observation (bug report, scope change, or instructor feedback).
- Planning is recorded in scope-freeze.md and TODO.md.
- Implementation is recorded in the file-change table in scope-freeze.md.
- Regression is the V&V task in verification-and-validation.md.
- Review is this document and the checkpoint in scope-freeze.md.

## 2. Actual change log

| Change ID | Date | Type | Trigger | Description | Files changed | Regression status |
|---|---|---|---|---|---|---|
| MC-1 | 8-12 Sep 2026 | Adaptive | Scope expansion to Karachi-wide | GPS coordinates added to reports; haversine distance scoring replaces binary NED-location match; handover location generalised from ENUM to free text | database.sql, functions.php, matching.php, workflow.php, match.php, index.php, reports.php, report_form.php | Partial: matching_test.php now fails (D1, verification-and-validation.md) |
| MC-2 | 12 Sep 2026 | Corrective | D1 discovered during V&V run | Pending: update tests/matching_test.php for haversine scoring | tests/matching_test.php (not yet changed) | Open |
| MC-3 | 12 Sep 2026 | Corrective | D2: integration_test.py cannot save reports | Pending: add lat/lng fields to the HTTP posting helper | tests/integration_test.py (not yet changed) | Open |

## 3. Types classification

| Type | Definition in this project | Change |
|---|---|---|
| Adaptive | Modifying the system to work in a changed environment or platform | MC-1: GPS expansion, new coordinates and distance scoring |
| Corrective | Fixing a defect discovered after release | MC-2, MC-3: test suites written for the frozen baseline now fail against the GPS code |
| Perfective | Improving performance, maintainability, or usability without a bug or environment change | None recorded yet. The deferred Leaflet.js map (scope-freeze item 5) would fall here if implemented |
| Preventive | Reducing future risk of problems | Strict `declare(strict_types=1)` and validation concentration in `validate_report()` are preventive practices applied from the start; no separate change was needed |

## 4. Impact analysis (MC-1)

| Layer | Affected | Reason |
|---|---|---|
| Database schema | reports.lat, reports.lng added; handovers.location widened to VARCHAR(255) | New GPS data requirement |
| Validation | validate_report() adds lat/lng validation | FR-02b |
| Scoring | haversine_score() replaces exact match; location_score output unchanged in max (20 points) | FR-05s |
| Presentation | report_form.php lat/lng text inputs replace NED dropdown; match.php accepts free-form handover | Usability update |
| Regression risk | Both test suites expect the old scoring | Recorded as D1, D2 |

## 5. Regression evidence

- Syntax: `php -l` on all 16 application files passes after the GPS change (verification-and-validation.md section 3.1).
- Logic: `php tests/matching_test.php` fails immediately. The failure is confined to the location factor in the scoring assertion.
- The regression gap is the highest-priority open item before submission (rmmm.md R8, project-management.md retrospective).