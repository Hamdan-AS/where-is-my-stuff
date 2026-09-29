# AGENTS.md — Where Is My Stuff? (Django)

## Project overview

Campus lost-and-found app. Django 5.2, Python 3.10+, SQLite, server-rendered templates, one app (`core`). No REST API; all pages are Django templates.

This folder is the authoritative copy. There are no sibling copies to keep in sync.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8086
```

App URL: `http://127.0.0.1:8086/`. Admin: `/admin/`.

First-time machine only: the `python3 -m venv` line.

Create admin: `python manage.py createsuperuser`. Mark a user as staff for management access.

## Commands

| Task | Command |
|---|---|
| System check | `python manage.py check` |
| Migrate | `python manage.py migrate` |
| Migration drift | `python manage.py makemigrations --check --dry-run` |
| Unit tests | `python manage.py test core` |
| Browser tests | `python manage.py test core.test_browser` |
| Install browser deps | `pip install -r requirements-dev.txt` |

The unit test command is `core`, not `core.tests`. `core.tests` matches only `core/tests.py` and silently skips `core/test_screening.py`, which holds 303 lines of boundary sweeps over the form layer.

Browser tests need Playwright and Chrome (`/usr/bin/google-chrome`). They use an isolated test database and bind a temporary localhost port.

## Structure

- `config/` — Django project settings, URLs, WSGI. Settings module: `config.settings`.
- `core/` — The only app: models, views, forms, services, migrations, templates, tests.
  - `core/qr.py` — QR PNG generation for the claim flow.
  - `core/test_screening.py` — form boundary sweeps, no database.
  - `core/test_browser.py` — Playwright tests, skipped without Playwright.
- `templates/` — Django templates (no separate frontend build).
- `static/` — CSS, JS, fonts, images, and vendored Leaflet 1.9.4 (BSD-2-Clause, see `static/leaflet-LICENSE`). `static/images/` holds Leaflet marker and layer sprites.
- `docs/WIREFRAME-BRIEF.md` — written spec of all screens, for generating wireframes.
- `docs/cs326-legacy/` — CS-326 documentation filing. Describes the removed PHP implementation. Not a description of this code.
- `db.sqlite3` — Database (gitignored, contains private answers).
- `.venv/` — Virtual environment (gitignored).

## Key conventions

- **Custom user model**: `core.User` with email-based login (`AUTH_USER_MODEL = "core.User"`).
- **Settings**: `DJANGO_SECRET_KEY` and `DJANGO_DEBUG` read from env vars; defaults are dev-only. Change `SECRET_KEY` before deployment.
- **Timezone**: `Asia/Karachi`, `USE_TZ = True`.
- **SQLite transactions**: `IMMEDIATE` mode in settings to serialize writes.
- **Location**: three inputs, one source of truth. The Leaflet picker, the browser geolocation button, and the lat/lng fields all write `Report.lat` and `Report.lng`.
- **Wizard**: five steps, `Type` → `Details` → `Location` → `Matching` → `Review`, one view serving all of them (`core/views.py:wizard`).
- **Matching**: Score-based (category 20, location 20 by haversine band, date 15/10/5, description up to 15, private evidence up to 30). Requires 70+ points and 2+ agreements. Rules in `matching-architecture.md`.
- **Demo credentials** (local only, never deploy): `admin@demo.local` / `Admin123!`, `mod@demo.local` / `Moderator123!`. Also in `TODO-INCREMENTAL.md`.
- **Human-readable report IDs**: `LFD-001`, `FND-002`.
- **No legacy PHP data imported**. The original PHP project was removed on 26-09-2026; the Django application is the only implementation. Its state before the 29-09-2026 cleanup is git commit `54fa6fc`.

## Testing notes

- Tests use `@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])` for speed.
- Browser tests are skipped unless Playwright is installed (`requirements-dev.txt`).
- Browser tests use `StaticLiveServerTestCase` and launch Chrome headlessly.

## Important constraints

- Private matching answers are never rendered in match or management views.
- Reports, answers, drafts, and matches are absent from Django admin.
- `db.sqlite3` contains private answers — protect with OS permissions.
- No automatic draft saving while typing.

## Open work

See `TODO-INCREMENTAL.md` for current task status. It is the single authoritative tracker. Increments 3 and 4 are pending.
