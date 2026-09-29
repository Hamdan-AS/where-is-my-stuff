# Where Is My Stuff? incremental task tracker

This is the single authoritative project tracker.

Stack: Django 5.2, SQLite, server-rendered templates. Updated: 13-09-2026.

## Increment 1: core foundation

Status: complete.

- [x] Django project, settings, migrations, SQLite database
- [x] Custom user model with email login, registration, logout, sessions, and CSRF
- [x] Four-step report wizard with account-owned server drafts
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
- [ ] Tests for password reset, profile, notifications, and management pagination

## Increment 4: deployment and security

Status: pending.

- [ ] Logging, environment-based secrets, and production settings
- [ ] Secure cookies, HSTS, content-type, frame, and host configuration
- [ ] Login throttling or rate limiting
- [ ] Static collection and production ASGI/WSGI deployment configuration
- [ ] PostgreSQL option, migration notes, and backup policy
- [ ] Deployment documentation and in-app help
- [ ] Production security review and load test with at least 50 reports

## Deferred features

- [ ] Image uploads
- [ ] Social or campus single sign-on
- [ ] AI matching
- [ ] Maps and location picker
- [ ] In-app chat
- [ ] Production email notifications
- [ ] Native mobile app
- [ ] Separate child or sub-item reports
- [ ] Automatic draft saving while typing
- [ ] Formal SRS and SDD documents

## Verification

- Django system check passes.
- Migration drift check passes with no new migration required.
- 39 unit tests pass with `.venv/bin/python manage.py test core.tests` (includes public-field screening and the four scan-flow regression tests).
- 2 browser tests pass with `.venv/bin/python manage.py test core.test_browser`.
- Adversarial edge suite: 42 checks, 34 pass, 8 correctly blocked by design, 0 gaps.
- Browser tests need permission to bind a temporary localhost port in the sandbox.

## Demo accounts

Local demonstration credentials only:

| User ID | Login | Password | Access |
|---|---|---|---|
| 1 | admin@demo.local | Admin123! | Administrator and moderator |
| 2 | mod@demo.local | Moderator123! | Moderator / Management only |

Do not reuse these credentials in a deployed environment.
