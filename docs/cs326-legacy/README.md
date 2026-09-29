# CS-326 documentation (legacy)

These files are kept for the documentation filing. They are **not** a description of the
code in this repository.

They were written against a PHP 8.1 / MySQL implementation that was removed on 26-09-2026.
The Django application in the project root is the only implementation. The pre-deletion
state is recoverable from git commit `54fa6fc`.

## What is stale in here

- `sqa-report.md` still specifies PHP 8.1, `e()` output escaping, and a `php -l` syntax gate.
- `design-record.md` maps modules to `matching.php`, `workflow.php`, `functions.php`, and
  `router.php`.
- `analysis-models.md` names `database.sql`, `workflow.php`, `matching.php`, and
  `match.php` as its source of truth.
- `verification-and-validation.md` records `php -l` results and `matching_test.php` runs.
- `SE-checklist.md` line 23 describes "the small PHP/MySQL scope".
- `scope-freeze.md` points at `/home/elite/sandbox/where-is-my-stuff-gps/`.

The diagrams, the requirement IDs, the risk register, and the COCOMO estimates remain
usable as coursework artifacts. The module names, file names, LOC counts, and stack
claims do not.

## Known-broken citations

`srs.md` line 65 and `design-record.md` line 78 cite `ui-wireframes-redesign.png` as the
UI reference. That image was deleted during the 29-09-2026 cleanup. `scope-freeze.md`
line 122 also cites `ui-wireframes-redesign.backup.png`, which no longer exists in the
repository.

## If you are re-measuring the numbers

`cost-estimation.md`, `sqa-report.md` section 3, and `SE-checklist.md` report 1,249 LOC
and 44 functions from the PHP codebase. The Django application is roughly 2,155 lines
across `core/`, `config/`, and `manage.py`, excluding tests. Re-measure before reusing any
figure.

## Current documents

For the live application, read `../../README.md`, `../../AGENTS.md`,
`../../TODO-INCREMENTAL.md`, `../../matching-architecture.md`,
`../../report-structure.md`, and `../../report-wizard-flow.md`.
