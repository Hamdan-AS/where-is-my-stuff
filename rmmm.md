# Risk Management and RMMM/RSKM

Where Is My Stuff? GPS-enabled Lost and Found System. CS-326 evidence for the risk management process.

Reference: architecture.md risk record and scope-freeze.md risk rules. Risk process phases applied: identification, analysis, planning, monitoring (loop restarts after each monitoring pass).

## 1. Risk register

Columns: ID, risk, probability (P), impact (I), exposure, plan (RMMM), contingency, monitoring status.

| ID | Risk | P | I | Exposure | Response plan (R/E) / Mitigation (M) | Contingency | Monitoring |
|---|---|---|---|---|---|---|---|
| R1 | False positive match suggests the wrong owner | High | High | High | M: reproducible deterministic score with factor breakdown; threshold 70 + 2 private agreements; score labelled "suggestion, not proof" in UI | Reject option removes pair permanently; Moderator can close both reports | match.php banner text and state machine verified in integration test |
| R2 | Private answers leak into dashboards or staff pages | Medium | High | High | E: never RENDER answers, only counts; masked suffixes; type change from 9 private outputs audited | Code inspection of report_answers reads | integration_test.py privacy assertions (deferred until test update) |
| R3 | Unauthorized change to another user's report | Medium | High | High | M: ownership checks on every report/match route return 404; CSRF on every POST | GET requests rejected with 405; ownership review per route | integration_test.py 404/403 assertions |
| R4 | Stale match suggestions after a report edit | Medium | Medium | Medium | M: edit deletes stale Possible Match rows inside the save transaction; rejected pairs stay rejected | Re-save report to refresh suggestions | integration_test.py edit scenario |
| R5 | Database setup failure on a fresh machine | Medium | Medium | Medium | M: database-reset.sql + database-user.sql + read-only setup-check.php; env-var DB overrides | setup-check exits 1 and lists missing columns/accounts | setup-check.php run after reset |
| R6 | Invalid GPS coordinates entered | High | High | High | M: validate_report() requires lat/lng in range, rejects blanks | Form keeps draft of public fields; user re-enters answers | matching_test.php + manual form test |
| R7 | Match score breaks when location data is missing | Medium | Medium | Medium | M: missing lat/lng scores 0, never errors | Reports always require coordinates in current code | haversine_score() unit tests |
| R8 | Scoring tests drift from the shipped algorithm | Confirmed | High | High | M: scope increment gates test updates (retrospective in project-management.md) | Fix tests/matching_test.php for haversine before submission | tracked as defect in verification-and-validation.md |
| R9 | Double booking one report into two handovers | Medium | High | High | M: report_has_locked_match guard + GET_LOCK serialised writes | Second proposal rejected with clear message | integration_test.py concurrency scenario |
| R10 | Scope creep (maps, images, messaging) | High | Medium | Medium | M: scope-freeze.md records what is deferred and why; changes need reason, requirements impact, effort, test impact | Item absent from router.php and from FR table | scope-freeze change control |

Legend: E = avoid, M = mitigate, T = transfer, A = accept.

## 2. RMMM summary

- Analysis: R2 and R3 are privacy/security risks with high exposure; both are mitigated in code and now need the deferred tests to be re-run to prove it.
- Planning: R1, R2, R3, R4 mitigation is implemented; R6 and R7 mitigation is implemented in validate_report() and haversine_score().
- Monitoring: R8 is the confirmed active risk. It was found during the 12 Sep 2026 checkpoint and is tracked until the test suites are updated.

## 3. Monitoring process

- Each increment ends with a scope-freeze checkpoint that re-opens this register.
- Stale rows between increments are removed.
- The checklist in verification-and-validation.md acts as the monitoring instrument for R2, R3, and R9.

## 4. Residue risk (accepted)

A Fully evaluated score of 70 does not prove ownership; that residual uncertainty is inherent to a similarity-based system and is communicated to users in the match page banner.