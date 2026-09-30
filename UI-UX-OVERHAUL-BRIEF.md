# UI/UX overhaul brief

Read this before changing any template or stylesheet. It describes what the application
actually does, where the seams between the server and the browser are, and which parts of
the current design are load-bearing rather than cosmetic.

Every claim here was read out of the source on 29-09-2026. Line references are included so
each statement can be checked.

---

## 1. What this application is

A campus lost and found web app. A member of the public signs in with an email address, files
a report saying whether they lost an item or found one, and the server scores the report
against every other open report of the opposite kind in the same category. A pair scoring 70
or more, with at least two agreeing private answers, becomes a "possible match" that both
people can see. The two then agree a public meeting place and time, and confirm the handover.

Three ideas shape every screen:

- **Public versus private split.** Some text is visible to everyone. Other text is visible only
  to the person who found the counterpart report. The split is enforced in the database, not in
  the template, so a redesign cannot leak it by accident.
- **Nothing is revealed until a handover is scheduled.** Contact details are the sharpest case.
  They unlock only at the `Handover Scheduled` state, not on first contact.
- **No self-matching.** A person cannot be matched with their own report, and cannot match a
  report of the same kind.

## 2. Three constraints that decide what a redesign is allowed to be

These are not preferences. They are properties of the codebase, and breaking any of them
produces a broken application rather than an ugly one.

**There is no API and no build step.** Every page is a Django template rendered by a view
returning HTML. There is no JSON endpoint, no React, no bundler, no `package.json`, no
`node_modules`. The only client code is `static/app.js` (202 lines) and `static/auth.js`
(13 lines), both plain ES2017 with no imports. If a redesign needs a component model, a CSS
framework, or an icon set, you are adding a build step and changing the deployment story. That
is a decision, not an implementation detail, and it should be made deliberately.

**The database is the only enforcement of the privacy split.** `Report.answers` holds the
private questionnaire as a JSON blob. Every other report field is public. The match screen
deliberately renders the two public reports side by side and never the answers. A redesign
that adds a "detail" panel to a report card must not read `answers`.

**No automatic draft saving while typing.** The wizard saves on explicit "Save and next". This
is a stated project constraint in `AGENTS.md`, and `core/test_screening.py` plus the wizard
tests depend on the step-by-step contract. Client-side autosave would change the `Draft.updated_at`
semantics that the resume prompt and the login redirect both rely on (`core/views.py:33-37`,
`core/views.py:52-55`).

## 3. Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8086
```

The app is at `http://127.0.0.1:8086/`. Django admin is at `/admin/`; see section 12 for why
almost nothing is registered there.

Verification commands:

| Task | Command |
|---|---|
| System check | `python manage.py check` |
| Migration drift | `python manage.py makemigrations --check --dry-run` |
| All tests | `python manage.py test core` |
| Browser tests only | `python manage.py test core.test_browser` |
| Install browser deps | `pip install -r requirements-dev.txt` |

`manage.py test core` discovers 65 test methods and executes 63, because the 2 browser
methods are skipped unless Playwright is installed. The command is `core`, never
`core.tests`. The narrower label silently skips all 17 methods in `core/test_screening.py`.

## 4. Request lifecycle

There is one path through the whole application. Every screen is this:

```
browser  --POST form + CSRF token-->  view  -->  form validates  -->  service  -->  ORM
   ^                                                                              |
   |------------------------------ redirect with ?step=N or messages -------------|
```

Consequences for a redesign:

- State lives in the URL (`?step=`, `?q=`, `?status=`, `?page=`) and in the session. A client-side
  router would fight the server's step gates, which read `request.GET.get("step")` and redirect
  backwards when data is missing (`core/views.py:141-152`).
- Success and failure are communicated by `django.contrib.messages`, rendered in one loop in
  `base.html:82-84`. There is no toast system and no inline success region. If you add one,
  keep the messages framework working, because every action in the application reports through it.
- A full page load happens on every wizard step. State is not preserved client-side.

## 5. File map

| File | Lines | Role in a redesign |
|---|---|---|
| `config/settings.py` | 25 | Timezone `Asia/Karachi`, SQLite in `IMMEDIATE` mode, no `STATIC_ROOT`, no email backend |
| `config/urls.py` | 20 | All 14 routes |
| `core/models.py` | 72 | `User`, `Report`, `Draft`, `Match`, `Event` |
| `core/forms.py` | 255 | Every field, every validator, the dynamic private questionnaire |
| `core/views.py` | 287 | All 14 routes' handlers, the wizard state machine |
| `core/services.py` | 180 | Matching score, publish, handover transitions, moderation |
| `core/qr.py` | 12 | PNG generation for the claim flow |
| `core/admin.py` | 10 | Registers `User` only, on purpose |
| `templates/base.html` | 95 | Shell, sidebar, topbar, messages, script tag |
| `templates/dashboard.html` | 210 | Largest screen, four stacked sections |
| `templates/match.html` | 132 | Side-by-side comparison plus the handover form |
| `templates/wizard.html` | 107 | All five steps through one template |
| `templates/auth.html` | 99 | Login and registration on one page |
| `templates/report.html` | 79 | One report, its matches, its activity log |
| `templates/reports.html` | 30 | Filterable, paginated history table |
| `templates/management.html` | 42 | Staff-only moderation list |
| `templates/resume_draft.html` | 21 | Draft found on arrival, continue or discard |
| `templates/closed_notice.html` | 14 | Scanned an already-resolved report |
| `static/app.css` | 1964 | The entire app stylesheet |
| `static/auth.css` | 319 | Login and registration stylesheet, plus the only `@font-face` rules |
| `static/app.js` | 202 | All client behaviour |
| `static/leaflet.css`, `static/leaflet.js` | vendored | Leaflet 1.9.4, BSD-2-Clause, do not edit |

## 6. Data model

Five tables. Read `core/models.py` for the exact fields.

**`User`** extends `AbstractUser`. Login is by email, and `username` is set equal to the lowercased
email at registration (`core/forms.py:90-95`), so both columns are populated. A
`visible_report_count` property drives sidebar nav visibility (`templates/base.html:34-39`).

**`Report`** is the central entity. Public fields: `kind`, `title`, `category`, `description`,
`location`, `lat`, `lng`, `location_detail`, `event_date`, `contact`. Private field:
`answers`, a JSON blob. Control fields: `status`, `reserved`, `created_at`, `owner`.
`public_id` is a UUID with a `db_index`, used in the QR URL so the route does not leak a
sequential primary key. `display_id` renders the human-readable `LFD-001` or `FND-002`
(`core/models.py:33-36`) and is the identifier to show a user.

`status` takes four values: `Open`, `Returned`, `Closed`, `Removed`. `Removed` is hidden from
listings everywhere. `reserved` is a separate boolean meaning "a handover is in progress",
independent of `status`, and it is what locks editing.

**`Draft`** is a JSON blob plus an optional `report` pointer. A draft with a null `report` is
unpublished. A draft with a `report` is an edit-in-progress. It is deleted on publish
(`core/services.py:115`).

**`Match`** joins two reports. `lost` and `found` are protected foreign keys, so a report with
any match history cannot be deleted. `score`, `breakdown` (a per-component JSON score),
`state`, `proposer`, `rejected_by`, `meeting_place`, `meeting_at`. A unique constraint on the
`(lost, found)` pair prevents duplicates (`core/models.py:55-59`).

**`Event`** is an append-only activity log, one row per state change, rendered on the report
detail screen.

## 7. Routes

From `config/urls.py`. "Auth" means `@login_required`.

| Path | Name | Auth | Method | View | Template |
|---|---|---|---|---|---|
| `/admin/` | | staff | any | Django admin | |
| `/register/` | `register` | no | GET POST | `views.register:40` | `auth.html` |
| `/login/` | `login` | no | GET POST | `AccountLoginView:20` | `auth.html` |
| `/logout/` | `logout` | no | POST | Django `LogoutView` | |
| `/` | `dashboard` | yes | GET | `views.dashboard:49` | `dashboard.html` |
| `/reports/` | `reports` | yes | GET | `views.report_history:98` | `reports.html` |
| `/reports/new/` | `create` | yes | GET | `views.wizard:125` | `resume_draft.html` or redirect |
| `/drafts/<pk>/` | `draft` | yes | GET POST | `views.wizard:125` | `wizard.html` |
| `/reports/<pk>/` | `report` | yes | GET | `views.report_detail:204` | `report.html` |
| `/reports/<pk>/edit/` | `edit` | yes | POST only | `views.edit_report:211` | redirect |
| `/matches/<pk>/` | `match` | yes | GET POST | `views.match_detail:225` | `match.html` |
| `/r/<uuid>/qr/` | `report-qr` | **no** | GET | `views.report_qr_image:258` | PNG |
| `/r/<uuid>/found/` | `report-found` | yes | GET | `views.report_found:264` | `closed_notice.html` or redirect |
| `/management/` | `management` | staff | GET POST | `views.management:245` | `management.html` |

Two routing details a redesign must respect. `/r/<uuid>/found/` is the QR scan target and is
the **only** entry point a person who has never seen the site can reach, so it is effectively
a landing page. And `/reports/<pk>/edit/` is `@require_POST`: there is no edit page, so the Edit
control in `report.html:34-37` must stay a POST form carrying `{% csrf_token %}`, not a link.

## 8. Screens

| Screen | Purpose | Main components |
|---|---|---|
| `auth.html` | Login and registration | Split hero, one form, in-page switch, password reveal |
| `dashboard.html` | Everything needing attention | "Needs your response" hero match, "Also needs attention", "Your active reports" (max 3), collapsible history, four counters, draft banner |
| `reports.html` | Find an old report | Search box, status filter, kind filter, data table, pagination at 10 |
| `report.html` | One report | ID badge, title, public fields, matches list, activity log, Edit button |
| `match.html` | Decide on a match | Lost panel, Found panel, score breakdown, state-dependent action area, contact block |
| `wizard.html` | File or edit a report | Step rail, one form, per-step heading, action row |
| `management.html` | Staff moderation | Report list with Close and Remove buttons |
| `resume_draft.html` | Unfinished draft | Continue link, "Fill a new one" POST button |
| `closed_notice.html` | Scanned a dead report | Static notice |
| `base.html` | Shell | Sidebar, topbar, account strip, message loop |

**The dashboard is the screen to redesign first.** It carries four separate concerns in 210
lines: a single hero match that needs a response, a list of secondary matches, the three most
recent active reports, and a collapsible full history. It also contains the only forms on the
page, a `reject` POST inside the hero card (`dashboard.html:97-99`).

**Sidebar nav is conditional.** "Dashboard" renders only when the user has at least one visible
report, and "My reports" only when they have more than one (`base.html:34-39`). A user with
exactly one report sees a two-item sidebar. Any redesign that hardcodes three or four nav items
changes behaviour that the unit tests assert on.

## 9. The wizard

One view serves five steps. The template branches on `step`; there are no separate step views.

| Step | Form class | Fields | Template branch |
|---|---|---|---|
| 1 | `TypeForm` | `kind` (radio Lost/Found), `title`, `category`, `event_date` | default |
| 2 | `DetailsForm` | `description` (textarea), `contact` | adds `#privacy-hint` |
| 3 | `LocationForm` | `location`, `lat`, `lng`, `location_detail` | injects the map |
| 4 | `MatchingForm` | dynamic, from `schema()` in `core/forms.py:143` | adds refresh button |
| 5 | none | review only, POST publishes | renders a `<dl>` |

**Step gates.** `core/views.py:145-152` refuses to render a step whose inputs are absent and
redirects back one step. Editing a report whose `status` is not `Open`, or which is `reserved`,
redirects to the report page with an error (`core/views.py:137-139`).

**The questionnaire is dynamic.** `schema()` in `core/forms.py:143` builds step 4's fields from
the chosen `category` and the current selection. A wallet with contents selected grows a
sub-question per bank card, capped at five (`core/forms.py:165-174`). Changing "Visible logo?"
to Yes adds a "Logo name" field. The conditional field set is data-driven, so a redesign cannot
hardcode a fixed step-4 layout.

**The refresh round-trip.** When a selection changes, `app.js:10-19` submits the form with
`action=refresh` and `formnovalidate`. The view re-renders step 4 unvalidated from the posted
selection (`core/views.py:164-165`). The refresh button is hidden by JS, so without JavaScript
step 4 submits an ordinary save. This is the one place the wizard depends on a full page load
mid-step, and it is invisible to the user. If a redesign makes step 4 dynamic on the client, the
`schema()` function in `core/forms.py` becomes a duplicate source of truth and must be deleted
or shared.

**Date formats.** `event_date` is typed `DD-MM-YYYY` with a real `<input type="date">` behind
`DateInput`, validated to the range 2000 to today (`core/forms.py:114-120`). The meeting time
is typed as **free text** in the format `DD-MM-YY hh:mm AM/PM`, deliberately, so the browser
cannot supply a US-ordered date field. `MEETING_TIME_PATTERN` in `core/forms.py:224` is the
single source of truth, shared by the widget's `pattern` attribute, the server validator, and
the JS formatter. `core/tests.py:395` asserts day, month, and hour all require two digits,
because an earlier version accepted a single digit in one place and not another. A redesign
that swaps the text input for `<input type="datetime-local">` will break that test and the
Pakistan-time intent.

**Changing category clears the private answers.** `core/views.py:170-171` drops `data["answers"]`
when step 1's category changes, because the old answers no longer match the new schema. A user
who goes back and changes category silently loses their private questionnaire. There is no
warning. This is a genuine UX defect and a good candidate for the overhaul.

## 10. Location: three inputs, one source of truth

The same two stored values, `Report.lat` and `Report.lng`, are written by three controls on
step 3:

| Control | Behaviour |
|---|---|
| Leaflet map click | `app.js:77-80` places a draggable pin and writes both inputs to 6 decimal places |
| Pin drag | `app.js:72` updates the inputs live while dragging, not on drop |
| "Use my location" button | `app.js:84-89` calls `navigator.geolocation`, then pans and pins |
| The `lat` and `lng` number inputs | Typed directly by the user |

The status line under the map (`[data-map-status]`) narrates which control was used last. The
geolocation error handler distinguishes denied, unavailable, and timeout, because a desktop
with no provider cannot be fixed by changing browser settings (`app.js:95-99`).

**A pin is never placed at the default centre.** With no saved coordinates the map is centred
on Karachi at zoom 13 and shows no marker, because a pin at the default would read as a chosen
location (`app.js:56-58`, `app.js:50`). The map default is `24.8607, 67.0011` at zoom 13, or
zoom 15 when a pin exists.

**The marker path is patched in JS.** Leaflet's built-in heuristic returns a CSS-relative path
that the browser then resolves against the page, which 404s at `/drafts/<pk>/`. `app.js:41-42`
rewrites `L.Icon.Default.imagePath` from the `leaflet.css` href. If a redesign drops that patch
while keeping `/drafts/<pk>/` as the URL, the pin disappears on every draft page. The map is
untested, so nothing will catch it.

**QR seeding deliberately drops coordinates.** When a finder scans a lost report's QR,
`report_found` copies `kind`, `category`, `title`, `location`, and today's date into a new
draft, and explicitly deletes `lat`, `lng`, `description`, `location_detail`, `contact`, and
`answers` (`core/views.py:284-285`). The reason is given in the comment: the owner's drop point
is not the finder's recovery point, and carrying it over would hand the pair 20 free match
points for a position nobody independently observed. The finder lands on step 3 with the map
empty. This is correct and must survive a redesign.

## 11. Matching

`core/services.py:50-85`. Maximum 100 points, stored on `Match.score` with a per-component
`breakdown` dict.

| Component | Max | Rule |
|---|---|---|
| Category | 20 | Awarded outright if equal; pairing requires it anyway |
| Location | 20 | Haversine bands: under 0.5 km gives 20, under 1 km 15, under 2 km 10, under 5 km 5, beyond that 0 |
| Date | 15 | Same day 15, one day apart 10, up to 3 days 5, beyond 0 |
| Description | 15 | Jaccard similarity of word tokens, minus a 13-word stop list (`services.py:72`) |
| Private | 30 | Agreed non-trivial answers over total keys, compared casefolded |

**Gating.** A pair is stored only when the score is 70 or more **and** at least 2 private answers
agree (`core/services.py:85`). Both conditions, not either.

**What counts as evidence.** `contents`, `bank_count`, and `logo` are excluded, and any key
starting with `bank_` is excluded from key comparison. Values that are empty, `"None"`,
`"Other"`, `"Not provided"`, `[]`, or `"No"` are dropped before comparison
(`core/services.py:53-56`). Bank cards are compared as a set of `(issuer, suffix)` pairs, so
entry order does not affect the score (`core/services.py:61-68`, tested at `core/tests.py:355`).

**Recalculation is destructive.** `recalculate` deletes every `Possible Match` touching the
report, then rescans candidates (`core/services.py:87-99`). Publishing a report or editing one
rescores the neighbourhood. Scores are never stale; they are also never historical, so a redesign
must not present a score as a record of the past.

**Candidate scan is unindexed.** It filters on `category`, `status`, and `reserved` only
(`core/services.py:89`). There is no geospatial prefilter, so scoring is O(open reports) per
publish. Fine at campus scale, worth knowing before the dataset grows.

### Match state machine

`core/services.py:118-168`. Every transition is a POST with `action` in the form, validated
server-side, and every transition writes an `Event` on both reports.

| From | Action | To | Guard |
|---|---|---|---|
| `Possible Match` | `propose` | `Handover Proposed` | Not already reserved, meeting place and future time supplied; sets `reserved` on both reports |
| `Handover Proposed` | `accept` | `Handover Scheduled` | Only the non-proposer may accept; meeting not yet passed |
| `Possible Match` or `Handover Proposed` | `reject` | `Rejected` | Clears `reserved` if it was set; records `rejected_by` |
| `Rejected` | `restore` | `Possible Match` | Only the dismissing user; not reserved; rescore must still pass |
| `Handover Scheduled` | `returned` | `Returned` | Meeting time must have passed; sets both reports `Returned` and rejects sibling matches |

Any other combination raises "That action is unavailable in this state." **The UI must render
the action set from `match.state`, not from guesswork.** The template already branches on it
(`match.html:76-118`), and the browser cannot know the current time relative to `meeting_at`,
so the "Confirm item returned" button must stay server-gated. `core/tests.py:514` covers a
`Possible Match` that is parked while reserved and becomes usable again after.

**Dashboard ordering is a computed priority,** not creation order: your own proposal first
(order 2), then scheduled (1), then other proposals (0), then plain possible matches (3)
(`core/views.py:66-74`). Matches where either report is `reserved` are excluded from the
dashboard entirely while the reservation holds.

## 12. Privacy and access rules

These are constraints on the redesign, not suggestions. They come from `AGENTS.md` and are
enforced in code.

- **Private answers are never rendered** in the match screen or the management screen. The
  match screen shows the two public reports side by side and a score breakdown, never
  `Report.answers`. The management screen never shows them either.
- **`Report`, `Draft`, `Match`, and `Event` are absent from Django admin.** `core/admin.py`
  registers `User` only. Keep it that way; adding a report admin would expose private answers
  to any staff account and bypass the template-level privacy work entirely.
- **Contact details unlock at `Handover Scheduled` only,** via the `contacts` context flag
  (`core/views.py:242`). Not at `Possible Match`, not at `Handover Proposed`.
- **Public fields reject identifiers outright** rather than redacting them. `public_short` and
  `public_text` in `core/forms.py:67-76` run 10 regexes over phone numbers, emails, CNIC in two
  formats, roll numbers, IBAN and account phrasing, and "last 4 digits 1234". A user who
  types an email into the description is **rejected**, and the error tells them to move it into
  the private questions. Do not soften this into a warning; `core/tests.py:103` asserts the
  draft survives a rejected submission.
- **Public fields also reject invisible Unicode.** `BAD_CHARS` in `core/forms.py:32` blocks C0
  and C1 controls, zero-width characters, all bidi embedding and isolate marks, and the BOM.
  The reason is in the comment: these exist to hide text from a screen reader or to reorder a
  name after the fact. A redesign that adds a rich-text editor or an emoji picker on a public
  field will trip this, and the test at `core/tests.py:79` covers it.
- **`db.sqlite3` holds the private answers** and is gitignored. Do not commit it.

## 13. Server and browser contract

Every piece of client behaviour, and the server state it touches. This is the section to check
whenever you change a template.

| Behaviour | Source | Reads | Writes | Server counterpart |
|---|---|---|---|---|
| Strip non-digits from `input[inputmode="numeric"]` | `app.js:3-5` | any numeric-marked input | strips in place | `forms.suffix()` uses `PasswordInput` with `inputmode=numeric` (`forms.py:150-152`) |
| Mark a field on native validation failure | `app.js:6-9` | `invalid` event, capture phase | adds `.has-error` to closest `.field` | Django's own error markup in `wizard.html:53-55` |
| Auto-refresh step 4 on selection change | `app.js:10-19` | `contents`, `bank_count`, `logo`, `card_type` | submits `action=refresh`, `formnovalidate` | `views.wizard:164-165` re-renders unvalidated |
| Live privacy warning on the description | `app.js:20-31` | `description` | sets `#privacy-hint` text and `setCustomValidity` | mirrors but does not replace `public_text` |
| Map pin, drag, geolocation | `app.js:34-105` | `#id_lat`, `#id_lng` | both inputs, 6 dp, plus status text | `LocationForm`, `views.report_found:284` |
| Meeting time formatting and validation | `app.js:107-155` | `meeting_at` | reformats, sets `setCustomValidity`, shows a `role=alert` paragraph | `MeetingForm` and `MEETING_TIME_PATTERN` (`forms.py:224`) |
| Confirm before dismissing a match | `app.js:157-171` | `[data-reject-match]`, `[data-restore-match]` | blocks submit on cancel | `services.transition` guards regardless |
| Mobile sidebar open and close | `app.js:173-193` | `[data-sidebar-toggle]`, `[data-sidebar-close]` | toggles `body.sidebar-open`, sets `aria-expanded` | none, purely presentational |
| Collapsible report history | `app.js:195-202` | `[data-reports-toggle]` | toggles `.open`, sets `aria-expanded` | none |
| Password reveal | `auth.js` | `[data-password-toggle]` | swaps `input.type`, updates label and `aria-pressed` | none |

**Rules that fall out of this table.** Never add a `name` to a numeric input that is not meant
to be digits only. Never rely on a JS-only validation, because the server runs its own and the
two must agree; the meeting time pattern is the documented case where they drifted. Never add
an element that JS selects by a hardcoded ID without also handling its absence, since every
block in `app.js` is already guarded and a new one must be too. `app.js` is loaded on every
authenticated page from `base.html:93` with `defer`, and on the login page too, so it must stay
safe when nothing it looks for exists.

**Cache busting is manual.** `base.html` appends `?v=24` to `app.css` and `?v=17` to `app.js`;
`auth.html` uses `?v=3` and `?v=1`. Bumping a file without bumping its query string serves the
cached copy during development.

## 14. The current design system

There is not much of one, which is the opportunity.

**`app.css` defines 17 custom properties** in `:root`: `--bg`, `--panel`, `--panel-soft`,
`--line`, `--line-soft`, `--text`, `--muted`, `--blue`, `--blue-soft`, `--blue-line`,
`--green`, `--green-soft`, `--amber`, `--amber-soft`, `--red`, `--red-soft`, `--shadow`. A
light theme only. Blue `#0b63d8` is the primary, green and amber and red are semantic only.

**The main app has no type system.** `app.css` contains exactly one `font-family` declaration,
a monospace stack, used for one element. Everything else renders in the browser default serif
or sans. The four font files in `static/fonts/` are referenced only by `auth.css`, which
carries the only `@font-face` rules in the project, so **Fraunces and Inter load on the login
and registration pages and nowhere else.** A redesign that wants a consistent typeface has to
load the fonts in `base.html` or move the `@font-face` block into `app.css`. Note the two
licence files, `Fraunces-OFL.txt` and `Inter-OFL.txt`, must travel with them.

**Breakpoints are at 900, 700 (twice), and 640 px.** At 700 px the sidebar becomes an
off-canvas drawer opened by the mobile bar button in `base.html:13-19`. There is no dark mode,
no `prefers-reduced-motion` handling, and no `prefers-color-scheme` support.

**Accessibility already present,** worth preserving: `role=status` on messages and the privacy
hint, `role=alert` on the field error and the meeting error, `aria-expanded` on all three
disclosure controls, `aria-controls` wiring the sidebar and the history toggle, `aria-label` on
the icon-only controls, and a skip-free but landmark-structured page with `<aside>`, `<header>`,
`<nav>`, and `<main>`.

**Vendored assets.** Leaflet 1.9.4 under BSD-2-Clause, with `static/leaflet-LICENSE`. The five
sprites in `static/images/` are Leaflet's own. `static/login-campus.png` is the only project
image, used by `auth.css`. Do not edit vendored files.

## 15. Test coverage by screen

65 methods, 63 executed without Playwright.

| Screen | Unit coverage | Browser coverage |
|---|---|---|
| Login and registration | `tests.py:146`, `tests.py:191`, `tests.py:235` | `test_browser.py:11` checks computed fonts, contrast, ARIA, mobile drawer |
| Dashboard | `tests.py:172`, `tests.py:185`, `tests.py:206`, `tests.py:225` | none |
| Wizard | `tests.py:103`, `tests.py:154`, `tests.py:116`, `tests.py:311`, `tests.py:338`, `tests.py:344` | `test_browser.py:60` covers the wallet flow at 1440 and 390 px |
| Report detail and editing | `tests.py:467`, `tests.py:473`, `tests.py:311`, `tests.py:320` | none |
| Match and handover | `tests.py:269`, `tests.py:278`, `tests.py:362`, `tests.py:374`, `tests.py:514`, `tests.py:325` | none |
| Reports history and filters | `tests.py:296` | none |
| Management | `tests.py:296` | none |
| QR flow | `tests.py:461`, `tests.py:486`, `tests.py:498`, `tests.py:534`, `tests.py:553` | none |
| All form boundaries | `test_screening.py`, 17 methods, no database | none |
| **Leaflet map on step 3** | **none** | **none** |

**Two blind spots to watch.** The map has no coverage at all, so the marker-path patch and the
tile layer can both break silently. And only two screens are covered in a real browser, so
layout regressions anywhere else reach production unseen.

**A redesign will break tests,** and that is expected. `core/tests.py` asserts on rendered
text, on which nav links appear given a report count, on the exact set of POST actions, and on
privacy. `core/test_screening.py` sweeps every field against codepoint ranges. Budget for
reading the failure and deciding whether the test or the design is wrong. Do not delete a test
to make a build pass.

## 16. Defects and gaps found while reading

Real issues, in rough priority order for a redesign.

1. **The post-submit jump is broken.** `views.py:196` redirects to
   `dashboard?new=<pk>#report-<pk>`, but no template reads `request.GET`, and `dashboard.html`
   emits no `id="report-<pk>"`. The only `id` in the file is `historyBody`. The user lands at
   the top of the dashboard with a success message and no way to see the report they just
   submitted. Either add the anchor and a highlight, or drop the fragment.
2. **Changing category silently destroys the private questionnaire.**
   `views.py:170-171`. No warning, no confirmation.
3. **Error messages are generic on wizard fields.** `wizard.html:53-55` renders the fixed string
   "Invalid input. Please enter a correct value." for every field error, discarding the specific
   validator message, which is usually the most useful text in the form. `PUBLIC_HINT` and the
   per-field hints in `forms.py` never reach the user.
4. **The dashboard is doing four jobs** in 210 lines, with a reject form nested inside a card.
5. **No password reset and no email verification.** No `EMAIL_BACKEND` is configured, so
   neither is possible without new infrastructure.
6. **No 404 or 500 template,** so a bad URL or an unhandled exception shows Django's debug page
   in development and nothing useful in production.
7. **`STATIC_ROOT` is not defined and neither is WhiteNoise.** With `DEBUG=1` by default,
   production static serving is unresolved. Any deploy needs this fixed.
8. **The map is untested** and depends on a JS patch, per section 10.
9. **The map sits outside its own field group.** `wizard.html:41-49` matches on
   `field.name == 'lat'` and injects the map *before* the loop reaches the lat field, so the
   map gets its own `.field` div with no label while the lat and lng inputs render separately
   at `wizard.html:50-59`. Visually the map is not attached to the coordinates it controls.
10. **No dark mode and no reduced-motion support.**

## 17. What a redesign must not do

- Do not render `Report.answers` outside the private questionnaire, and never on a public page.
- Do not register `Report`, `Draft`, `Match`, or `Event` in `core/admin.py`.
- Do not unlock contact details before `Handover Scheduled`.
- Do not change `MEETING_TIME_PATTERN`, the `event_date` format, or the score thresholds
  without reading `core/tests.py` and `core/test_screening.py` first. Those tests encode
  decisions, not accidents.
- Do not add autosave while typing.
- Do not edit `static/leaflet.*` or the Leaflet sprites. Extend around them.
- Do not commit `db.sqlite3`.
- Do not move `lat` and `lng` out of `Report`. The haversine scorer reads them directly
  (`services.py:19-22`).
- Do not replace the free-text meeting input with a locale-ordered date widget without
  understanding why it is free text.

## 18. Where to start

1. Fix the three cheapest defects: the dashboard anchor, the category-change warning, and the
   real field error messages in `wizard.html`.
2. Load the fonts properly. Move the `@font-face` block from `auth.css` into `app.css` and set
   `font-family` on `body`, so the whole app gets a type system.
3. Decide whether to keep the single-step-page wizard or make step 4 dynamic on the client. If
   client-side, delete `schema()` duplication and keep `core/forms.py` authoritative for
   validation.
4. Redesign the dashboard first, since it carries the most weight and has no browser test.
5. Add a browser test for the map before touching the map.
6. Only then consider a build step, a component library, or a dark theme. Each one is a real
   change to how the project is deployed, and each is easier to justify once the constraints in
   section 2 are settled.

## 19. Related documents

- `AGENTS.md` for the operating rules and the project conventions.
- `TODO-INCREMENTAL.md` for live task status, increments 3 and 4 are pending.
- `matching-architecture.md` for the scoring rules in prose, including the NED-only baseline.
- `report-wizard-flow.md` for the step-by-step field contract.
- `report-structure.md` for the report and match data contract.
- `osm-integration-guide.md` for the Leaflet and tile-layer setup.
- `docs/WIREFRAME-BRIEF.md` for the written spec of all screens, useful as wireframe input.
- `PROJECT_ESSENCE.md` for the project vision and the full delivery status.
