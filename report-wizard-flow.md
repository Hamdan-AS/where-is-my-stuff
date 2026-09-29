# Report wizard: step-by-step flow checklist

Reflects the current implementation: 5-step wizard, Leaflet + OpenStreetMap location picker, one `wizard()` view serving all steps. GPS (browser Geolocation API) is one of three ways to set `Report.lat/lng`. All three write to the same fields, no separate GPS columns, so the Report data model stays single-source-of-truth for location.

Checked against the source on 26-09-2026. Boxes marked `[x]` are implemented and verified by reading the code, by `manage.py check`, and by the test suite (`manage.py test core`, over 47 tests).

## Entry point

- [x] `GET /reports/new/` with no `pk`
- [x] Owner-less draft exists -> render `resume_draft.html` offering Continue or "Fill a new one". The second option deletes the draft and posts a "Previous draft discarded" message, so it is destructive despite the label.
- [x] No draft exists -> create empty draft -> redirect to `/drafts/<pk>/`
- [x] Editing an existing report (`edit_report`) snapshots the current row into a new draft, redirects into the same wizard
- [x] Edit path refused if the report is not `Open` or is `reserved`

## Step 1: Type

Form: `TypeForm`

- [x] Select `kind`: Lost or Found
- [x] Enter `title` (public, identifier-screened)
- [x] Select `category` (drives the step 4 question schema)
- [x] Enter `event_date`
- [x] Changing `category` after it was already set discards any private answers already entered in step 4
- [x] POST validates: `event_date` converted to an ISO string at the storage boundary, merges `cleaned_data` into `draft.data`, saves, redirects to step 2

## Step 2: Item details

Form: `DetailsForm`

- [x] Enter `description` (public, identifier-screened)
- [x] Enter `contact` (only ever shown to the other party post-handover)
- [x] POST validates, merges `cleaned_data` into `draft.data`, saves, redirects to step 3

## Step 3: Location

Form: `LocationForm` (new when this step was split out; `DetailsForm` now holds only `description` and `contact`)

- [x] Enter `location`, public place name, required
- [x] Enter `location_detail`, free text, required
- [x] Map renders: no saved coordinates -> Karachi, zoom 13; saved coordinates -> centred on them, zoom 15
- [x] Status line reads "Pin loaded from your saved draft" only when saved coordinates exist
- [x] Click on map -> marker moves, `lat`/`lng` inputs written to 6 decimal places
- [x] Drag marker -> same write, on `dragend`
- [x] No place search box. Nominatim forbids per-keystroke autocomplete, so the Google Places box was dropped rather than ported.
- [x] "Use my location" button calls `navigator.geolocation.getCurrentPosition`, recentres map at zoom 15, writes `lat`/`lng`
- [x] Button hidden entirely when the browser has no geolocation API
- [x] Geolocation only fires over HTTPS in production. Browsers block it on plain HTTP except on localhost. `ALLOWED_HOSTS` is currently `127.0.0.1, localhost, testserver`, so there is no TLS story yet and this path only works on localhost in development.
- [x] User can decline the browser permission prompt; the status line reports it and map plus manual entry remain available, no dead end
- [x] `Latitude` / `Longitude` inputs stay visible and editable (keyboard path, fallback if tiles fail or GPS/map are unavailable)
- [x] POST validates: `lat`/`lng` converted to strings so `draft.data` stays JSON-serialisable
- [x] Map click/drag, "Use my location", and manual entry all write to the same `lat`/`lng` fields; no separate `gps_lat`/`gps_lng` columns
- [x] Merges into `draft.data`, saves, redirects to step 4

## Step 4: Matching

Form: `MatchingForm`

- [x] Question schema generated dynamically from the category chosen in step 1
- [x] Answer private matching questions (never rendered publicly, never in admin)
- [x] POST validates, merges into `draft.data`, saves, redirects to step 5

## Step 5: Review and publish

No form.

- [x] Review screen shows all entered data
- [x] Submit calls `services.publish()`, wrapped in `transaction.atomic`
- [x] `validated()` re-runs `TypeForm`, `DetailsForm`, and `MatchingForm` against the entire stored draft, not just what each step already validated
- [x] `lat`/`lng` are required at this point since `DetailsForm` revalidates them: no publish without coordinates, regardless of which part of 2b supplied them
- [x] Create or update the `Report` row
- [x] Write an `Event` entry
- [x] Run `recalculate()`: deletes this report's old `Possible Match` rows, rescores against every open candidate
- [x] Delete the `Draft`

## Cross-step rules

- [x] Progress stepper renders all 5 steps as numbered circles, with the current step filled blue, completed steps light blue, and future steps grey
- [ ] Circles joined by a connecting line. What exists is a `border-bottom` running under the whole stepper plus a 10px grid gap, so the circles float independently and nothing joins them to each other. This was invisible at four steps and is a real gap at five.
- [x] Step guards bounce a user back if they deep-link forward past data not yet entered
- [x] `Draft.data` already carries `lat`/`lng`, so a draft survives a page reload mid-wizard with no extra schema work
- [x] Existing `Match` rows keep their stored score and breakdown until the report is republished; a scoring code change does not retroactively update the database

## Coordinate display

Coordinates are stored and feed `location_score`, but they are not shown to users. The place name and location description are what a reader gets.

- [x] Raw decimal `lat`/`lng` removed from `dashboard.html` (4 sites), `match.html` (2 sites), and the wizard review step. This was leaking each item's precise drop point to the other party of a match. `report.html` never showed coordinates, so display is now consistent.
- [ ] Dashboard cards gain a small map pin
- [ ] Match view gains a map pin
- [ ] Wizard review screen gains a map pin

The three remaining items are blocked on a decision, not on effort, and they are additions to pages that currently show no coordinates at all. They split two ways:

- **Embedded map per card.** No dependency, but each Leaflet instance is a live map that fetches tiles. The dashboard renders up to 3 report cards plus match rows, so 3 to 7 maps per page, on every load. If done this way it must be `interactive: false` with no controls and no attribution control, and confined to the report detail page rather than the dashboard.
- **Link out to a map page.** Far cheaper, and a pin is the only sensible way to express a coordinate, but no map page exists. That is the same undecided browse view described below, so this route is blocked on the visibility decision.

Reverse geocoding is not implemented. Coordinates are expressed by map only, with no address text. Adding Nominatim reverse geocoding would be a separate change and would need a server-side proxy carrying an identifying User-Agent at no more than one request per second. Undecided.

## Known open items

- [x] **QR scan no longer copies the Lost report's exact coordinates.** `report_found` used to write `lat` and `lng` into the finder's draft, so the Found report published the owner's drop point as if the finder had recovered the item there, and `location_score` awarded the pair a full 20 for a position nobody had independently observed. Both keys are now dropped alongside the other scan-time clears, while `location` stays as a coarse confirmable hint. This restores the rule the earlier scan-mix fix already applied to `location_detail`. Covered by `test_scan_does_not_copy_lost_coordinates`.
- [ ] **No test exercises the map picker.** Every test types into `#id_lat` directly or never reaches the picker. If Leaflet failed to load, or the click handler stopped writing the inputs, the suite would still pass. A Playwright test that clicks the map and asserts both inputs changed would close this.
- [ ] **No browse or map view exists.** No page lists reports from multiple owners. Adding one is a new disclosure surface: today no user can see another user's report except a match they share, and every open item's exact drop point is the most sensitive field in the schema. Needs a product decision on who sees it, not just a template.
- [x] **Tile source moved off the blocked OSM endpoint.** `tile.openstreetmap.org` returned 403 for every tile with "App is not following the tile usage policy of OpenStreetMap's volunteer-run servers", so the basemap rendered as a grid of blocked images and the location step was unusable. Now served from `tile.openstreetmap.de`, which needs no key. `maxZoom` is 18 because that server returns 404 at 19.
- [x] **CARTO was tried and rejected.** Its public basemaps now return a 2 KB "API KEY REQUIRED" watermark tile instead of imagery, which is HTTP 200 and looks like success. Detected by decoding the PNG: 97.4 percent near-white pixels across a 16-colour palette, against 14.6 percent across 255 colours for a real tile. Worth remembering that a byte-length or colour-variance check alone does not catch this, since a text watermark has high variance.
- [ ] **Tile provider still needs a production decision.** `tile.openstreetmap.de` is a volunteer-run community server and is not sized for real traffic. Before any deployment, use a keyed provider such as MapTiler or Stadia Maps, or self-host tiles. This is a development fix only.
- [ ] **Increment 4 will break the map silently** if a content security policy is added without allowing `img-src` and `connect-src` for the tile host. No CSP exists today.
