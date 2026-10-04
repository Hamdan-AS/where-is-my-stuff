# PostgreSQL setup and migration

V2 now uses PostgreSQL locally through its gitignored `.env` file. The older
sibling was left unchanged and the original `db.sqlite3` was preserved. This is a local
migration, not an AWS deployment.

## Daily startup (PowerShell)

Start Docker Desktop, then run from the v2 project directory:

```powershell
docker compose up -d --wait
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8086
```

Open http://127.0.0.1:8086/. Existing accounts keep their passwords. Users sign
in again because browser sessions were deliberately not imported.

PostgreSQL 17 is in a Docker named volume, bound only to `127.0.0.1:55432`.
`docker compose stop` stops it without deleting data. `docker compose down`
also preserves the named volume. **Do not use `down -v` unless intentionally
destroying the database.** The app role is `wims`, a non-superuser with CREATEDB
for Django's isolated test databases. A cloud app role should not have CREATEDB.
The bootstrap administrator password and app URL are stored only in `.env`.
Environment variables supplied by the host take precedence over `.env`.

## First setup on another machine

Create/activate a Python virtual environment and install `requirements.txt`.
With Docker Desktop installed and running:

```powershell
python scripts/setup_local_postgres.py
docker compose up -d --wait
python scripts/setup_local_postgres.py
python manage.py migrate --noinput
```

The first script call generates local credentials if `.env` is absent; the
second initializes the database and app role. It is restricted to the local
compose endpoint and must not be used on RDS.

For AWS, set `DATABASE_URL` to the private PostgreSQL/RDS endpoint and use
`DJANGO_SETTINGS_MODULE=config.production` with the other production variables.
Apply migrations against the new database. Do not upload the local `.env`,
SQLite files, backups, or demonstration credentials to a public repository.

## Transferring an existing SQLite database

Stop all app writers first. Set DATABASE_URL for the destination, apply schema
migrations, then run:

```powershell
python manage.py import_sqlite db.sqlite3
```

The destination must have no application records. The command refuses to merge
or overwrite existing records. It creates a consistent SQLite snapshot and
private fixture under `.local-data/backups`, imports within a transaction, and
verifies every application field. A verification failure rolls back the import.
Natural keys preserve user/group permissions across regenerated content types.
User passwords, report IDs, private answers, drafts, matches, and activity events
are preserved. Sessions and Django admin logs are excluded. Photos and QR files
stay in private media storage; moving to another machine requires copying those
files separately with their relative paths unchanged.

## Transaction behaviour

PostgreSQL advisory transaction locks serialize report publication, matching,
handover transitions, and moderation across workers. Readers remain concurrent.
This intentionally preserves the original app's SQLite IMMEDIATE behaviour and
prevents missed matches, duplicate draft publication, and double reservations.
It is a simple correctness-first approach for a small app; high-volume writes
may later need narrower locks. Advisory locking protects these service paths,
not arbitrary SQL or external tools modifying reports directly.

## Verification performed on 2026-10-03

- Imported and verified **111 application records**: 9 users, 19 reports,
  3 drafts, 8 matches, 72 events, and 0 personal QR labels.
- All **104 tests passed on PostgreSQL**, including six Playwright browser
  tests and three concurrent transaction tests.
- No system-check issues or migration drift.
- PostgreSQL restart preserved all record counts; ID sequences and existing
  private media references were verified.
- A PostgreSQL custom-format backup was restored into a separate verification
  database, and all application records were compared successfully.
- Repeating the SQLite import was correctly refused because the target already
  contained data.
- Playwright MCP verified a login session stored in PostgreSQL and 24 page/width
  combinations, with no overflow, failed responses, or JavaScript errors.

The preserved SQLite snapshot and PostgreSQL backup are under the gitignored
`.local-data/backups` directory. The separate restore-check database is retained
locally for inspection. Protect backups like the database: they contain private
answers and password hashes. A volume is persistence, not a backup policy.

## Backup and tests

```powershell
# Store a PostgreSQL archive inside the container, then copy it without piping
# binary output through Windows PowerShell's text encoding.
docker compose exec -T db pg_dump -U wims -d wims -Fc -f /tmp/wims-backup.dump
docker compose cp db:/tmp/wims-backup.dump .local-data/backups/wims-backup.dump
python manage.py test core --noinput
```

Back up private-media separately. Restore only into a fresh database and verify
it before switching the app. Test execution creates/drops `test_wims`; never
point the test runner at an account that cannot safely create test databases.

Without a DATABASE_URL, development retains the SQLite fallback. To select it
explicitly in PowerShell, set `$env:DATABASE_URL=''` for that shell. This does
not copy new PostgreSQL changes back to SQLite; the preserved SQLite file is a
pre-cutover snapshot. Production settings still require PostgreSQL.
