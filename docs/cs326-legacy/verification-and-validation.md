# Verification and Validation

Where Is My Stuff? GPS-enabled Lost and Found System. CS-326 evidence for testing, debugging, inspection, and types of testing applied.

This file records only results that were actually executed. Everything still pending is marked pending. Reference: matching-architecture.md V&V list, CS-326-SE-Project-Plan.md test cases.

## 1. Verification strategy (V-model)

Each requirements tier has a corresponding check level:

| Requirements tier | Level | Instrument |
|---|---|---|
| FR-01 accounts | Unit + integration | tests/integration_test.py register/login/logout |
| FR-02..FR-04 reports + GPS | Unit + integration | validate_report unit checks, HTTP report save |
| FR-05..FR-07 matching | Unit + integration | tests/matching_test.php, stored-total assertions |
| FR-08..FR-09 handover | Integration + system | integration_test.py handover scenarios |
| FR-10 staff | Integration | integration_test.py role and management checks |
| NFR security/privacy | Security + privacy tests | integration_test.py 404/403 and no-private-value checks |

## 2. Types of testing

| Type | Coverage | Status on 12 Sep 2026 |
|---|---|---|
| Unit (component) | score_reports, haversine_score, description_score, validate_report, validate_questionnaire_answers | tests/matching_test.php written; FAILS (see defect D1) |
| Integration | Real HTTP routes against isolated MySQL | tests/integration_test.py written; requires isolated socket, not part of normal runs |
| System (black-box) | Demo journey: register, report, match, handover, return | Pending browser pass (scope-freeze item 6) |
| Acceptance | Scenario in CS-326-SE-Project-Plan.md | Pending stakeholder demo |
| Regression | Re-run after GPS change | Blocked by D1; re-run needed after test update |
| Security | CSRF, ownership 404/403, private-value absence | integration_test.py assertions; pending re-run |
| Performance | Response-time sampling | No formal baseline yet |

## 3. Executed results (12 Sep 2026, this session)

### 3.1 Syntax verification (executed, all pass)

`php -l` ran on the 16 application files. Result: no syntax errors in any file (config.php, router.php, functions.php, matching.php, workflow.php, setup-check.php, handover.php, match.php, reports.php, moderation.php, admin.php, auth.php, index.php, report.php, report_form.php, claims.php).

### 3.2 Scoring unit test (executed, FAILS)

Command: `php tests/matching_test.php`. Output: `FAIL: identical eligible reports score 100`, exit code 1.

Root cause: the test fixture carries no lat/lng, so `score_reports()` gives the location factor 0 (category 20 + location 0 + date 15 + description 15 + private 30 = 80). The assertion was written for the frozen binary-location scoring where an equal NED location is worth 20. This is defect D1.

### 3.3 Integration test (not executed here)

`tests/integration_test.py` refuses to run unless `NED_TEST_MODE=1` and `NED_DB_SOCKET` points under `/tmp/ned-workflow-test.*`. It answers its own PHP server, then drives SQL through tests/db_fixture.php. It also asserts a stored total of 100 and never posts lat/lng, which current `validate_report()` requires. Both must be reconciled with the GPS scoring before it is a valid run (defect D1).

## 4. Defect log

| ID | Date found | Description | Severity | Status |
|---|---|---|---|---|
| D1 | 12 Sep 2026 | tests/matching_test.php expects 100 for identical reports and integration_test.py expects stored total 100 without lat/lng; both were written for frozen binary-location scoring | High | Open; blocked by the deferred "update scoring tests" task in TODO.md |
| D2 | 12 Sep 2026 | integration_test.py posts no lat/lng, so it can no longer save any report | High | Open, same root cause as D1 |

Both defects share one fix: port the two suites to haversine scoring and lat/lng fixtures. This is the pending task in TODO.md ("Pass scoring and validation tests") and scope-freeze.md resume order item 4.

## 5. Debugging record

| Debug session | Method | Finding |
|---|---|---|
| GPS branch behaviour | Ran matching_test.php against GPS matching.php | First assertion failed; isolated the cause to location scoring by recomputing the factor totals |
| Syntax gate | `php -l` over all files during the GPS change | No parse errors introduced by the lat/lng refactor |
| Manual form flow | Browser walkthrough per demo journey | Browser verification still pending (scope-freeze item 6) |

## 6. Inspections

No formal code inspection has been recorded (SE-checklist section 8, open item). The review checklist to use at the submission inspection, mapped to risks:

- [ ] Every mutation is POST + CSRF (`require_post`) for FR-03, NFR security
- [ ] Ownership checks on report, match, handover, and management routes return 404 (R3)
- [ ] No report_answers value rendered anywhere; only counts used (R2, FR-07)
- [ ] Masked-suffix validation rejects full identifiers (functions.php, matching-architecture.md)
- [ ] `write_transaction()` wraps every report/handover mutation (R9)
- [ ] haversine_score() band boundaries match scope-freeze.md exactly (FR-05s)

## 7. Pending verification items before submission

- [ ] Update both test suites for haversine scoring (fix D1, D2) and get `matching_test.php` passing
- [ ] Run integration_test.py against an isolated MySQL instance and record output
- [ ] Browser verification of the demo journey and record results
- [ ] Regression re-run of the frozen scenarios after the GPS change
- [ ] Performance sample of the score/match pages