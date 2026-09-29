# Where Is My Stuff? — Django rebuild

Local campus lost-and-found application. Python 3.10+, Django 5.2, SQLite, Django templates, CSS, and small browser scripts.

## Run

```bash
cd /home/elite/sandbox/where-is-my-stuff-python
source .venv/bin/activate
python manage.py migrate
python manage.py runserver 127.0.0.1:8085
```

Open http://127.0.0.1:8085/ and register. For a new machine, first run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create an administrator interactively:
```bash
python manage.py createsuperuser
```
Admin account management is at /admin/. Mark a user as staff for the restricted management page. Only superusers should receive auth-management permissions. No fixed demo passwords.

## Check

```bash
python manage.py check
python manage.py test core.tests
```

## Behaviour

Optional real-browser verification (uses installed Google Chrome):
```bash
pip install -r requirements-dev.txt
python manage.py test core.test_browser
```
Browser tests use a separate test database and leave no demo accounts in the application database.

One account reports Lost and Found items. Reports use Type → Details → Matching → Review with one final submit. Next saves each validated step to an account-owned database draft. Step links perform a normal page refresh to load the selected step. Private drafts are stored on the local server, never in browser localStorage; drafts are not automatically saved while typing. Selection refresh retains the visible inputs but does not claim to save them.

Wallet contents control the questions. Selecting CNIC and Cash shows their fields, not bank-card fields. An empty wallet is allowed. Up to five bank cards each have issuer and four-digit suffix. CNIC accepts three digits. No full identifier is collected. A wallet remains one report.
Bank or payment service names use a controlled list including HBL, MCB, UBL, Meezan Bank, NayaPay, SadaPay, JazzCash, and Easypaisa. Selecting Other asks for the service name.

Report descriptions are public to the involved users and moderation. Private matching answers are never rendered in match or management views. SQLite files contain these answers and must be protected by operating-system permissions; encryption at rest is not implemented.

Matching requires different owners, opposite report types, open reports and the same category. Category 20, location 20, date 15/10/5, shared-word description up to 15, and genuine private evidence up to 30. Missing values and generic None/Other do not earn evidence points. At least two agreements and 70 points are required. Scores are suggestions, not ownership guarantees.

NED department values use a controlled catalog: CIS, CSIT, Civil Engineering, Mathematics, Physics, Chemistry, Metallurgical Engineering, and Other. A Department Office handover requires a department selection. BCIT is treated as a historical programme name, not a current department label.

A proposal reserves both reports. The other participant accepts the same meeting; only then are contacts visible. Either participant can record return at or after the meeting time. Rejection releases a proposed reservation. Returned records and moderation history persist. Management removal is an audited soft removal.

SQLite IMMEDIATE transactions serialize brief writes to prevent competing handovers in the local app. A shared campus deployment requires deployment configuration, HTTPS, login throttling, backup policy, and a PostgreSQL concurrency review.

## Delivery

See TODO-INCREMENTAL.md for checked work and outstanding verification. The PHP project is reference material and has not been modified by this rebuild. No legacy data is imported.

Deferred: separate child reports, social login, images, maps, AI, chat, notifications by email, hosted deployment, and formal academic SRS/SDD packages.
