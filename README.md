# Where Is My Stuff? — Django application

Local campus lost-and-found application. Python 3.10+, Django 5.2, SQLite, Django
templates, CSS, and small browser scripts.

## Run

```bash
cd /home/elite/sandbox/where-is-my-stuff-ui_iter
python3 -m venv .venv
source .venv/bin/activate
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

`manage.py test core` runs three modules: `core/tests.py`, `core/test_screening.py`, and
`core/test_browser.py`. The browser module is skipped unless Playwright is installed. Do
not use `manage.py test core.tests`, which silently skips the 303 lines of boundary
sweeps in `core/test_screening.py`.

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

A Lost report shows a QR code. Scanning it opens a public claim page where a finder
enters their contact details and claims the item, which seeds a Found draft for them.
Scanning your own report is refused, and the QR box renders only on Lost reports.

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

NED department values use a controlled catalog: CIS, CSIT, Civil Engineering, Mathematics,
Physics, Chemistry, Metallurgical Engineering, and Other. A Department Office handover
requires a department selection. BCIT is treated as a historical programme name, not a
current department label.

A proposal reserves both reports. The other participant accepts the same meeting; only
then are contacts visible. Either participant can record return at or after the meeting
time. Rejection releases a proposed reservation. Returned records and moderation history
persist. Management removal is an audited soft removal.

SQLite IMMEDIATE transactions serialize brief writes to prevent competing handovers in
the local app. A shared campus deployment requires deployment configuration, HTTPS,
login throttling, backup policy, and a PostgreSQL concurrency review.

## Delivery

`TODO-INCREMENTAL.md` is the single authoritative project tracker and holds the local demo
credentials. Increments 1 and 2 are complete, increments 3 and 4 are pending.

`docs/cs326-legacy/` holds the CS-326 documentation filing. It describes a removed PHP
implementation and does not match this code.

Deferred: separate child reports, social login, images, AI, chat, notifications by email,
hosted deployment, and formal academic SRS/SDD packages.
