# Where Is My Stuff? — Django application

Local campus lost-and-found application. Python 3.10+, Django 5.2, PostgreSQL, Django
templates, CSS, and small browser scripts.

## Run

This machine's v2 database has been migrated to PostgreSQL. Start Docker Desktop,
then run `docker compose up -d --wait` before starting Django. Local credentials
are loaded from the gitignored `.env` file. See [PostgreSQL setup and migration](docs/POSTGRESQL.md)
for first setup on another machine, backups, and the preserved SQLite source.

Run these commands from the project directory. Create the virtual environment only
the first time on a machine.

```bash
python -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux, use `source .venv/bin/activate` instead. Then install and start:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8086
```

Open http://127.0.0.1:8086/ and register. Skip the venv creation on a machine that
already has one.

Create an administrator interactively:
```bash
python manage.py createsuperuser
```

Admin account management is at /admin/. Mark a user as staff for the restricted
management page. Only superusers should receive auth-management permissions.

## Check

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test core
```

`manage.py test core` runs the unit, boundary, adversarial, image/QR, and browser test
modules. Browser tests are skipped unless Playwright and Chrome are available. Do not use
`manage.py test core.tests`, which silently skips the boundary sweeps in
`core/test_screening.py`.

## Behaviour

One account reports Lost and Found items. Reports use a five-step wizard: Type, Details,
Location, Matching, Review, with one final submit. Next saves each validated step to an
account-owned database draft. Step links perform a normal page refresh to load the
selected step. Private drafts are stored on the local server, never in browser
localStorage; drafts are not automatically saved while typing. Selection refresh retains
the visible inputs but does not claim to save them.

Location has three ways in: the Leaflet and OpenStreetMap picker, the browser Geolocation
button, and the latitude and longitude fields. All three write to the same
`Report.lat` and `Report.lng` columns, which stay the single source of truth for
position. The fields are the keyboard and no-JS path when tiles fail.

A Lost report shows a QR code to share with the finder. Scanning it asks them to sign in,
then seeds a Found draft with public item details. Scanning from the same account is
refused. Accounts are not verified real-world identities, so another account can still
start a Found draft from the QR; the code does not prove possession or ownership. The QR
box renders only on Lost reports. Owners can also make six-month personal item labels
that show their phone number to anyone scanning an active label; the owner and finder
arrange the return themselves.

Report photos are optional. JPEG, PNG, and WebP uploads are limited to 5 MiB and 24
megapixels. The wizard previews the selected photo and shows it again on Review. Stored
photos are oriented, resized to at most 1,800 pixels on the long edge without cropping,
converted to JPEG, and stripped of metadata. Only the owner and match participants can
view report photos.

Wallet contents control the questions. Selecting CNIC and Cash shows their fields, not
bank-card fields. An empty wallet is allowed. Up to five bank cards each have issuer and
full 16-digit number. CNIC accepts 13 digits. A wallet remains one report. Issuing
service and card type must agree.
Bank or payment service names use a controlled list including HBL, MCB, UBL, Meezan Bank,
NayaPay, SadaPay, JazzCash, and Easypaisa. Selecting Other asks for the service name.

Report descriptions are public to the involved users and moderation. Private matching
answers are never rendered in match or management views. SQLite files contain these
answers and must be protected by operating-system permissions; encryption at rest is not
implemented.

Matching requires different owners, opposite report types, open reports and the same
category. Category 20, location 20 by haversine band, date 15/10/5, shared-word
description up to 15, and genuine private evidence up to 30. Missing values and generic
None/Other do not earn evidence points. At least two agreements and 70 points are
required. Scores are suggestions, not ownership guarantees. Full rules are in
`matching-architecture.md`.

NED student-card issuer values use a controlled department catalog: CIS, CSIT, Civil
Engineering, Mathematics, Physics, Chemistry, Metallurgical Engineering, and Other.
BCIT is treated as a historical programme name. Handover meeting places are free text.

A proposal reserves both reports. The other participant accepts the same meeting; only
then are contacts visible. Either participant can record return at or after the meeting
time. Rejection releases a proposed reservation. Returned records and moderation history
persist. Management removal is an audited soft removal.

PostgreSQL advisory transaction locks serialize matching and handover writes.
Draft acquisition locks the owner's row so concurrent new-report, QR-scan, and edit
requests reuse the same applicable draft. Late step saves cannot recreate a deleted draft.
A shared campus deployment still requires HTTPS, login throttling, a backup
policy, production security review, and load testing.

## Delivery

For cloud learning, see [the cloud practice guide](docs/CLOUD-PRACTICE.md),
`requirements-production.txt`, and `config.production`. Cloud deployment
remains pending. Local PostgreSQL migration and concurrency
validation are complete; see [verification results](docs/POSTGRESQL.md).

`TODO-INCREMENTAL.md` is the single authoritative project tracker and holds the local demo
credentials. Increments 1 and 2 are complete, increments 3 and 4 are pending.

The CS-326 documentation set, and the PHP project it described, are both gone. The
Django application is the only implementation.

Deferred: separate child reports, social login, AI, chat, notifications by email, hosted
deployment, and formal academic SRS/SDD packages.
