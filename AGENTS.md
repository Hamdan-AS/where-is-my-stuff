# AGENTS.md — Where Is My Stuff? (Django)

## Project overview

Campus lost-and-found app. Django 5.2, Python 3.10+, SQLite, server-rendered templates, one app (`core`). No REST API; all pages are Django templates.

## Setup

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver 127.0.0.1:8086
```

App URL: `http://127.0.0.1:8086/`. Admin: `/admin/`.

Port 8085 is taken by a separate project at `../where-is-my-stuff-python`, which has its own `LOCALHOST-COMMANDS.txt`. Do not reuse it.

First-time machine: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

Create admin: `python manage.py createsuperuser`. Mark a user as staff for management access.

## Commands

| Task | Command |
|---|---|
| System check | `python manage.py check` |
| Migrate | `python manage.py migrate` |
| Migration drift | `python manage.py makemigrations --check --dry-run` |
| Unit tests | `python manage.py test core.tests` |
| Browser tests | `python manage.py test core.test_browser` |
| Install browser deps | `pip install -r requirements-dev.txt` |

Browser tests need Playwright and Chrome (`/usr/bin/google-chrome`). They use an isolated test database and bind a temporary localhost port.

## Structure

- `config/` — Django project settings, URLs, WSGI. Settings module: `config.settings`.
- `core/` — The only app: models, views, forms, services, migrations, templates, tests.
- `templates/` — Django templates (no separate frontend build).
- `static/` — CSS, JS, fonts, images, and vendored Leaflet 1.9.4 (BSD-2-Clause, see `static/leaflet-LICENSE`).
- `scripts/screening_probe.py` — Optional probe for `core/forms.py` screening patterns. Not part of the test suite.
- `tests/integration_test.py` — HTTP route integration test. Self-disables unless `NED_TEST_MODE=1` and an isolated `NED_DB_SOCKET` are set.
- `db.sqlite3` — Database (gitignored).
- `.venv/` — Virtual environment (gitignored).

## Key conventions

- **Custom user model**: `core.User` with email-based login (`AUTH_USER_MODEL = "core.User"`).
- **Settings**: `DJANGO_SECRET_KEY` and `DJANGO_DEBUG` read from env vars; defaults are dev-only. Change `SECRET_KEY` before deployment.
- **Timezone**: `Asia/Karachi`, `USE_TZ = True`.
- **SQLite transactions**: `IMMEDIATE` mode in settings to serialize writes.
- **Matching**: Score-based (category 20, location 20, date 15/10/5, description up to 15, private evidence up to 30). Requires 70+ points and 2+ agreements.
- **Demo credentials** (local only, never deploy): `admin@demo.local` / `Admin123!`, `mod@demo.local` / `Moderator123!`.
- **Human-readable report IDs**: `LFD-001`, `FND-002`.
- **No legacy PHP data imported**. The original PHP project was removed on 26-09-2026; the Django application is the only implementation. Its history is in the first commit.

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

See `TODO-INCREMENTAL.md` for current task status. Increments 3 and 4 are pending.
