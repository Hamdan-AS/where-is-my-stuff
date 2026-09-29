# Where Is My Stuff? GPS Prototype — Karachi-wide Expansion

Course: CS-326 Software Engineering  
Environment: Karachi (GPS-enabled)  
Checkpoint: 12 September 2026  
Project directory: `/home/elite/sandbox/where-is-my-stuff-gps`  

**This is the GPS-enabled prototype branch. The original NED-only frozen project remains at `/home/elite/sandbox/where-is-my-stuff/`. The Django implementation in this folder is authoritative; the PHP files remain reference material.**

## Current status

This prototype extends the frozen NED-only project with GPS coordinates and haversine distance-based matching for expansion beyond campus to all of Karachi.

## Scope changes from frozen baseline

| Module | Frozen baseline | GPS prototype |
|---|---|---|
| Locations | Fixed NED campus dropdown (11 locations) | Latitude/longitude coordinates, any location worldwide |
| Location matching | Binary exact match (20 or 0) | Haversine distance bands: <0.5km→20, <1km→15, <2km→10, <5km→5, else→0 |
| Location entry | NED dropdown (11 fixed options) | Google Maps Places Autocomplete + geocoding writes lat/lng; manual coordinate entry remains as fallback |
| Handover location | ENUM: 'NED Security Office' or 'Department Office' | Free-form text (any safe meeting point) |
| Schema | `reports.location VARCHAR(100)` | `Report.lat` / `Report.lng` nullable on the Django model; handover location stored as free-form text |

## Frozen scope (still applies)

| Module | Agreed behaviour |
|---|---|
| Accounts | Registration, login, logout, password hashing, PHP sessions, and access checks. |
| Reports | Students create, view, and edit their own Lost and Found reports; Moderator/Admin users close or delete reports, subject to handover state. |
| Questionnaires | Both Lost and Found reporters complete the same applicable category-specific private fields. |
| Matching | Deterministic scoring, private answer comparison, same-user exclusion, haversine distance bands. |
| Dashboard | Report status, recovery status, and clickable match cards. |
| Handover | Either participant proposes any meeting location and time; the other accepts or rejects. |
| Contact sharing | Reveal saved contact details to the two participants only after both accept the handover. |
| Return | Either participant records the completed return after a handover is scheduled. |
| Moderator | Reviews reports, closes or deletes invalid reports; cannot assign roles. |
| Admin | Has Moderator access and can assign account roles. |

## Matching rules

A candidate must contain one Lost and one Found report, belong to different users, have the same category, and have both reports active. At least two private answers must agree, and the total must reach 70 points.

| Factor | Points |
|---|---:|
| Same category | 20 |
| Haversine distance: <0.5km / <1km / <2km / <5km / further | 20 / 15 / 10 / 5 / 0 |
| Date: same day / one day apart / two or three days apart / further apart | 15 / 10 / 5 / 0 |
| Description: shared meaningful words divided by all unique meaningful words, multiplied by 15 | 0–15 |
| Private questionnaire: equal answers share a normalized 30-point allocation | 0–30 |
| Maximum | 100 |

Private values compare after trimming and lowercasing. A match page may show the category-specific agreement count, but must not reveal the other person's answers. A score is a similarity suggestion, not a probability or proof of ownership.

Categories are Wallet / Purse, Cards / IDs, Keys, Electronics, Bag, Documents, Cash / Money, and Other. Wallet/Purse uses conditional logo and card-presence fields; other categories use their complete structured questionnaires. The Cards / IDs suffix field accepts only the last three CNIC digits or the last four NED/bank-card digits. Full identifiers must be rejected there.

The previous idea of showing private answers to the Finder is superseded. Both people now submit their own answers, and the server compares them privately.

## Handover and status rules

Report status is `Open`, `Closed`, or `Returned`. Recovery status belongs to the match:

```text
Possible Match -> Handover Proposed -> Handover Scheduled -> Returned
                          |
                          +-> Rejected
```

The proposal records any location and a date and time, and the proposer. Proposing counts as that participant's acceptance. Only the other participant can supply the second acceptance of the same proposal.

Finish enforcing these rules before the demo:

- A report cannot enter two handovers at once.
- A proposed or scheduled handover prevents report edits that would change the agreed item details.
- Closing a report cancels its active matches and handover consistently.
- Returning an item updates both reports and resolves competing matches.
- Direct requests from unrelated users cannot read private match details or change the workflow.

## Technology and database

Use Django 5.2, Python 3.10+, SQLite, and server-rendered templates (see AGENTS.md). No additional backend framework is required. Location entry uses the Google Maps Places Autocomplete API with geocoding to write lat/lng to the report; manual coordinate entry remains as fallback for users without the API. Haversine distance is computed server-side from stored coordinates; no map API is involved in scoring.

The Django data model (core app) contains `User`, `Report`, `Draft`, `Match`, and `Event`. It replaces the legacy PHP `claims`, `report_answers`, and `handovers` tables. `Report` carries nullable `lat`/`lng` for GPS coordinates. The handover location is free-form text.

## Saved coding progress

The file-level list below records the original PHP prototype changes. The Django port supersedes them; the PHP files remain reference material.

| File | Change |
|---|---|
| `database.sql` | Added `lat`/`lng` to `reports`, changed `handovers.location` to VARCHAR(255) |
| `functions.php` | Removed `NED_LOCATIONS`/`HANDOVER_LOCATIONS`, added `haversine_score()`, updated `validate_report()` with lat/lng validation |
| `matching.php` | Replaced binary location score with `haversine_score()` distance bands |
| `report_form.php` | Replaced NED location dropdown with lat/lng text inputs |
| `workflow.php` | Removed `HANDOVER_LOCATIONS` check, added lat/lng to INSERT/UPDATE |
| `match.php` | Replaced handover ENUM dropdown with text input |
| `index.php` | Show lat/lng in match cards and report list |
| `reports.php` | Added `lat`/`lng` to draft save fields |
| `scope-freeze.md` | Updated to reflect GPS prototype scope |

## Resume order

1. [done] Extend matching with haversine distance bands and GPS schema
2. [done] Replace NED location constraints with coordinate inputs
3. [done] Generalize handover locations from ENUM to free-form text
4. [deferred] Port haversine scoring, lat/lng fields, and location entry to the Django codebase
5. [pending] Wire Google Places Autocomplete + geocoding into Django report entry (manual fallback must stay)
6. [pending] Run scoring tests, Django checks, and an isolated two-user workflow test
7. [pending] Complete browser verification and record actual test results

## Completion evidence for CS-326

Keep requirements and acceptance criteria, database and state diagrams, a module map, the incremental plan, risk records, test results, defect fixes, and a maintenance/change log. Record actual results; do not claim that a saved file or a high match score demonstrates correctness.

The release check must include unauthorized report edits, same-user exclusion, invalid category answers and identifier suffixes, score boundaries, private-answer visibility, role restrictions, duplicate handover prevention, rejection, and a complete two-user return.

## Outside this scope

No runtime LLM, image matching, chat, notifications, QR/NFC, mobile app, or second backend stack. Google Maps is used only for Places Autocomplete and geocoding at location entry; scoring never calls an external API. Map display (Leaflet.js) is optional and deferred. Any later scope change needs a reason, affected requirements, effort estimate, and test impact recorded before implementation.

## Incremental UI update — 8 September 2026

The light four-screen wireframe is the current UI reference. It is retained as `ui-wireframes-redesign.png`, with `ui-wireframes-redesign.backup.png` preserved as a rollback copy. The report-form increment now uses the reference's Lost/Found control, four-step progress header, grouped report details, and privacy-aware matching section. Wallet/Purse reports use the latest contents checklist, item-detail accordion, and report-decision wizard. Photo upload and true separate child-report creation are deliberately deferred and are not represented as working features.
