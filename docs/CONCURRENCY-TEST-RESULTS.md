# Local concurrency probe

Run on 2026-10-02 against an isolated temporary SQLite database. The probe used
independent HTTP sessions and real account registration followed by the full
five-step report wizard. Each cohort began together, used synthetic users, and
published one report per user. The repository's `db.sqlite3` was not used.

## Results

| Simultaneous users | Reports completed | Failed flows | Cohort time | Per-flow p95 |
|---:|---:|---:|---:|---:|
| 10 | 10 | 0 | 3.7 s | 3.7 s |
| 25 | 25 | 0 | 12.9 s | 12.8 s |
| 50 | 50 | 0 | 27.7 s (repeat: 27.7 s) | 27.3 s (repeat: 27.3 s) |
| 75 | 66 | 9 | 39.0 s | 38.6 s |
| 100 | 65 | 35 | 40.8 s | 39.9 s |

At 75 and 100 concurrent users, some connections were refused. The successful
50-user result confirms the app can complete a synchronized wave of 50 report
submissions in this environment. It does not establish an absolute maximum;
the first tested failing range is 75 users, so practical capacity under this
setup is between 50 and 75 concurrent submitters, with poor response times
already at 50.

## Limits of this measurement

- Server: Django `runserver`, `DEBUG=True`, local Windows environment.
- Database: SQLite using the project's `IMMEDIATE` transaction mode; SQLite
  serializes writers. Report publication runs matching while in a transaction,
  so simultaneous submissions queue behind database writes.
- This is a burst test of account registration and report creation, not a
  steady-state test of browsing, uploads, external services, or a production
  WSGI/ASGI server behind a reverse proxy.
- The result describes this development setup only. It is not a production
  user-capacity guarantee. A production estimate requires testing the intended
  server, database, host resources, and representative read/write mix.

## Reproduction

The temporary runner used for this probe has been removed. Re-run only after
creating an isolated benchmark harness/database; do not point a load test at
the private development `db.sqlite3`.
