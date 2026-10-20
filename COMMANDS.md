# Local commands

These commands are for this Django project on Windows PowerShell. PostgreSQL
runs in Docker and is bound to localhost port 55432. The Django site runs at
http://127.0.0.1:8086/.

## Open the project folder

```powershell
Set-Location 'C:\Users\rizwa\Desktop\sandbox\where_is_my_stuff@v2'
```

## First-time setup

Install Python 3.10 or newer and Docker Desktop, then create the virtual
environment and install the application dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

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

Check whether the local database port is listening:

```powershell
Get-NetTCPConnection -LocalPort 55432 -State Listen -ErrorAction SilentlyContinue
```

This project reads DATABASE_URL from .env. To use the SQLite fallback just
for the current PowerShell session, clear the environment override before
starting Django:

```powershell
$env:DATABASE_URL = ''
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8086
```

For PostgreSQL backup, SQLite import, and migration details, see
[docs/POSTGRESQL.md](docs/POSTGRESQL.md).
