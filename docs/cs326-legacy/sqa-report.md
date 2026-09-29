# Software Quality Assurance

Where Is My Stuff? GPS-enabled Lost and Found System. CS-326 evidence for SQA approaches, measurements and metrics, and the measurement process.

This report reports only measured numbers. Figures marked provisional are computed from the current codebase on 12 Sep 2026.

## 1. SQA plan

- Standard: PHP 8.1 with `declare(strict_types=1)` on every file; prepared statements everywhere; output always escaped through `e()`; dates canonicalised to Y-m-d.
- Quality attributes (srs.md section 5): security, privacy, usability, reliability, maintainability, efficiency, portability.
- Verification gates: `php -l` syntax gate at every change; deterministic scoring test; isolated HTTP workflow test; manual browser pass before demo.
- Defect management: defect log in verification-and-validation.md; change control in scope-freeze.md and maintenance-record.md.

## 2. SQA approaches

| Approach | Application | Evidence |
|---|---|---|
| Standards | strict_types, escaping, prepared statements, POST-only mutations | codebase-wide, listed above |
| Defect prevention | validation concentrated in functions.php so rule changes happen once | validate_report, validate_public_description |
| Audit | the V&V inspection checklist is the audit instrument | verification-and-validation.md section 6 |
| Post-mortem | GPS change retrofit recorded after the fact | verification-and-validation.md defects D1/D2 |

## 3. Software metrics (measured 12 Sep 2026)

### 3.1 Size-oriented metrics

| Module | Files | LOC | Functions |
|---|---|---|---|
| Configuration and bootstrap | config.php, router.php, setup-check.php | 88 | 1 |
| Helpers and validation | functions.php | 325 | 30 |
| Matching | matching.php | 83 | 5 |
| Workflow | workflow.php | 137 | 6 |
| Page controllers (presentation) | index, report_form, report, reports, match, handover, moderation, admin, auth, logout | 616 | 2 |
| Application total | 16 files | 1249 | 44 |
| Tests | tests/matching_test.php | 68 | 2 |

### 3.2 Defect metrics (provisional)

| Metric | Value | Basis |
|---|---|---|
| Defects found (open) | 2 | D1, D2 in verification-and-validation.md |
| Defect density (app) | 2 / 1.249 KLOC = 1.6 defects per KLOC | provisional, open defects only |
| Test assertions written | 25+ (matching_test.php) | counted in tests/matching_test.php |
| Vocabulary | 4 modules of equivalent responsibility | matches srs.md traceability matrix |

These figures are provisional because the two test suites are not yet passing (D1, D2).

## 4. Measurement process

1. Define: each metric maps to a quality attribute (LOC for maintainability, defect density for reliability, function count for complexity scoping).
2. Collect: source measurement via `php -l` and a static count of LOC and `function` declarations (recorded in sqa-report.md section 3).
3. Analyse: D1/D2 came out of running the suites, which is why test execution is the primary monitor.
4. Report: this file plus verification-and-validation.md, fed back into rmmm.md risk R8.

## 5. Open items

- Formal LOC/FP/COCOMO figures for the final report are drafted in cost-estimation.md.
- A structured defect-tracking log (severity, fix time, regression) should replace the flat defect list once the test update lands.
- Performance metric sampling (response time) is pending (verification-and-validation.md section 7).