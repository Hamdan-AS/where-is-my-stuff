# Local commands

These commands are for this Django project on Windows PowerShell. PostgreSQL
runs in Docker and is bound to localhost port 55432. The Django site runs at
http://127.0.0.1:8086/.

## Open the project folder

```powershell
Set-Location 'C:\Users\rizwa\Desktop\sandbox\projects\where-is-my-stuff\v2'
```

## First-time setup

Install Python 3.10 or newer and Docker Desktop, then create the virtual
environment and install the application dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Check `python --version` first. If `python` is not on PATH, use the full
path to a Python 3.10+ interpreter, for example
`& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv`.
If you use the `py` launcher instead, run `py --list` first: it fails with
"Unable to create process" when its default points at an uninstalled Python.

If this folder does not have a .env file yet, generate local database
credentials. This first call creates the file and exits:

```powershell
.\.venv\Scripts\python.exe scripts\setup_local_postgres.py
```

Start PostgreSQL, then initialize its local application role and database:

```powershell
docker compose up -d --wait
.\.venv\Scripts\python.exe scripts\setup_local_postgres.py
```

Apply database migrations:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

## Start the app on localhost

Start Docker Desktop if it is not already running, then from the project
folder run:

```powershell
docker compose up -d --wait
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8086
```

Open http://127.0.0.1:8086/. Keep the terminal open while using the site.
Press Ctrl+C in that terminal to stop Django.

If you have not created an account yet, open
http://127.0.0.1:8086/register/.

## Common Django commands

Run Django's configuration checks:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Show migration status:

```powershell
.\.venv\Scripts\python.exe manage.py showmigrations
```

Apply migrations after updating the project:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Create an administrator account:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Open the admin site at http://127.0.0.1:8086/admin/ after starting the
server.

## Run the tests

The tests run against SQLite and do not need Docker. Point `DATABASE_URL` at
SQLite for the current PowerShell session so the PostgreSQL value in `.env`
is not used (see [tests/README.md](tests/README.md) for why):

```powershell
$env:DATABASE_URL = 'sqlite:///ignored.sqlite3'

# Fast unit layer
.\.venv\Scripts\python.exe manage.py test tests.unit -v 2

# Every layered suite
.\.venv\Scripts\python.exe manage.py test tests.unit tests.blackbox tests.behavior tests.robustness -v 2

# Everything, including the existing suites
.\.venv\Scripts\python.exe manage.py test -v 2
```

Open a new terminal, or run `Remove-Item Env:DATABASE_URL`, before starting
the app again so it goes back to PostgreSQL.

## PostgreSQL lifecycle

Stop the database while preserving its data:

```powershell
docker compose stop
```

Start it again:

```powershell
docker compose start
```

Stop and remove the Compose container and network while preserving the named
database volume:

```powershell
docker compose down
```

Do not run `docker compose down -v` unless you intentionally want to delete the
local PostgreSQL data.

## Troubleshooting

Check Compose service status:

```powershell
docker compose ps
```

Read PostgreSQL logs:

```powershell
docker compose logs db
```

If Django fails with `django.db.utils.OperationalError: connection timeout
expired`, PostgreSQL is not running. Start Docker Desktop, then run
`docker compose up -d --wait`. For tests, set the SQLite `DATABASE_URL`
shown in "Run the tests" instead.

Check whether the local database port is listening:

```powershell
Get-NetTCPConnection -LocalPort 55432 -State Listen -ErrorAction SilentlyContinue
```

This project reads DATABASE_URL from .env. To run on the local SQLite file
instead (for example when Docker is not installed), point DATABASE_URL at it
for the current PowerShell session:

```powershell
Copy-Item db.sqlite3 db.sqlite3.bak
$env:DATABASE_URL = 'sqlite:///db.sqlite3'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8086
```

Do not use `$env:DATABASE_URL = ''`: Windows PowerShell deletes the variable
when it is set to an empty string, so `.env` is loaded and Django still
tries PostgreSQL.

For PostgreSQL backup, SQLite import, and migration details, see
[docs/POSTGRESQL.md](docs/POSTGRESQL.md).
