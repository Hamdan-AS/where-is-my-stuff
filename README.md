# Where Is My Stuff?

**A lost-and-found platform for Karachi.**

Where Is My Stuff? helps Karachiites report misplaced belongings, share items
they have found, and discover possible matches. It is designed for residents,
commuters, students, and people working across the city—from a wallet left in
Saddar to a bag found near a bus stop in Gulshan-e-Iqbal.

The application connects owners and finders through location-based matching,
private item details, and an agreed handover. The current version runs locally;
public deployment is still pending.

## How it works

1. **Report an item.** Choose Lost or Found and describe the item in a five-step
   wizard: Type → Details → Location → Matching → Review.
2. **Mark the location.** Enter a place or landmark and set coordinates using
   the map, your device location, or the latitude and longitude fields.
3. **Answer private questions.** Provide category-specific details that help
   distinguish the item from similar belongings.
4. **Review possible matches.** The app compares eligible reports using the
   category, distance, date, description, and private answers.
5. **Arrange a return.** Propose a meeting place and time. Contact details become
   available after the other participant accepts. Either person can record the
   return at or after the meeting time.

One account can report both lost and found items. Owners and finders arrange
the return themselves; a match score or QR scan does not verify ownership.

## Features

| Feature | What it does |
| --- | --- |
| Lost and found reports | Supports wallets, cards and IDs, keys, electronics, bags, documents, cash, and other items. |
| Location picker | Uses Leaflet and OpenStreetMap, with device location and manual coordinate entry. Place names and handover locations are free text. |
| Private matching | Requires different owners, opposite report types, open reports, the same category, at least two meaningful agreements, and a score of 70 or more. |
| Saved drafts | Saves each validated step when Next is selected. Drafts belong to the account and can be resumed later. |
| Item photos | Accepts optional JPEG, PNG, or WebP images up to 5 MiB and 24 megapixels; resizes the full image and removes metadata. |
| Report QR codes | Lets a finder sign in and start a Found draft from a Lost report's public details. |
| Personal QR labels | Creates printable item labels, active for six months, with owner-controlled deactivation and reactivation. |
| Handover workflow | Supports proposals, acceptance, dismissal, restoration, reservations, and return records. |
| Report history | Provides search, type/status filters, pagination, and human-readable report IDs. |
| Moderation | Allows staff to close or remove eligible reports with an audit trail. |

Wallet questions adapt to the selected contents. A wallet remains one report,
including an empty wallet or one with multiple cards. Bank and payment-service
options include HBL, MCB, UBL, Meezan Bank, NayaPay, SadaPay, JazzCash, Easypaisa,
and an Other option.

## Privacy and data handling

- Private matching answers are compared on the server and are not displayed in
  match or management pages. Public descriptions are screened for personal identifiers.
- Report photos are accessible to their owner and match participants. Stored
  images are converted to JPEG and resized to a maximum long edge of 1,800 pixels
  without cropping.
- Report contact details are revealed after both participants agree to a handover.
  **An active personal QR label intentionally shows its phone number to anyone
  scanning it.** Expired or deactivated labels hide that number.
- Drafts are stored on the server. There is no automatic saving while typing.
- Databases contain private matching answers, including full identifiers requested
  by some questionnaires. Application-level encryption at rest is not implemented.
  Credentials, databases, backups, and private uploads stay out of Git.

## Technology

Python 3.10+, Django 5.2, PostgreSQL, server-rendered Django templates, CSS,
JavaScript, Pillow, and QR generation. Leaflet is vendored locally; map tiles
come from OpenStreetMap. There is no separate frontend build or REST API.

SQLite is available as a fallback. PostgreSQL is the recommended local setup
and supports the transaction concurrency tests. Times use `Asia/Karachi`.

## Run locally

Install Python and Docker Desktop, then start Docker Desktop. For a fresh checkout:

```powershell
git clone https://github.com/Hamdan-AS/where-is-my-stuff-ui-surprise-v2.git
cd where-is-my-stuff-ui-surprise-v2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python scripts/setup_local_postgres.py
docker compose up -d --wait
python scripts/setup_local_postgres.py
python manage.py migrate
python manage.py runserver 127.0.0.1:8086
```

The first setup-script call creates a local `.env` with generated database
credentials. After PostgreSQL starts, the second call initializes the application
database and role. This bootstrap is for the local Docker database.

On macOS or Linux, activate the environment with `source .venv/bin/activate`;
the remaining Python commands are the same. The repository is private, so cloning
requires GitHub access.

Open **http://127.0.0.1:8086/** and register an account. On later runs, activate
the existing environment, start Docker with `docker compose up -d --wait`, and
run the server. See [PostgreSQL setup](docs/POSTGRESQL.md) for database details,
backups, and migration instructions.

To create an administrator:

```powershell
python manage.py createsuperuser
```

Account administration is at `/admin/`. Users marked as staff can access
`/management/`; reserve auth-management permissions for superusers.

## Verification

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test core --noinput
```

Use `test core` to include all unit, boundary, adversarial, image, QR, browser,
and PostgreSQL concurrency modules. `test core.tests` runs only one test module.

For browser checks:

```powershell
pip install -r requirements-dev.txt
python -m playwright install chromium
```

The tests use installed Chrome when available, otherwise Playwright's Chromium.
Browser tests are skipped when Playwright is absent; PostgreSQL-specific races
are skipped on SQLite.

The latest recorded full run on **4 October 2026 passed all 147 tests**, including
Chrome and PostgreSQL concurrency checks. See the [QA report](report-qa/QA-REPORT-2026-10-04.md)
and [verification record](report-qa/QA-VERIFICATION-2026-10-04.txt).

## Project status

The report, matching, handover, dashboard, QR-label, and photo workflows are
implemented. Draft acquisition reuses the applicable draft across concurrent
requests, and late saves cannot recreate a published draft.

Still pending: password reset, profile editing, notifications, management
pagination, login throttling, production backups, in-app help, hosted deployment,
production security review, and production load testing.

Production settings and deployment guidance are prepared. A public launch still
needs the remaining deployment and security work. The authoritative tracker is
[TODO-INCREMENTAL.md](TODO-INCREMENTAL.md).

## Further documentation

- [PostgreSQL setup and migration](docs/POSTGRESQL.md)
- [Deployment practice guide](docs/CLOUD-PRACTICE.md)
- [Repository hygiene and ignored files](docs/REPOSITORY-HYGIENE.md)
- [Concurrency verification](docs/CONCURRENCY-TEST-RESULTS.md)
- [Responsive UI verification](docs/RESPONSIVE-VERIFICATION.md)
