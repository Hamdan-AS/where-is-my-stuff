# Software Requirements Specification (SRS)

Where Is My Stuff? GPS-enabled Lost and Found System for NED University, Karachi.

Course: CS-326 Software Engineering.
Scope: The GPS prototype branch. The frozen NED-only baseline is documented in the sibling project at `/home/elite/sandbox/where-is-my-stuff/` and in `scope-freeze.md`. This SRS describes the GPS branch as it is implemented today.

Related documents: `architecture.md` (requirements summary), `scope-freeze.md` (scope and change control), `matching-architecture.md` (matching rules), `database.sql` (data model), `ui-wireframes-redesign.png` (UI reference).

## 1. Purpose and scope

The system is a web-based lost and found management system for NED University, extended from a fixed campus scope to a Karachi-wide scope. Students file Lost and Found reports with GPS coordinates, the server matches opposite report types from different users using a deterministic, explainable score, and both participants agree a handover before contact details are shared. The system records the completed return.

Included in this version: accounts, report CRUD with lat/lng, category-specific private questionnaires, same-user exclusion, haversine distance matching, mutual handover acceptance, private contact release, Moderator/Admin management, and return status.

Excluded: image upload and recognition, live maps, geocoding, chat, email, push notifications, QR/NFC, mobile apps, and a second backend stack. A Leaflet.js map display is optional and deferred.

## 2. Definitions

| Term | Meaning |
|---|---|
| Report | One Lost or Found posting by a user. |
| Questionnaire | The category-specific set of private fields both reporters complete. |
| Match | A scored Lost/Found pair from different users. |
| Handover | The mutual proposal and acceptance of a meeting point. |
| Recovery status | Possible Match, Handover Proposed, Handover Scheduled, Returned, Rejected. |

## 3. Stakeholders

| Stakeholder | Interest |
|---|---|
| Student (reporter) | Registers, files reports, reviews matches, arranges handover. |
| Finder | A Student who filed a Found report. Not a separate account role. |
| Moderator | Reviews, closes, or deletes invalid reports. Cannot assign roles. |
| Admin | Moderator access plus role assignment. |
| NED University | Operator of the system. |

## 4. Functional requirements

Columns: ID, requirement, acceptance evidence. Requirements FR-01 to FR-11 carry over from the frozen baseline (architecture.md). GPS-specific behaviour is stated in FR-02b, FR-04s, and FR-05s below.

| ID | Requirement | Acceptance evidence |
|---|---|---|
| FR-01 | Register, log in, log out, hash passwords, use session access control. | Invalid login fails; valid login opens the dashboard; logout ends the session (integration_test.py). |
| FR-02 | Create, view, edit, close, and delete owned reports. | An edited `user_id` cannot change another person's report. |
| FR-02b | Every report stores `lat` and `lng`; `validate_report()` rejects missing or out-of-range coordinates (-90..90, -180..180). | `validate_report()` in functions.php; integration rerun requested in verification-and-validation.md. |
| FR-03 | Store type, title, category, public description, location, coordinates, location description, date, contact, and the complete category questionnaire. | Server validation rejects missing, unknown, oversized, invalid, conditional-field, and sensitive public-description values. |
| FR-04 | One account can file both Lost and Found reports. | Both types appear on the same dashboard. |
| FR-04s | Event date is submitted as `d-m-Y` and stored as `Y-m-d`. | Canonicalisation is asserted in tests/matching_test.php. |
| FR-05 | Compare only opposite report types from different users. | A user's own reports never become a match. |
| FR-05s | Location score uses haversine distance bands: <0.5 km = 20, <1 km = 15, <2 km = 10, <5 km = 5, else 0. Missing coordinates score 0. | `haversine_score()` in functions.php; matching_test.php pending update. |
| FR-06 | Score category, location, date, description similarity, and private field agreement. | Match page stores and displays each factor score. |
| FR-07 | Keep all private answers private; show only the agreement count. | Dashboard, staff page, and unrelated-user responses contain no answer values. |
| FR-08 | Either participant proposes a free-form handover location and time; only the other participant can accept it. | Match changes to Handover Scheduled only after both accept. |
| FR-09 | Reveal contacts only after mutual acceptance; record Returned afterward. | Both reports show Returned after completion. |
| FR-10 | Moderator/Admin close or delete reports; Admin assigns roles. | Student gets 403; Moderator cannot assign roles; Admin can. |
| FR-11 | Warn users about a likely duplicate Open report. | The report stays saved; the dashboard shows a review warning. |

## 5. Non-functional requirements

| Attribute | Requirement |
|---|---|
| Security | Every mutation is POST-only and CSRF-protected; passwords hashed; sessions strict-mode with HttpOnly cookie. |
| Privacy | Private answers (report_answers) are never rendered, only agreement counts; Cards / IDs stores only a masked suffix; full identifiers are rejected. |
| Usability | Progress-header report form, grouped details, explainable score banner, Pakistani date `d-m-Y` display per `ui-wireframes-redesign.png`. |
| Reliability | Report, answer, match, and handover writes succeed or fail together inside `write_transaction()` (GET_LOCK + transaction). |
| Maintainability | Matching rules isolated in matching.php; workflow writes isolated in workflow.php; validation isolated in functions.php. |
| Efficiency | Candidate matching runs inside the save transaction and is limited by the `reports_candidate_lookup` index. |
| Portability | PHP 8.1 on MySQL with utf8mb4; connection settings overridable through `NED_DB_*` environment variables. |

## 6. Domain constraints

- Report types are `Lost` and `Found`; categories are Wallet / Purse, Cards / IDs, Keys, Electronics, Bag, Documents, Cash / Money, Other.
- A candidate pair must be opposite types, different users, same category, both `Open`, with at least two private answers agreeing and a total of at least 70 (matching-architecture.md, scope-freeze.md).
- A report can be in at most one active handover (workflow.php `report_has_locked_match`).
- Contacts release only after both participants accept the same proposal.
- Public descriptions must not contain emails, phone/identity numbers, or private-identifier phrases (functions.php `validate_public_description`).
- Time zone is Asia/Karachi throughout.

## 7. Traceability matrix

| Requirement | Module | Entry page |
|---|---|---|
| FR-01 | Authentication | auth.php, logout.php |
| FR-02, FR-02b, FR-03, FR-04, FR-04s, FR-11 | Reports | report_form.php, reports.php, report.php |
| FR-05, FR-05s, FR-06, FR-07 | Matching | matching.php, match.php, index.php |
| FR-08, FR-09 | Handover | handover.php, workflow.php |
| FR-10 | Management | moderation.php, admin.php |

## 8. Sign-off

| Role | Company/Organisation | Date | Signature |
|---|---|---|---|
| Student developer | NED University | 12 September 2026 | Pending |
| Course instructor | NED University | Pending | Pending |
| NED stakeholder | NED University | Pending | Pending |

Defect record: see verification-and-validation.md (V&V) and maintenance-record.md (changes). Change control: scope-freeze.md.