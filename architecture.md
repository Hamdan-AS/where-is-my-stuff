# Architecture and CS-326 evidence

## Project definition

Title: Design and Development of a Web-Based Lost and Found Management System for NED University.

Students create Lost and Found reports, receive explainable possible matches, arrange a mutual handover, and record the returned item. One account may submit both report types. A user's own Lost and Found reports are excluded by their user_id.

## Requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| FR-01 | Register, log in, log out, hash passwords, and use session access control. | Invalid login fails; valid login opens the dashboard. |
| FR-02 | Create, view, edit, close, and delete owned reports. | An edited user_id cannot change another person's report. |
| FR-03 | Store type, title, category, public description, NED location, written location details, date, contact, and the complete category-specific private questionnaire. | Server validation rejects missing, unknown, oversized, invalid, conditional-field, and sensitive public-description values. |
| FR-04 | A Student can submit both Lost and Found reports. | Both types appear in the same dashboard. |
| FR-05 | Compare only opposite report types from different users. | A user's own reports never become a match. |
| FR-06 | Score category, location, date, description similarity, and private field agreement. | Match page stores and displays each public factor score. |
| FR-07 | Keep all category-specific private answers private while showing only the agreement count. | Dashboard, staff page, and unrelated user responses contain no answer values. |
| FR-08 | Let either participant propose a fixed NED handover; require the other participant to accept or reject it. | Match changes to Handover Scheduled only after both accept. |
| FR-09 | Reveal contacts only after mutual acceptance and record Returned afterward. | Both reports show Returned after completion. |
| FR-10 | Moderator/Admin close or delete reports; Admin assigns roles. | Student receives 403; Moderator cannot assign roles; Admin can. |
| FR-11 | Warn users when they create a likely duplicate Open report. | The report remains saved, but the user receives a dashboard review warning. |

## Matching rule

The server compares an opposite-type pair only when both reports are Open, categories match, owners differ, and both category questionnaires are valid. It awards 20 points for category, up to 20 for location using haversine distance bands (under 0.5 km scores 20, under 1 km 15, under 2 km 10, under 5 km 5, and nothing beyond that), 15/10/5/0 for date distance, 0 to 15 for description Jaccard similarity, and a normalized 30 points for equal private answers. A report with no coordinates scores zero for location. At least two private answers and a total of 70 are required.

The title is a display heading. It does not affect the score. Private answers use normalized select values and masked card suffixes. Full CNIC and card numbers are rejected.

Public descriptions contain broad appearance and location information only. The server rejects likely email addresses, phone numbers, full identity/card-number sequences, and explicit private-identifier phrases. Private questionnaire answers are never copied into or derived from the public description.

## Modules

| Module | Responsibility |
|---|---|
| Authentication | Registration, login, password hashing, sessions, role refresh |
| Reports | Ownership-checked report CRUD and normalized answer storage |
| Matching | Candidate eligibility, deterministic scoring, same-user exclusion |
| Handover | Participant checks, proposal, acceptance, rejection, contacts, return |
| Management | Moderator/Admin report closure and deletion; Admin role assignment |

The active data model has users, reports, drafts, matches, and events. Private answers live in a validated JSON field on the report rather than a separate `report_answers` table, and handover state lives on the match rather than a separate `handovers` table. The old PHP claims table and single private question are retired.

## Process and risk record

The project was delivered in two completed increments, covering the account and dashboard foundation and then reporting, matching, handover, and management. Further increments for notifications, password reset, and deployment remain pending. Main risks are false matches, private data leaks, unauthorized changes, stale suggestions after edits, and database setup errors. The fixed score explanation, server-side validation, ownership checks, transaction boundaries, and ownership tests address those risks.

## State model

Report state is Open, Returned, Closed, or Removed. Removed is a soft delete: the row stays for referential integrity and is filtered out of listings. Match state is Possible Match, Handover Proposed, Handover Scheduled, Returned, or Rejected. A return updates both linked reports and rejects any other possible match on them.

## CS-326 evidence

Keep the requirements table, frozen matching architecture, scope checkpoint, database design, state transitions, risk record, implementation checklist, and later test results. Record actual defects and fixes. Do not present a high match score as proof of ownership: it is only a suggestion.

Image matching, chat, notifications, mobile apps, and another backend stack remain outside the frozen scope.

Two capabilities were added after the original freeze and are now implemented. GPS coordinates are stored on the report, feed location scoring, and are captured through a location picker that uses a vendored Leaflet map with OpenStreetMap tiles, so no keyed provider is required. The QR scan flow lets a finder file a Found report from a code printed on the Lost report. A browse view showing other users' reports on a shared map is still undecided, because no page currently lets one user see another user's report except a match they share.

## Implementation map

One Django application with server-rendered pages and SQLite. No PHP data is imported.

### Modules

- Accounts: Django password hashing, sessions, CSRF, normalized registration emails, and standard admin user management.
- Reporting: five form steps, account-owned database drafts, server validation, escaped Review, and one publication action. Location is its own step holding the map, place name, and coordinates. Publication re-validates the whole stored draft rather than trusting the per-step checks, so `lat` and `lng` are required to publish.
- Questionnaires: one Python schema determines visible fields and validation. The selected contents generate suffix and detail fields; no repeated presence questions. Browser change events refresh questions through the same server schema.
- Matching: pure similarity calculation, then persistence of eligible report pairs. No missing-value rewards or score above 100. Bank-card comparison ignores entry order. Recalculation runs only on publication, so stored scores persist until a report is republished.
- Workflow: atomic proposal, acceptance, rejection, return, and moderation services. SQLite IMMEDIATE transactions serialize writes; report reservation prevents competing proposals.
- Presentation: templates contain the UI; CSS controls layout; JavaScript handles conditional refresh, numeric filtering, live privacy hints, and the map location picker.

### Records

User owns Reports and Drafts. Reports carry private answers in a validated JSON field. Match relates one Lost and one Found report, stores its factor breakdown and meeting state, and is unique per pair. Event retains each report's workflow history. Draft deletion happens only after successful publication.

### Authority and visibility

Students can read and edit their own eligible reports and read only their own matches. Both Lost and Found participants submit private answers independently. Matching suggests a pair; people review the physical item at handover. Contacts are shown only for Scheduled or Returned matches. Staff management exposes public report details and audited close/remove actions. Reports, answers, drafts and matches are absent from generic Django admin.

The QR image endpoint is unauthenticated by design so the code can be printed, and it exposes nothing beyond the UUID already encoded in the URL. The scan destination requires login.

### Increment evidence

The increments are accounts/dashboard, reporting, matching, handover, and management. TODO-INCREMENTAL.md records actual implementation and check results. No stakeholder sign-off or production-readiness claim is implied by automated tests.
