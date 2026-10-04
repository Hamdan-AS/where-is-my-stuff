# Report feature: current structure

Reference for the lost-and-found Report entity and the machinery around it. Describes the code as it stands today, after the Leaflet and OpenStreetMap picker replaced the dormant Google Maps one.

Verified against `core/models.py`, `core/forms.py`, `core/views.py`, `core/services.py`, `core/qr.py`, `config/settings.py`, `config/urls.py`, all templates, `static/app.js`, and the three test classes in `core/tests.py`. `manage.py test core` discovers 65 test methods: 46 here, 17 in `core/test_screening.py`, 2 in `core/test_browser.py`. No migration drift.

## 1. The Report model

`core/models.py:13`. One row per lost or found item.

| Field | Type | Notes |
|---|---|---|
| `public_id` | UUID, unique, indexed | Not editable. Used in the QR URL so the id is unguessable. Backfilled in migration `0003`. |
| `owner` | FK to `core.User`, `PROTECT` | The reporter. A user cannot be deleted while owning reports. |
| `kind` | Char(5) | `Lost` or `Found`. No DB-level constraint. |
| `title` | Char(120) | Public. Screened for identifiers. |
| `category` | Char(40) | Drives the private question schema. |
| `description` | Text | Public. Screened for identifiers. |
| `location` | Char(80) | Public place name. Required. |
| `lat` | Decimal(10, 8), null | Added in migration `0004_gps_coordinates`. |
| `lng` | Decimal(11, 8), null | Added in migration `0004_gps_coordinates`. |
| `location_detail` | Char(255) | Free-text precise location. Required. |
| `event_date` | Date | When the item was lost or found, not when it was reported. |
| `contact` | Char(120) | Released only after both parties accept a handover. |
| `answers` | JSON | Private matching answers. Never rendered publicly. |
| `status` | Char(10), default `Open` | `Open`, `Returned`, `Closed`, `Removed`. Not a choices field. |
| `reserved` | Bool | Set during a handover, which locks editing. |
| `created_at` | DateTime, auto | |

`display_id` (`models.py:33`) is a property, not a column: `LFD-001` for Lost, `FND-002` for Found, derived from the primary key.

`Removed` is the soft delete. It is filtered out of the dashboard, report history, and management list rather than deleted, so `PROTECT` on the owner foreign key and on `Match.lost` / `Match.found` can do their job.

## 2. Supporting models

**Draft** (`models.py:38`). `owner` FK, optional `report` FK, `data` JSON, `updated_at`. A draft with a null `report` is an unsubmitted report in progress. The design allows one such draft per owner in practice, enforced in the view rather than by a constraint.

**Match** (`models.py:44`). `lost` and `found` FKs, `score`, `breakdown` JSON, `state`, `proposer`, `rejected_by`, `meeting_place`, `meeting_at`. Two constraints: `unique_pair` on `(lost, found)` and `score_maximum` on `score <= 100`.

**Event** (`models.py:65`). Append-only activity log rendered on the report detail page. One row per state change, moderation action, and match transition.

## 3. Draft lifecycle and the five-step wizard

One view, `core/views.py:126` `wizard(request, pk=None)`, serves all five steps.

| Step | Form | Contents |
|---|---|---|
| 1 | `TypeForm` | kind, title, category, event_date |
| 2 | `DetailsForm` | description, contact |
| 3 | `LocationForm` | location, lat, lng, location_detail, plus the map picker |
| 4 | `MatchingForm` | private answers, schema generated from category |
| 5 | none | Review, then submit |

A `GET` to `/reports/new/` with no `pk` looks for an existing owner-less draft. If one exists it renders `resume_draft.html` offering continue or discard. Otherwise it creates an empty draft and redirects to `/drafts/<pk>/`.

Each step POST validates, merges `cleaned_data` into `draft.data`, saves, and redirects to `step + 1`. Two storage-boundary conversions happen: `event_date` becomes an ISO string (views.py:168) and `lat` / `lng` become strings (views.py:175-178) so the JSON stays serialisable.

Step guards (views.py:146-151) bounce a user back if they deep-link forward past data they have not entered. Changing `category` on step 1 discards the private answers, because the question schema is category-specific.

Editing an existing report (`views.py:209` `edit_report`) snapshots the current row into a draft bound to that report, then redirects into the same wizard. The edit path is refused when the report is not `Open` or is `reserved`.

**Publishing** is `services.publish` (`services.py:101`), wrapped in `transaction.atomic`. It calls `validated()`, which re-runs `TypeForm`, `DetailsForm`, and `MatchingForm` against the *entire* stored draft rather than trusting what each step validated. Only then does it create or update the `Report`, write an `Event`, run `recalculate`, and delete the draft.

This has a consequence worth knowing: because `validated()` runs `DetailsForm` over the whole data dict, `lat` and `lng` are **required to publish a report**. There is no way to submit without coordinates today.

## 4. Location and the map picker

Coordinates flow one way. Django serialises them into the page, Leaflet reads the form inputs and writes them, the form POSTs, the values land on the row.

The picker lives in the wizard at step 3, its own step, rendered just above the `lat` field, keyed on `{% if field.name == 'lat' %}` (`templates/wizard.html:41`). Markup is three elements: a map container, a "Use my location" button, and a status line.

Behaviour, all in `static/app.js:34-79`:

- Leaflet 1.9.4, vendored at `static/leaflet.js` and `static/leaflet.css`, BSD-2-Clause, loaded with `defer` from a `{% block head %}` that `base.html` now provides. Because both it and `app.js` are deferred and it appears earlier in the document, `L` is defined before the picker code runs.
- Tile layer is `https://tile.openstreetmap.de/{z}/{x}/{y}.png` at `maxZoom: 18`, with the required visible OpenStreetMap attribution. Not `tile.openstreetmap.org`, which returns 403 for every tile under the OSM tile usage policy. `static/app.js:52`.
- No saved coordinates means the map centres on Karachi at zoom 13. Saved coordinates mean it centres on them at zoom 15 and the status line reads "Pin loaded from your saved draft."
- Clicking the map moves the marker and writes both inputs to 6 decimal places. Dragging the marker does the same on `dragend`.
- "Use my location" calls `navigator.geolocation.getCurrentPosition`, recentres at zoom 15, and writes the inputs. The button is hidden entirely when the browser has no geolocation API.
- The Latitude and Longitude inputs stay visible and editable, which keeps a keyboard and non-pointer path and keeps them usable if tiles fail to load.

There is no place search. The previous Google implementation used Places Autocomplete, which fires a request per keystroke; Nominatim forbids that, so the box was dropped rather than ported. The cost is that a user who does not know their coordinates must pan and zoom to find the spot.

`Draft.data` already carries `lat` and `lng`, so drafts survive a page reload mid-wizard without any schema work.

## 5. Matching

`services.py:50` `score(left, right)`. Returns `(total, breakdown)` or `None`.

Eligibility gates, all required: different owners, same category, `left.kind == "Lost"`, `right.kind == "Found"`, both `status == "Open"`.

| Component | Max | Rule |
|---|---|---|
| Category | 20 | All or nothing. |
| Location | 20 | Haversine bands in `location_score` (`services.py:19`): under 0.5 km = 20, under 1 km = 15, under 2 km = 10, under 5 km = 5, beyond = 0. Returns 0 if either report is missing coordinates. |
| Date | 15 | Same day 15, one day 10, within three days 5. |
| Description | 15 | Jaccard overlap of word tokens, stop words removed. |
| Private | 30 | Agreement ratio across private answers. |

A pair only becomes a match when it scores 70 or more **and** agrees on at least 2 private answers. Both conditions are enforced at `services.py:85`.

Two details in the private scoring. Values that are empty, `"None"`, `"Other"`, `"No"`, or empty lists are dropped before comparison, so leaving a field blank does not count as a disagreement. Bank cards are compared as a set of `(issuer, last-4)` pairs, independent of the order the user entered them in, so a two-card wallet scores the same either way.

`recalculate` (`services.py:87`) deletes this report's `Possible Match` rows and rescores it against every open candidate. It runs only from `publish`. Existing `Match` rows keep their stored `score` and `breakdown` until the report is republished, so a change to the scoring code does not retroactively update the database.

## 6. Handover state machine

`services.transition` (`services.py:118`). Every branch is a `Match.state` transition, and every one writes an `Event` to both reports.

```
Possible Match --propose--> Handover Proposed --accept--> Handover Scheduled
        |                            |                            |
        +-- reject ---> Rejected <--+                            |
                                    +-- restore --> Possible Match
```

`--returned--` from `Handover Scheduled` sets both reports to `Returned` and rejects every other `Possible Match` on them. It is refused before `meeting_at` has passed.

`propose` sets `reserved` on both reports, which is what locks editing. Only one handover can hold a report at a time: proposing while either report is already reserved raises. A `Possible Match` on a reserved report stays in the database but is hidden from the dashboard and excluded from counts, so it becomes actionable again if the handover is rejected.

`Rejected` matches can only be restored by the user who rejected them, and only if the score still qualifies.

## 7. QR scan flow

`core/qr.py` renders the QR with error correction level M. It encodes the absolute URL of `report-found`, which is `/r/<public_id>/found/`.

The QR image view (`views.py:256`) is **not** login-protected. That is deliberate, the image has to be printable, and it leaks nothing beyond the UUID already encoded in the URL.

`report_found` (`views.py:262`) is login-protected and then:

1. Refuses if the scanner owns the report, redirecting to it with an info message.
2. Refuses if the report is not `Open` or is reserved, rendering `closed_notice.html`.
3. Otherwise gets or creates the scanner's single owner-less draft and merges in `kind: Found`, `category`, `title`, `location`, and today's date.
4. Pops `description`, `location_detail`, `contact`, `answers`, `lat`, and `lng` so the scanner cannot publish Lost-flavoured text or the owner's drop point as Found attributes.
5. Redirects to wizard step 3, the Location step, since that is where the finder must place the pin.

The QR box only renders on Lost reports (`templates/report.html:24`).

The place name is deliberately kept as a coarse hint the finder can confirm, while the exact coordinates are cleared. `location_detail` and `lat`/`lng` are the same class of field: something only the finder can supply. Carrying the coordinates over would publish the owner's drop point as the finder's, and would hand `location_score` a full 20 for a position nobody independently observed. Covered by `test_scan_does_not_copy_lost_coordinates`.

## 8. Who can see what

| Surface | Access |
|---|---|
| Dashboard | Own reports only. |
| My reports history | Own only. Search on title and location, 10 per page. |
| Report detail | Own only, `get_object_or_404(Report, pk, owner=request.user)`. |
| Match detail | Either participant, filtered on `lost__owner` or `found__owner`. Contact is shown only in `Handover Scheduled` and `Returned`. |
| Management | `is_staff`, raises `PermissionDenied` otherwise. |
| Report found via QR | Any logged-in user with the UUID. |
| Report QR image | Unauthenticated, by design. |
| Django admin | Only `User`. `Report`, `Draft`, `Match`, and `Event` are deliberately unregistered, see `core/admin.py:5`. |

There is no page on which one user sees another user's report, other than a match they are part of. Any browse or map view of other people's reports would be a new disclosure surface and needs a decision, not just a template.

Two hard constraints hold across all of the above: private matching answers are never rendered in match or management views, and reports, answers, drafts, and matches are absent from the admin.

## 9. URL map

`config/urls.py`.

| Path | View | Name |
|---|---|---|
| `/` | `dashboard` | `dashboard` |
| `/reports/` | `report_history` | `reports` |
| `/reports/new/` | `wizard` | `create` |
| `/drafts/<pk>/` | `wizard` | `draft` |
| `/reports/<pk>/` | `report_detail` | `report` |
| `/reports/<pk>/edit/` | `edit_report` | `edit` |
| `/matches/<pk>/` | `match_detail` | `match` |
| `/r/<uuid>/qr/` | `report_qr_image` | `report-qr` |
| `/r/<uuid>/found/` | `report_found` | `report-found` |
| `/management/` | `management` | `management` |
| `/login/`, `/register/`, `/logout/` | auth | `login`, `register`, `logout` |

## 10. Cross-cutting validation

`core/forms.py` is the only place public text is screened. `IDENTIFIER_PATTERNS` rejects emails, obfuscated emails, spaced or dashed digit runs, bare 7-to-11 digit runs, CNIC formats, roll numbers, IBAN and card references, and "last 4 digits" phrasing. `BAD_CHARS` strips control characters and zero-width and bidirectional Unicode marks, which exist mainly to hide identifiers from the screen.

The rule is reject, never rewrite. The owner is told to move the value into the private questions instead. The wizard description step also runs a lighter live check in `app.js` that flags likely identifiers as the user types and blocks submission, but the server-side check is the one that matters.

## 11. Platform facts

- Django 5.2, SQLite, server-rendered templates, no REST API, no frontend build.
- `AUTH_USER_MODEL = "core.User"`, email-based login, usernames are set to the lowercased email.
- `TIME_ZONE = "Asia/Karachi"`, `USE_TZ = True`. Meeting times are entered as `%d-%m-%y %I:%M %p` and normalised to aware datetimes.
- SQLite runs in `IMMEDIATE` transaction mode with a 20-second timeout, which serialises writes.
- `SECRET_KEY` and `DEBUG` come from the environment, both defaulting to development values.
- Static assets are served from `static/` with `?v=` cache-busters, currently `app.css?v=20` and `app.js?v=12`.

## 12. Test coverage

42 tests in three classes, all with the MD5 password hasher substituted for speed.

**`PublicFieldScreeningTests`**, 10 tests. Identifier rejection across every public field, obfuscation variants, unicode acceptance, size boundaries, control characters, and a wizard-level test that a leaky description is rejected while the draft survives.

**`FlowTests`**, 24 tests. Registration and login, the full wizard through single publication, draft resume and discard, remember-me, dashboard filtering, the category-dependent wallet question schema, score eligibility and bounds, a complete handover, access and management permissions, draft ownership, CSRF, competing handovers and locked edit, category change clearing stale answers, XSS escaping on the review step, bank card order independence, recalculation, dismiss-and-restore rules, the Pakistan meeting date format, and the haversine distance bands.

**`QRScanTests`**, 8 tests. QR rendering and content type, login requirement on the scan, draft seeding, self-scan refusal, the Lost-only QR box, scan into an occupied draft clearing stale fields, and closed or reserved notices.

Two browser tests in `core/test_browser.py` drive Chrome through Playwright and are skipped unless it is installed. They cover the login and registration screens and the full wallet wizard.

## 13. Known inconsistencies and open work

**Raw coordinates leak into the UI as decimal text.** `dashboard.html:52,58,68,74`, `match.html:32,50`, and the wizard review step at `wizard.html:90` all print `24.8607, 67.0011` inline, while `report.html:20` shows no coordinates at all. Now that a map exists, the raw numbers are redundant on the first three and their absence on the fourth is inconsistent.

**No test exercises the map.** Every test either types into `#id_lat` directly or never reaches the picker. If Leaflet failed to load, or the click handler stopped writing the inputs, the suite would still pass. A Playwright test that clicks the map and asserts the inputs changed would close this.

**The QR coordinate copy is still live.** See section 7.

**There is no browse or map view.** No page lists reports from multiple owners. Any such page changes the disclosure surface described in section 8.

**Version control.** The repository had no tracked files when this was written. A git repository was created on 29-09-2026; the pre-cleanup state is commit `54fa6fc`.

**Map deployment follow-up.** Increment 4 still needs a content security policy allowing `img-src` and `connect-src` for the tile host, and a keyed provider such as MapTiler or Stadia Maps, or self-hosted tiles, before deployment. `tile.openstreetmap.de` is a volunteer community server not sized for real traffic.
