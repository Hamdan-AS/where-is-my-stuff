# Test suite

This directory is the layered test suite for **Where Is My Stuff?**. It is
additive: the existing `core/tests.py`, `core/test_*.py`, and `core/qa_tests/`
suites stay where they are and continue to run.

The layers are split by the question each one asks, so a failure points at the
right level of the product:

| Layer | Directory | Question |
| --- | --- | --- |
| Unit | `tests/unit/` | Does each module's own logic hold in isolation? |
| Black box | `tests/blackbox/` | What does the HTTP contract look like from outside? |
| Behaviour | `tests/behavior/` | Does a real user flow through the product correctly? |
| Robustness | `tests/robustness/` | Do hostile, empty, and malformed inputs fail safely? |

`tests/support.py` holds the shared cast of users, complete answer sets for
every category, and helpers for the wizard, meetings, photos, and temporary
media. Tests use real model rows and real HTTP clients. Mocks are reserved for
storage failures and for pinning a random token.

## Running

From `where_is_my_stuff@v2/`:

```powershell
# The fast unit layer
$env:DATABASE_URL='sqlite:///ignored.sqlite3'
.\.venv\Scripts\python.exe manage.py test tests.unit -v 2

# Every layered suite
.\.venv\Scripts\python.exe manage.py test tests.unit tests.blackbox tests.behavior tests.robustness -v 2

# Everything, including the existing suites
.\.venv\Scripts\python.exe manage.py test -v 2
```

### Why `DATABASE_URL` is set to a SQLite URL

`config/settings.py` loads `.env` with `load_dotenv(..., override=False)`. In
PowerShell, `$env:DATABASE_URL=''` removes the variable instead of setting it to
an empty string, so `.env` is loaded and the tests try to reach PostgreSQL.

Setting a real SQLite URL keeps the variable present and forces the test
database to SQLite:

```powershell
$env:DATABASE_URL='sqlite:///ignored.sqlite3'
```
Django still creates its normal isolated test database; `ignored.sqlite3` is not
used as the test database name. If PostgreSQL is available, remove the override
or point `DATABASE_URL` at the test server.

### Browser dependencies

`requirements-dev.txt` still lists Playwright because the existing
`core/test_browser.py` suite uses it. The layered suite in this directory does
not; no browser install is needed for the four layers above.

## What each layer covers

### `tests/unit/`

One module per application module, testing that module's own logic rather than
routing everything through an end-to-end flow:

* `test_models.py` — derived display ids, counts, defaults, ordering, and
  PROTECT/CASCADE/unique/check constraints.
* `test_forms.py` — text screening, phone/date/coordinate validators, every
  category's `schema()`, the meeting format, registration, and email login.
* `test_services.py` — draft validation, haversine and location bands, scoring
  rules, publish (including photo cleanup), recalculation, the full handover
  state machine, and moderation.
* `test_views.py` — selection parsing, login/dashboard redirects, history
  filters and pagination, wizard step clamping and gating, QR scanning, label
  and photo views, management errors, edits, and match actions.
* `test_qr.py` — PNG output, stability, and independent buffers.
* `test_qr_labels.py` — URL-safe tokens, SHA-256 digests, month-end expiry
  clamping, and label QR delegation.
* `test_images.py` — JPEG re-encoding, resize limits, transparent flattening,
  EXIF orientation, metadata stripping, and mode conversion.

### `tests/blackbox/`

* Public and private routes, redirects, and preserved `next` destinations.
* Route smoke tests for every primary page.
* GET/PUT/PATCH/DELETE on POST-only endpoints.
* CSRF enforcement on login, registration, the wizard, edits, QR labels,
  logout, and match actions.

### `tests/behavior/`

* Registration, email-as-username, password rules, login, remember-me,
  open-redirect rejection, and logout.
* The five-step wizard: navigation gates, drafts, all eight categories,
  category changes, validation, review escaping, duplicate warnings,
  publication, and edits.
* Dashboard counts, hero match ordering, history search/filter/pagination,
  report detail, and ownership scoping.
* Scoring rules, automatic matching, the full handover state machine, contact
  release only after acceptance, competing handovers, and audit events.
* Photo validation, normalisation (orientation, transparency, resizing), and
  owner/participant-only access.

### `tests/robustness/`

* Invisible/control/bidi characters and identifiers in public fields.
* Length, phone, email, date, coordinate, and meeting-time boundaries.
* HTTP posts with hostile values: form errors, no partial saves, no 500s.
* Missing rows, foreign ownership, wrong HTTP methods, and management errors.
* Incomplete or tampered drafts, double publication, stale drafts, and
  multi-draft QR scans.
* Storage failure cleanup, missing private files, and inactive/expired labels.
* Contact, private-answer, photo, QR-token, redirect, and cookie privacy.

## Notes and limitations

* Tests that need PostgreSQL-specific concurrency behaviour are skipped on
  SQLite. The application detects the backend and uses an advisory lock only on
  PostgreSQL. This covers `core/test_postgres.py` and the threaded race tests in
  `core/qa_tests/`, because SQLite locks the whole table instead of a row.
* The geo tests do not depend on a live map tile server. Leaflet is allowed to
  fail to fetch tiles without making a test flaky; only page errors are
  asserted.
* `core/services.py` rejects a non-mapping `Draft.data` / `answers` payload as a
  normal validation error. Draft data is a JSON column, so this keeps a damaged
  or legacy row from producing a 500 during publication.
