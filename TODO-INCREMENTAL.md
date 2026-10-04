# Where Is My Stuff? incremental task tracker

This is the single authoritative project tracker.

Stack: Django 5.2, PostgreSQL (SQLite fallback), server-rendered templates. Updated: 04-10-2026.

## Increment 1: core foundation

Status: complete.

- [x] Django project, settings, migrations, SQLite database
- [x] Custom user model with email login, registration, logout, sessions, and CSRF
- [x] Five-step report wizard (Type, Details, Location, Matching, Review) with account-owned server drafts
- [x] Lost and found fields with category-specific private questions
- [x] Privacy validation for public descriptions and private matching answers
- [x] Matching engine with eligibility rules, bounded scoring, and duplicate-pair protection
- [x] Handover workflow: propose, accept, reject, restore, and returned
- [x] Reservations, competing-match protection, contact release, and edit locks
- [x] Staff moderation with audited close and soft removal
- [x] Responsive styling, mobile sidebar menu, local fonts, and authentication screens
- [x] Human-readable report IDs such as LFD-001 and FND-002
- [x] Unit and browser coverage for the core workflow

## Increment 2: dashboard and navigation

Status: complete.

- [x] New users go directly to the report form after registration or first login
- [x] First report screen asks "What happened to your item?" and starts with Lost or Found
- [x] Users with no reports see Create report instead of an empty dashboard
- [x] Dashboard is an action page for open reports, drafts, possible matches, and handovers
- [x] Dashboard shows at most three current open reports, newest first, with reserved reports prioritized
- [x] Possible matches appear on the dashboard as actions to review
- [x] Rejected and completed matches are excluded from the active dashboard list
- [x] Counts distinguish open reports, matches to review, handovers, and returned reports
- [x] My reports appears after the user has more than one report
- [x] My reports history has search, type/status filters, and pagination
- [x] Report detail shows related non-rejected matches
- [x] New submissions return to the dashboard and identify possible matches when found
- [x] Removed the duplicate Possible matches sidebar destination
- [x] Dashboard cards, filters, report rows, and action panels are responsive
- [x] Owners can create, print, deactivate, and reactivate six-month QR item labels; QR tokens are random and SHA-256 hashed in the database
- [x] Active item QR pages show the owner's call details and explain that owner/finder arrange the return themselves; OTP/transfer verification is out of scope
- [x] Reports accept optional validated photos (5 MiB, 24-megapixel cap), resize the full image without cropping, strip metadata, preview before publish, and limit access to the owner and match participant

## QR scan open issues (found by adversarial testing, 13-09-2026)

Status: complete. All four surfaced in the scan-to-claim flow and are fixed with regression tests.

- [x] QR self-scan: an owner scanning their own report is seeded a self-Found draft. Guarded on `report.owner_id == request.user.pk`; the owner now gets an info notice and is redirected to their report.
- [x] QR box renders on Found-kind reports too (`templates/report.html`), and scanning a Found report seeds a Found-from-Found draft that doubles match noise. The box now renders only for Lost reports.
- [x] Stale competing match: after a handover is proposed, unclaimed `Possible Match` rows for the reserved report stay actionable on the dashboard and error on propose. They are now hidden from dashboards and counts while the report is reserved (parked, not destroyed), and become usable again if the handover is rejected.
- [x] Scan-mix: scanning merges public fields into an in-progress draft, flips kind to Found, but keeps previously typed Lost description/contact/answers which get published as Found attributes. Scanning now clears description, location detail, contact, and answers on merge.

## Increment 3: useful follow-up features

Status: pending.

- [ ] Password reset with development email backend
- [ ] Profile page for name, email, and password changes
- [ ] Notifications for new matches and handover state changes
- [ ] Pagination for management records
- [ ] Permanent QR-label deletion for active, expired, and deactivated labels
  - Require explicit confirmation and explain that an active printed code will stop working immediately; keep Deactivate as the reversible option.
  - Use an authenticated, owner-scoped POST action; remove both the label record and its private QR image so the public scan URL returns 404.
  - Cover confirmation cancel, non-owner and non-POST requests, storage cleanup, and the post-delete scan result in tests.
- [ ] Tests for password reset, profile, notifications, and management pagination

## V2 QA follow-up (04-10-2026)

Status: complete. All 147 tests pass; regression results are recorded in Verification below.
The original findings and resolution are in `report-qa/QA-REPORT-2026-10-04.md`.

- [x] Align accepted place length with the report database column (100 characters)
- [x] Allow email login usernames up to 254 characters; migration 0006 applied locally
- [x] Serialize draft acquisition per owner across new reports, QR scans, and report edits
- [x] Prevent late wizard saves from recreating published or discarded drafts
- [x] Decode images during validation so truncated JPEG uploads become form errors
- [x] Reject invalid search controls before PostgreSQL text lookups
- [x] Return 404 for missing private report, draft, and QR image files
- [x] Validate management report IDs before database lookup
- [x] Replace the obsolete login artwork assertion with current UI checks
- [x] Strengthen concurrency tests to require one draft, including simultaneous QR/new-report and edit requests

## Increment 4: deployment and security

Status: pending. Production settings are prepared locally; deployment and production verification remain incomplete.

- [x] Logging, environment-based secrets, and separate production settings (`config.production`)
- [x] Secure cookies, HSTS, content-type, frame, and host configuration in production settings
- [ ] Login throttling or rate limiting
- [ ] Static collection and production ASGI/WSGI deployment configuration
- [x] Local PostgreSQL migration, verified data import, concurrent workflow tests, and backup/restore exercise (see docs/POSTGRESQL.md)
- [ ] Scheduled production database/media backups and recovery policy
- [x] Deployment practice documentation and production WSGI startup instructions (`docs/CLOUD-PRACTICE.md`)
- [ ] In-app help
- [ ] Production security review and production load test with at least 50 reports
  - Local Django `runserver` burst probe completed on 2026-10-02: 50/50
    simultaneous report submissions succeeded; 75+ showed connection refusal.
    See `docs/CONCURRENCY-TEST-RESULTS.md`. This does not complete the
    production load-test item.

## Deferred features

- [x] Report photos: optional JPEG/PNG/WebP uploads, normalized and private to report participants
- [ ] Social or campus single sign-on
- [ ] AI matching
- [x] Maps and location picker — Leaflet + OpenStreetMap, browser Geolocation, and lat/lng fields all writing `Report.lat`/`Report.lng`. Shipped, not deferred. Drift corrected 29-09-2026.
- [ ] In-app chat
- [ ] Production email notifications
- [ ] Native mobile app
- [ ] Separate child or sub-item reports
- [ ] Automatic draft saving while typing
- [ ] Formal SRS and SDD documents — the CS-326 set was deleted 29-09-2026 along with the PHP project it described

## Verification

Current PostgreSQL verification (2026-10-04): **147 tests passed in 40.600 seconds**,
including Chrome browser tests and the added adversarial/concurrency regressions.
Concurrent new-report requests now produce one active draft; QR/new-report and
concurrent edit requests share the applicable draft; late-save replay leaves one report.
Evidence: `report-qa/QA-VERIFICATION-2026-10-04.txt`.

Migration 0006 is applied locally. System checks pass and there is no migration drift.
The 2026-10-03 database migration exercise imported and verified 111 application records;
restart, ID sequences, media references, and backup/restore passed then.
See `docs/POSTGRESQL.md` for that historical exercise and setup details.

- Django system check passes.
- Migration drift check passes with no new migration required.
- On this Windows workspace run `.venv/Scripts/python.exe manage.py test core --noinput`.
  On Linux/macOS use `.venv/bin/python manage.py test core`. Use `core`, not
  `core.tests`: the narrow form matches only `core/tests.py` and silently skips
  `core/test_screening.py`.
- **Historical inventory, 100 methods across 5 modules** (02-10-2026; superseded by the 147-test run above):

  | Module | Test methods | Classes | Skips |
  |---|---|---|---|
  | `core/tests.py` | 49 | 3 | none |
  | `core/test_screening.py` | 17 | 6 | none |
  | `core/test_adversarial.py` | 17 | 1 | none |
  | `core/test_item_features.py` | 12 | 2 | none |
  | `core/test_browser.py` | 5 | 1 | all, unless Playwright is installed |
  | **Total** | **100** | **13** | |

  So a bare run without Playwright is 95 passed and 5 skipped. The full suite ran on
  02-10-2026 with Chrome and Playwright: 100 passed, 0 failed, 0 skipped.
- The `subTest` sweeps expand into far more assertions at runtime than there are test
  methods, 14 `subTest` call sites in `core/test_screening.py` alone. Django reports one
  result per method, so the method count above is the number the runner prints.
- Historical adversarial edge suite: 42 checks, 34 pass, 8 correctly blocked by design.
  This is not an exhaustive coverage claim; see the QA report's coverage limitations.

## Demo accounts

Local demonstration credentials only:

| User ID | Login | Password | Access |
|---|---|---|---|
| 1 | admin@demo.local | Admin123! | Administrator and moderator |
| 2 | mod@demo.local | Moderator123! | Moderator / Management only |

Do not reuse these credentials in a deployed environment.
