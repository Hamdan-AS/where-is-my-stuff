WHERE IS MY STUFF? - SETUP AND RUN GUIDE
========================================

Course project: a lost-and-found web app for Karachi, built with Django.
It runs locally on Windows with SQLite. No Docker, no PostgreSQL, and no .env
file are needed.

Design and SRS documents are submitted separately from this code archive.

--------------------------------------------------------------------------------
1. REQUIREMENTS
--------------------------------------------------------------------------------
- Windows 10 or 11
- Python 3.10 - 3.13 (tested on 3.12)      check with: python --version
- Internet only for map tiles; every other feature works offline

--------------------------------------------------------------------------------
2. FIRST-TIME SETUP
--------------------------------------------------------------------------------
Open PowerShell in the folder containing manage.py, then run:

    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt

The .venv folder is not included in this archive because it is machine-specific.
These three commands are the only setup required.

--------------------------------------------------------------------------------
3. RUN THE APP
--------------------------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\run_local.ps1

The launcher applies database migrations, selects a free port from 8765 to 8774,
and prints the address to open in a browser. Register an account to begin.
Press Ctrl+C to stop the server.

Manual equivalent:

    .\.venv\Scripts\python.exe manage.py migrate
    .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8765

--------------------------------------------------------------------------------
4. RUN THE TESTS (optional)
--------------------------------------------------------------------------------
    powershell -ExecutionPolicy Bypass -File .\scripts\run_tests.ps1

Expected result: 139 tests, OK, 3 skipped (PostgreSQL-only tests).

--------------------------------------------------------------------------------
5. TROUBLESHOOTING
--------------------------------------------------------------------------------
"Project dependencies are unavailable"
    Section 2 was skipped or .venv is missing. Re-run the setup commands.

"running scripts is disabled on this system"
    Launch with: powershell -ExecutionPolicy Bypass -File .\<script>.ps1

"Ports 8765 through 8774 are busy"
    Close the old server window, or run:
    .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8790

Map area is blank or grey
    No internet connection. Type coordinates or a place name instead.

"DisallowedHost"
    Open the exact 127.0.0.1 or localhost address printed by the launcher.
    The site is not reachable from another device.

Django asks for DJANGO_SECRET_KEY or DATABASE_URL
    A .env file exists, or DJANGO_SETTINGS_MODULE is set to config.production.
    Delete the .env and use the normal launch commands above.

--------------------------------------------------------------------------------
6. CONTENTS OF THIS ARCHIVE
--------------------------------------------------------------------------------
Included:
    config/              Django project settings and URL routing
    core/                application code: models, forms, services, views,
                         migrations, admin, management commands, and tests
    templates/           HTML templates
    static/              CSS, JavaScript, fonts, and map assets
    scripts/             test runner and optional PostgreSQL helper
    manage.py            Django entry point
    run_local.ps1        one-command local launcher
    requirements.txt     runtime dependencies
    requirements-production.txt
    compose.yaml         optional local PostgreSQL container
    README.md            project overview and feature description
    COMMANDS.txt         command reference
    README.txt           this guide

Excluded on purpose:
    .venv/, db.sqlite3, private-media/ (uploaded photos), __pycache__/,
    SRS documents, LaTeX sources, and build output.

--------------------------------------------------------------------------------
7. SCOPE AND SECURITY
--------------------------------------------------------------------------------
This is a course demonstration: DEBUG is on, the database is SQLite, and the
SECRET_KEY is a local placeholder. Do not deploy it publicly.

config.production is intended for real hosting only and requires
DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DATABASE_URL, and DJANGO_MEDIA_ROOT.
