# Software Requirements Specification

## Where Is My Stuff? — Karachi Lost-and-Found Web Application

| Document field | Value |
|---|---|
| Version | 3.2 (implementation-aligned review revision) |
| Standard layout | IEEE 29148 style, adapted for this project |
| Product scope | Release 1.0 implementation baseline; future roadmap is informative only |
| Status | Revised for stakeholder review; approval is pending. Proposed quality targets and the production privacy decision are not approved commitments. |


## 1. Introduction

### 1.1 Purpose

This document specifies externally observable requirements for Where Is My Stuff? It supports stakeholder review, design, implementation, and verification. Functional requirements use unique IDs, “shall” statements, priorities, and acceptance criteria. Requirements describe product behavior rather than source-code organization. Items explicitly marked Proposed are candidate targets, not normative Release 1.0 requirements or release acceptance gates until approved and incorporated into the baseline.

### 1.2 Scope

The system helps people in Karachi publish Lost and Found reports, find plausible opposite-kind reports, and coordinate an in-person return. It includes accounts, resumable report drafts, deterministic matching, report history, QR sharing, time-limited personal QR contact labels, and staff moderation. The service offers leads only: it does not establish real-world identity, possession, or ownership. It does not arrange payment, courier delivery, or police reporting.

### 1.3 Intended readers

Project owner, user/stakeholder representatives, developers, testers, maintainers, and course reviewers.

### 1.4 References

- IEEE Std 29148, Systems and software engineering — Life cycle processes — Requirements engineering.
- Project roadmap and CS-326 course materials, as background for proposed future scope.
- Current application source, templates, and implementation notes listed in Section 12.

### 1.5 Conventions and definitions

“Shall” denotes a mandatory requirement. Priority is High, Medium, or Low. Release 1.0 describes the implementation baseline. Appendix A is informative, non-normative future scope and carries no delivery-date commitment.

| Term | Meaning |
|---|---|
| Report | A record of one Lost or Found item |
| Reporter | Registered user who owns a report |
| Draft | Unpublished report data saved for later completion |
| Private answers | Category-specific details used in matching and withheld from normal report views |
| Possible match | Lost/Found pair meeting eligibility, private-answer, and score rules |
| Participant | Owner of either report in a match |
| Handover | Proposed meeting place and time between match participants |
| Reserved | A report held by a proposed or scheduled handover, locking editing and moderation |
| Display identifier | Human-readable report label from kind and database ID (`LFD-...` Lost, `FND-...` Found) |
| Personal label | Time-limited QR bearer link that deliberately displays its owner's phone while active |
| Moderator | Staff user permitted to close or remove eligible reports |
| Acceptance criterion | Observable result that determines whether a requirement is satisfied |

## 2. Overall description

### 2.1 Product perspective

The product is a standalone browser-based lost-and-found service. It has no dependency on an authoritative lost-property registry, identity provider, payment provider, courier service, or notification provider. It uses a third-party map tile service for location selection. A readable place name, location description, and coordinates are required for publishing. The reporter must provide coordinates either by placing/moving the map pin or entering latitude and longitude; map imagery availability is external.

### 2.2 Product functions

The system supports account registration and sign-in; creation, saving, resumption, and editing of Lost/Found reports; private category questions; deterministic match suggestions; handover proposal and acceptance; return recording; owner history; report QR sharing; personal QR labels; and staff moderation. Possible future additions are listed as informative, non-normative scope in Appendix A.

### 2.3 User classes

| User class | Goals and access |
|---|---|
| Reporter | Register, publish and manage own reports, review matches and history |
| Match participant | Coordinate a handover and report a return for a match involving their report |
| Report-QR finder | Sign in and start a Found draft from selected public hints |
| Personal-label finder | Scan an active label and view the phone number intentionally published by its owner |
| Moderator | Review, close, or remove eligible reports |
| Organization administrator | Proposed future role; see informative Appendix A |

### 2.4 Operating environment

Current scope is a mobile- and desktop-browser web application. Users need internet access for the service and map imagery. The service requires a relational data store (SQLite for local use; PostgreSQL supported) and private media storage for photographs and QR images. Application time uses the `Asia/Karachi` timezone. Public deployment requires HTTPS and an agreed operational environment.

### 2.5 Constraints

| ID | Constraint |
|---|---|
| CON-01 | The product shall be a web application; a native mobile application is out of scope. |
| CON-02 | Matching shall be deterministic and rule-based; machine-learning or LLM ranking is out of scope for Release 1.0. |
| CON-03 | Release 1.0 shall target Karachi; places shall have readable names and geographic coordinates. No Karachi-only coordinate boundary is currently enforced. |
| CON-04 | No report, match score, verification result, or QR scan shall be represented as proof of identity, possession, or ownership. |

### 2.6 Assumptions and dependencies

Users provide accurate information, have an email account, and choose a safe public meeting place. Map imagery may be unavailable. Browser geolocation needs browser support, permission, and a secure context. A reachable phone number is needed for a handover. The service cannot enforce physical-world safety or truthfulness of reports.

## 3. External interface requirements

### 3.1 User interface

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| UI-01 | The system shall provide pages for registration, sign-in, dashboard, report wizard, history, report details, match details, QR labels, and staff moderation. | High | A user with the applicable role can navigate to each listed function; protected pages disclose no data to signed-out users. |
| UI-02 | The report wizard shall present Type, Details, Location, Matching, and Review in that order. | High | A new reporter sees all five stages in order; an incomplete prerequisite prevents skipping ahead. |
| UI-03 | The reporter shall provide complete location information: a readable place name, a location description, and coordinates. Coordinates shall be provided either by selecting or moving a pin on the map or by entering latitude and longitude manually. | High | Submission succeeds through either coordinate-entry path when all required location fields are valid; the map path is not required when valid coordinates are entered manually. |
| UI-04 | The core reporting flow shall fit a 360-pixel-wide viewport without horizontal page scrolling. | Medium (proposed) | At 360 CSS-pixel viewport, all required fields and actions are reachable without horizontal scrolling. This target is not yet validated. |
| UI-05 | Validation errors shall identify the relevant field and preserve previously entered valid values. | High | Invalid submission displays an actionable field-level message and restores other submitted values. |

### 3.2 Hardware interfaces

No dedicated hardware is required. A phone camera and a standard QR scanner may be used by the user.

### 3.3 Software interfaces

| Interface | Requirement |
|---|---|
| Relational data store | Persist account, report, draft, match, event, and label data. Roadmap data entities are conditional on release approval. |
| Private media storage | Store report photographs and QR images and enforce the privacy requirements in Section 8. |
| Map tile service | Supply map imagery; its failure shall not prevent coordinate entry. It is not an authoritative source of report truth. |
| QR reader | A standards-compliant scanner shall open encoded report or personal-label addresses in a browser. |

### 3.4 Communications interfaces

User traffic shall use HTTP(S). A public deployment shall use HTTPS for every page. State-changing requests shall include an anti-forgery token. Session and anti-forgery credentials shall not be exposed in page content or public QR data.

## 4. System features and functional requirements

### 4.1 Accounts and access

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-ACC-01 | The system shall let a visitor register with a name, unique email address, and a password that satisfies configured password validators. | High | Valid unused credentials create one account and sign the user in; a duplicate email or password failing validators creates none and produces an error. |
| FR-ACC-02 | The system shall authenticate a registered user using email and password and offer a remember-me session choice. | High | Valid credentials establish a session; invalid credentials establish none. The remember-me choice controls session expiry. |
| FR-ACC-03 | The system shall allow an authenticated user to sign out. | High | After sign-out, a protected request requires authentication. |
| FR-ACC-04 | The system shall require authentication for protected reports, drafts, matches, history, dashboard, and label management. | High | A signed-out request discloses no protected data and asks the visitor to authenticate. |
| FR-ACC-05 | The system shall restrict report/draft actions to the owner, match actions to participants, and moderation actions to staff. | High | An actor lacking the required relationship/role is denied and the record remains unchanged. |
| FR-ACC-06 | The system shall reject state-changing requests without valid anti-forgery protection. | High | A request with a missing or invalid token is rejected without changing data. |

### 4.2 Reports and drafts

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-REP-01 | The system shall let an authenticated user create a Lost or Found report. | High | User can select either report kind; all later report behavior preserves that selection. |
| FR-REP-02 | A report shall record category, title, event date, public description, contact phone, readable place name, required location description, latitude, and longitude. All listed fields are required to publish. | High | Missing or invalid data in any required field, including location description or either coordinate, prevents publication; valid values are saved with the report. |
| FR-REP-03 | A report may include one photograph. | Medium | The photograph may be omitted; when supplied it is associated with the report and protected under FR-PHO-04, NFR-SEC-08, and SEC-05. |
| FR-REP-04 | The system shall ask category-appropriate private questions and store answers with the report. | High | Each supported category presents applicable questions; required and conditional answers are validated before publication. |
| FR-REP-05 | The system shall save draft progress whenever a valid wizard step is submitted. | High | After submitting a valid step and leaving the flow, the draft contains that step's values. |
| FR-REP-06 | The system shall let the owner resume a saved draft and restore all previously saved fields. | High | Given values saved through step 3, resuming restores those values in steps 1 to 3. |
| FR-REP-07 | The system shall require explicit confirmation before discarding an existing draft to start another. | Medium | Cancel preserves the draft; confirmation discards it and permits a new draft. |
| FR-REP-08 | A user shall not be able to read, edit, or delete another user's draft. | High | A different account receives denial/not-found and cannot alter or infer draft contents. |
| FR-REP-09 | The review step shall show the owner a summary of report type/category, title, event date, public description, location, and any photo. Private answers and contact phone shall remain on their earlier wizard steps and shall not be included in the review summary. | High | The review summary shows the listed values and no private-answer or phone values; the owner can return to earlier steps to inspect or change them. |
| FR-REP-10 | The system shall let an owner edit an open report that is not reserved for handover. | Medium | Eligible report can be edited; closed or reserved report cannot be changed. |
| FR-REP-11 | The system shall run matching after a report is published. | High | A newly published report is evaluated against eligible opposite-kind reports and qualifying matches are available to participants. |
| FR-REP-12 | When a draft's category is changed, the system shall clear private answers that belong to the previous category. | Medium | After a category change, old-category answer keys appear in neither the revised draft nor review. |
| FR-REP-13 | Each report shall have a display identifier built from its kind and database ID (`LFD-...` for Lost, `FND-...` for Found) and a separate UUID used in report QR URLs. The database ID shall not appear in QR URLs. | Medium | A Lost report shows an `LFD-` identifier and a Found report an `FND-` identifier; its report QR URL contains the UUID. |

### 4.3 Input validation and photos

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-VAL-01 | The system shall reject title, place, location detail, or description text that matches configured private-identifier patterns. | High | Identifiers within configured detection rules are rejected; submitted text is not silently rewritten. |
| FR-VAL-02 | The system shall reject public text containing configured invisible or control characters. | High | Submitted characters covered by the configured rule cause a field error and no publication. |
| FR-VAL-03 | When public text is rejected, the system shall explain the validation failure and preserve the submitted value for correction. | High | The user sees an actionable error and can edit the unchanged submitted value. |
| FR-VAL-04 | The system shall require the reported event date not to be in the future and not before 1 January 2000. | Medium | A future date or date before 1 January 2000 is rejected; today or an allowed past date is accepted. |
| FR-VAL-05 | The system shall require latitude and longitude to fall within valid geographic ranges (latitude -90 to 90, longitude -180 to 180). The system does not restrict points to a service-area boundary. | Medium | A point inside valid ranges is accepted; a point outside them is refused. |
| FR-VAL-06 | The system shall render user-entered text as data rather than executable markup or script. | High | Script/markup test strings render inertly in report, match, history, and staff views. |
| FR-PHO-01 | The system shall accept a photo only if its type, size, and pixel dimensions are within configured limits. | Medium | A valid in-limit photo is accepted; each out-of-limit sample is refused without losing other draft data. |
| FR-PHO-02 | The system shall decode each uploaded image and reject damaged or non-image files. | Medium | Renamed non-image and corrupted image files are refused. |
| FR-PHO-03 | The system shall normalize accepted photos to JPEG, resize the longest edge to at most 1,800 pixels, and discard source metadata before storage. | Medium | Retrieved image is JPEG, is no larger than 1,800 pixels on its longest edge, and has no carried source metadata. |
| FR-PHO-04 | The system shall serve report photographs only to the report owner and an owner of the opposite report in a match involving that report. | High | Authorized requests return the image; unrelated/anonymous requests return no image bytes. |

Photo upload limits are JPEG, PNG, or WebP; 5 MiB maximum; 6,000 pixels per side and 24 megapixels total. Stored normalized output is JPEG with longest edge no greater than 1,800 pixels.

### 4.4 Matching

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-MAT-01 | The system shall consider only reports owned by different users, of opposite kind, both open, and in the same category. | High | Any pair violating one condition creates no possible match; an otherwise eligible pair proceeds to scoring. |
| FR-MAT-02 | The system shall require at least two meaningful private-answer agreements for a possible match. | High | Fewer than two agreements produces no match even when other factors score maximally. |
| FR-MAT-03 | The system shall score an eligible pair from 0 to 100 using category (20), location (20), date (15), description (15), and private answers (30). | High | Controlled factor fixtures produce the documented weighted sum, always between 0 and 100. |
| FR-MAT-04 | The system shall create a possible match only when its score is at least 70. | High | Score 69 creates none; score 70 with at least two private agreements creates one. |
| FR-MAT-05 | The system shall store each match's score and factor scores. | High | Match detail displays the correct factor totals for the test pair. |
| FR-MAT-06 | The system shall create at most one match for a given Lost/Found report pair. | High | Repeated publication/recalculation of the same pair does not create duplicate matches. |
| FR-MAT-07 | The match page shall show factor scores without exposing the other party's private-answer values. | High | Participants can see factor agreement; raw private responses remain absent. |
| FR-MAT-08 | The match page shall state that a match is not proof of ownership. | High | The notice is visible on each match detail page. |

Scoring details: location uses haversine distance (<0.5 km: 20; <1 km: 15; <2 km: 10; <5 km: 5; otherwise 0; missing coordinates: 0). Date uses absolute difference (0 days: 15; 1 day: 10; 2–3 days: 5; otherwise 0). Description uses Jaccard overlap of lowercase alphanumeric tokens of at least three characters, after configured stop words are removed, rounded from `15 × intersection / union`; empty token union scores 0. Private values are compared after trimming and case-folding, excluding configured non-evidence values; bank issuer/suffix pairs are treated as pairs independent of order. At least two meaningful private agreements and total score >=70 are both mandatory.

### 4.5 Handover and return

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-HND-01 | A participant shall be able to propose a meeting place and future time for a possible match. | High | A non-empty place and future time create a proposal; invalid time or reserved reports prevent the proposal. |
| FR-HND-02 | The other participant shall be able to accept the pending proposal. Either participant may dismiss a possible match or pending proposal. | High | The non-proposer's acceptance schedules the handover. Dismissal sets the match to Rejected and releases any reservation for a pending proposal. |
| FR-HND-03 | The proposer shall not accept their own proposal as the second participant. | High | Proposer acceptance is refused and state remains pending. |
| FR-HND-04 | Only the participant who dismissed a suggestion shall be able to restore it, and only if neither report is reserved and the pair still meets current match rules. | Low | The dismissing participant restores an eligible pair; the other participant cannot restore it; stale, ineligible, or conflicting pair remains rejected. |
| FR-HND-05 | Once a handover is scheduled or returned, the system shall show each match participant both saved report contact numbers. | High | After the other participant accepts, both authorized participants see both numbers. |
| FR-HND-06 | Before the handover is scheduled, the system shall not show either party's saved phone number through the match. | High | Neither participant can retrieve the other report's number while the match is Possible Match or Handover Proposed. |
| FR-HND-07 | A participant shall be able to record return only at or after the scheduled meeting time. On return, both reports become Returned, reservations are cleared, and competing possible matches involving either report are dismissed. | High | Early return is refused; at or after meeting time it succeeds and updates both reports and competing matches. |
| FR-HND-08 | While a handover is proposed or scheduled, the system shall reserve its reports against editing, moderation, or a second active handover. | High | Competing proposals allow at most one active reservation; edit/moderation attempts fail while reserved. |
| FR-HND-09 | Only a participant of a match shall be able to view or change its state. | High | Nonparticipant read and action requests are denied without disclosure or state change. |

### 4.6 History and dashboard

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-HIS-01 | The dashboard shall show the signed-in user's report summaries, drafts, and active matches. | High | Each owned item appears with current state; another user's items do not appear. |
| FR-HIS-02 | The history page shall list the user's non-Removed reports and support search by title/location and filters for kind and status. | Medium | Combined query and filters return only matching records owned by that user. |
| FR-HIS-03 | The history page shall divide long lists into pages of ten reports. | Low | More than ten records are accessible across pages. |
| FR-HIS-04 | The user shall see only their own reports in dashboard and history. | High | Two-account fixture demonstrates strict owner separation. |
| FR-HIS-05 | The system shall record actor and time for report publication/edit, match transitions, moderation, and return events. | Medium | Each specified action produces attributable event entries on the affected report(s). |
| FR-HIS-06 | The system shall reject history search strings that contain configured invisible or control characters. | Medium | Such a query returns a client error and exposes no additional report data. |

### 4.7 Report QR and personal labels

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-QR-01 | The system shall generate a QR code for a report, encoding its UUID URL. The normal report interface offers the code for Lost reports. | Medium | The UUID URL opens the report-entry flow. The current endpoint does not enforce Lost kind; see GAP-04. |
| FR-QR-02 | A signed-in finder opening the report QR shall start a Found draft prefilled with selected public Lost-report hints (category, title, and coarse place). | Medium | Draft contains approved hints and remains unpublished until the finder completes submission. Exact coordinates, location detail, private answers, and contact are not copied. Kind is seeded as Found. |
| FR-QR-03 | The report QR shall not reveal private answers or the owner's phone number. | High | QR URL and seeded draft contain neither private answers nor contact number. |
| FR-QR-04 | A signed-out finder opening the report QR shall be asked to sign in before report hints are copied into a draft. | Medium | Before sign-in no seeded draft is created; after sign-in eligible hints may be copied. |
| FR-QR-05 | A user shall be able to create a personal label with an item name and phone number. The label's expiry is fixed at six months after creation. | Medium | A created label expires six months after creation; the user cannot choose another expiry. |
| FR-QR-06 | The system shall store only a non-reversible digest of each personal-label bearer token. | High | Persisted label record contains no raw token; token resolution still works. |
| FR-QR-07 | Scanning an active personal label shall show the phone number its owner chose to publish. | Medium | An active, unexpired, unrevoked token displays its associated number. |
| FR-QR-08 | Scanning an expired, revoked, or deactivated label shall not show a phone number. | High | All inactive conditions suppress the number. |
| FR-QR-09 | A user shall be able to deactivate a personal label at any time and reactivate it. Reactivation extends expiry by six months. | Medium | Deactivation immediately suppresses contact; reactivation makes the existing printed code work again until the new expiry. |
| FR-QR-10 | The system shall refuse self-use of a report QR and show a notice when the source report is closed or reserved. | Medium | The owner is returned to their report; a closed/reserved source seeds no Found draft and shows a notice. |
| FR-QR-11 | The label owner shall be able to view and download the label's QR image. Other accounts shall not access it. | Medium | Owner receives the image; a non-owner receives denial or not-found. |

### 4.8 Moderation

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-MOD-01 | The system shall provide staff with a report-management list of non-Removed reports. | Medium | Authorized staff can access the list. |
| FR-MOD-02 | A staff user shall be able to close or remove an open report that is not reserved. The action shall dismiss its possible matches. | Medium | Eligible report changes state and possible matches become Rejected; closed, removed, or reserved report action is refused. A Removed report leaves ordinary history and management lists. |
| FR-MOD-03 | The management list shall not show private answers. | High | Private answer values do not appear in management output. |
| FR-MOD-04 | Each moderation action shall record the acting staff user and event time. | Medium | Resulting event identifies the actor and timestamp. |
| FR-MOD-05 | A non-staff user shall be denied access to management functions. | High | Non-staff request is denied without exposing the management list. |


## 5. Business rules

| ID | Rule |
|---|---|
| BR-01 | A match or QR scan is only a lead; it shall never change a report to Returned without a participant recording return. |
| BR-02 | Release 1.0 match score is the sum of category (20), location (20), date (15), description (15), and private-answer agreement (30). Total shall not exceed 100. |
| BR-03 | A candidate pair requires a score of at least 70 and at least two meaningful private-answer agreements. |
| BR-04 | A match can transition Possible Match → Handover Proposed → Handover Scheduled → Returned. Dismissal moves it to Rejected; only the dismissing participant may restore it if the pair remains eligible and unreserved. |
| BR-05 | A report is Open until Closed, Removed, or Returned. Only open reports are considered for new matches. |
| BR-06 | Match contacts are revealed after the other participant accepts the handover (scheduled or returned). An active personal label separately reveals its chosen number. |
| BR-07 | A report is reserved while a handover is proposed or scheduled. Reserved reports cannot be edited or moderated. |

### 5.1 Score interpretation

| Factor | Maximum | Rule |
|---|---:|---|
| Category | 20 | Full points for exact category match |
| Location | 20 | Haversine distance: <0.5 km: 20; <1 km: 15; <2 km: 10; <5 km: 5; otherwise 0. Missing coordinates score 0. |
| Date | 15 | Absolute difference: 0 days: 15; 1 day: 10; 2–3 days: 5; otherwise 0. |
| Description | 15 | Jaccard overlap of lowercase alphanumeric tokens of at least three characters, after configured stop words are removed; score is rounded `15 × intersection / union`. Empty union scores 0. |
| Private answers | 30 | Applicable normalized answers agree when trimmed and case-folded. Configured non-evidence values/placeholders are ignored. Bank issuer/suffix pairs compare as pairs independent of entry order. |

## 6. Data requirements

### 6.1 Logical data dictionary

| Entity | Principal data | Visibility and relationship |
|---|---|---|
| User | email, password hash, display name, staff role | Owns reports, drafts, labels; password is not stored in plaintext |
| Report | owner, kind, category, title, event date, public text, phone, place, coordinates, photo, status, private answers, public UUID | One owner; private answers and photos are sensitive data with restricted access; may participate in matches. Display identifier is derived from kind and database ID. |
| Draft | owner, entered report data, optional report being edited | Owner only; removed or finalized according to draft lifecycle |
| Match | Lost report, Found report, score, factor breakdown, state, proposer, meeting data | Exactly two report participants; one record per pair |
| Event | report, actor, text, timestamp | Attributable history entry for report/workflow actions |
| Personal label | owner, item name, phone, token digest, image, expiry, revoked state | Public number only while active; raw token is not persisted; owner-only image |

### 6.2 Sensitive-data requirement

Current category questions can request complete national identity and bank-card numbers for matching. Report photographs are also classified as sensitive personal data. Before public/production use, the owner shall approve necessity, minimization, protection, retention, and deletion for these data. Prefer issuer, presence, or short suffix evidence where it can satisfy matching need. Release 1.0 does not perform automated visual classification or similarity analysis on photos. See NFR-SEC-07 and Section 10.

### 6.3 Report input boundaries

| Data | Constraint |
|---|---|
| Report kind | Lost or Found |
| Category | Wallet / Purse; Cards / IDs; Keys; Electronics; Bag; Documents; Cash / Money; Other |
| Title | Required; maximum 120 characters; likely personal identifiers and configured invisible/control characters rejected |
| Public description | Required; maximum 2,000 characters; likely contact/account identifiers and configured invisible/control characters rejected |
| Contact phone | Eleven digits beginning with 0 |
| Event date | Not future; earliest supported date is 1 January 2000 |
| Place name | Required readable text; maximum 100 characters |
| Location detail | Required; maximum 255 characters; public-text screening applies |
| Latitude/longitude | Required to publish. Geographic ranges latitude -90 to 90, longitude -180 to 180; no service-area boundary enforced |
| Photo | Sensitive personal data; optional JPEG, PNG, or WebP; maximum 5 MiB, 6,000 pixels per side and 24 megapixels; decoded and normalized to JPEG at max 1,800-pixel longest edge; access controlled under FR-PHO-04, NFR-SEC-08, and SEC-05 |
| Handover place | Required readable public place; maximum 255 characters |
| Handover time | Must be future when proposed; interpreted/displayed in Asia/Karachi local time |
| Personal-label item name | Maximum 80 characters |
| Personal-label phone | Eleven digits beginning with 0; expiry six months from creation and extended six months on reactivation |

## 7. Non-functional requirements

“Proposed” thresholds are candidate targets for approval and measurement, not claims of achieved performance. They remain non-normative and are not Release 1.0 acceptance gates unless approved and incorporated into the baseline.

| ID | Category | Requirement and acceptance criterion | Priority |
|---|---|---|---|
| NFR-SEC-01 | Security | Every protected page/action shall require a valid authenticated session. Acceptance: signed-out request reveals no protected content. | High |
| NFR-SEC-02 | Security | Every protected object access shall enforce owner/participant/staff scope. Acceptance: cross-account access matrix denies unauthorized reads/actions. | High |
| NFR-SEC-03 | Security | Every state-changing browser form shall require anti-forgery protection. Acceptance: absent/invalid token is rejected with no state change. | High |
| NFR-SEC-04 | Security | State transitions shall be authorized and validated at request time. Acceptance: stale UI state cannot bypass current eligibility/reservation checks. | High |
| NFR-SEC-05 | Privacy | Private answers shall not appear in user-facing pages, responses, or notifications delivered to another user or moderator. Acceptance: role-based output review finds no private answer values outside the owner's authorized views. | High |
| NFR-SEC-06 | Privacy | Secrets and credentials shall be supplied through protected deployment configuration, not committed source. Acceptance: release security review finds no live secret in distributable source. | High |
| NFR-SEC-07 | Data protection | Before public/production use, the owner shall approve minimization, protection, retention, and deletion of sensitive private-answer and photo data. Acceptance: policy is approved and verified against collected fields. | High |
| NFR-SEC-08 | Media security | Report photos and label images shall be served through authorization-aware views. Media responses shall be private and `no-store`. Acceptance: unauthorized requests return no image bytes and authorized media responses carry private/no-store headers. | High |
| NFR-REL-01 | Reliability | Publishing, matching, moderation, and handover transitions shall complete fully or not at all. Acceptance: induced failure leaves no partial database state. | High |
| NFR-REL-02 | Reliability | Concurrent proposals involving the same report shall permit at most one active reservation. Acceptance: concurrent test yields one winner and clear rejection for others. | High |
| NFR-REL-03 | Reliability | A Lost/Found pair shall have at most one match and score shall never exceed 100, enforced by database constraints. Acceptance: repeated/concurrent generation leaves one pair; out-of-range score is refused. | High |
| NFR-REL-04 | Reliability | Persistent schema changes shall be delivered through versioned migrations. Acceptance: clean install and prior-version upgrade reach declared schema. | Medium |
| NFR-LOC-01 | Localization | User-facing dates and meeting-time behavior shall use `Asia/Karachi`. Acceptance: meeting time is stored, compared, and displayed in that timezone. | Medium |
| NFR-PER-01 | Performance | **Proposed:** with up to 1,000 open reports on agreed reference hardware, 95% of ordinary page loads complete within 2 seconds, excluding map tiles. Acceptance: load test meets target. | Medium |
| NFR-PER-02 | Performance | **Proposed:** matching after publication finishes within 5 seconds with up to 1,000 open reports. Acceptance: benchmark meets target. | Medium |
| NFR-USE-01 | Usability | **Proposed:** at least 8/10 first-time participants publish without help; median completion time <=5 minutes. Acceptance: observed success and median meet target. | Medium |
| NFR-USE-02 | Usability | Text fields shall have visible labels and errors shall say what to fix. Acceptance: review confirms every core form field label and actionable error. | Medium |
| NFR-USE-03 | Usability | Place input shall accept free-text Karachi place names independently of map imagery. Acceptance: submit a valid typed location when tile service is unavailable. | High |
| NFR-MNT-01 | Maintainability | Matching, state-transition, and moderation rules shall be independently verifiable from page rendering. Acceptance: rule-level tests can exercise behavior without browser interaction. | Medium |
| NFR-MNT-02 | Testability | Each in-scope Release 1.0 High-priority functional requirement shall map to at least one acceptance test; every other in-scope requirement shall have a test before release. Acceptance: the approved RTM has no untested in-scope requirement at release approval. | High |
| NFR-ACC-01 | Accessibility | **Proposed:** core flows shall meet WCAG 2.2 AA for keyboard use, labels, focus, contrast, and error identification, including entering coordinates by keyboard. Acceptance: documented audit has no blocking failures. | High |
| NFR-COMP-01 | Compatibility | **Proposed:** core workflows shall work in current and previous major Chrome, Edge, Firefox, and Safari on desktop and mobile. Acceptance: defined browser matrix passes. | Medium |
| NFR-OPS-01 | Recoverability | **Proposed:** production backups run daily, retain 14 daily points, and pass quarterly restore exercise with RPO <=24 hours. Acceptance: restore evidence meets targets. | Medium |
| NFR-OPS-02 | Availability | **Proposed:** public service achieves 99.5% monthly availability excluding announced maintenance. Acceptance: monitoring report meets target. | Medium |

## 8. Security, privacy, and trust requirements

| ID | Requirement | Acceptance criterion |
|---|---|---|
| SEC-01 | Protected objects shall be accessible only to their owner, authorized match participant, or authorized staff role. | Unauthorized role tests deny access and reveal no protected data. |
| SEC-02 | Report contacts shall remain hidden from the other participant until the handover is scheduled, except contact deliberately published through an active personal label. | Pre-acceptance match responses contain no other-party contact; active label displays its configured number. |
| SEC-03 | Report QR flow shall expose only approved public hints and omit private answers, contact number, exact coordinates, and location detail. | Inspect QR flow and seeded draft; prohibited values are absent. |
| SEC-04 | Personal-label bearer tokens shall be stored as digests, and expired/revoked/deactivated labels shall disclose no number. | Persisted label contains no raw token; inactive scan omits contact. |
| SEC-05 | Photos are sensitive personal data. Uploaded photos shall be decoded and re-encoded, stripped of source metadata, and served under the photo-access rule. Release 1.0 shall not run automated visual classification or similarity analysis on report photos. | Image boundary/privacy checks pass, normalized output contains no source metadata, and no Release 1.0 visual analysis is performed. |
| SEC-06 | A public deployment shall use HTTPS, secure session/anti-forgery cookies, explicit allowed hosts, secret configuration, and production-safe response headers. | Deployment review confirms configuration and browser-visible transport/header behavior. |
| SEC-07 | User-facing copy shall state that matching, QR scanning, and account creation do not prove identity, possession, or ownership. | Review confirms notice on relevant match and QR flows. |
| SEC-08 | The system shall reject likely sensitive identifiers in public report text under configured detection rules. | Adversarial cases covered by those rules are rejected; residual limitations are documented. |

The system reduces accidental disclosure but cannot verify truthful claims or guarantee safe physical meetings. Complete identifiers in private answers require minimization/protection approval before production.

## 9. Use cases

| ID | Use case | Primary actor | Related requirements |
|---|---|---|---|
| UC-01 | Register and sign in | Reporter | FR-ACC-01 to 06 |
| UC-02 | Create, review, and publish Lost/Found report | Reporter | FR-REP-01 to 13, FR-VAL-01 to 06, FR-PHO-01 to 04 |
| UC-03 | Save and resume a draft | Reporter | FR-REP-05 to 08, FR-REP-12 |
| UC-04 | Review a possible match | Reporter | FR-MAT-01 to 08 |
| UC-05 | Arrange a handover | Match participant | FR-HND-01 to 06, FR-HND-08 to 09 |
| UC-06 | Record an item returned | Match participant | FR-HND-07, FR-HIS-05 |
| UC-07 | Browse dashboard and report history | Reporter | FR-HIS-01 to 06 |
| UC-08 | Start a Found report from a report QR | Finder | FR-QR-01 to 04, FR-QR-10 |
| UC-09 | Create, deactivate, reactivate, and scan personal label | Reporter, label finder | FR-QR-05 to 09, FR-QR-11 |
| UC-10 | Moderate a report | Moderator | FR-MOD-01 to 05 |

### UC-02 main success flow

1. Reporter selects Lost or Found and enters details, private answers, and optional photo. The reporter must provide a place name, location description, and coordinates, with coordinates supplied by map pin or manual latitude/longitude entry.
2. System saves each valid step as draft progress and shows a review.
3. Reporter submits the review; system validates the entire report and publishes it.
4. System compares the report with eligible opposite-kind reports and creates qualifying matches.

**Exceptions:** Invalid step shows an actionable error and retains draft values. Category change removes inapplicable private answers. An unauthorized or locked report cannot be edited. Failed final validation does not publish.

### UC-05 main success flow

1. Participant opens a possible match and proposes a public place and future time.
2. System reserves both reports and records the proposal.
3. The other participant accepts.
4. System reveals both report contact numbers to the participants and records the scheduled handover.
5. At or after the scheduled time, either participant records the return.
6. System marks both reports Returned, dismisses competing possible matches, and records actor/time events.

**Exceptions:** Nonparticipant requests are denied; proposer cannot accept own proposal; reserved report cannot be used in another proposal; early return is refused; dismissal releases reservation, and only the dismissing participant may later restore the match.

### UC-08 main success flow

Finder scans a Lost-report QR. If signed out, the system requests sign-in. Once authenticated, it starts a Found draft containing only approved public hints; finder completes and submits it. Scanning does not publish automatically or prove possession.

**Exceptions:** The report owner opening their own QR is returned to their report; a closed or reserved source report shows a notice and seeds no draft.

## 10. Open decisions and exclusions

| ID | Decision needed | Affected scope |
|---|---|---|
| OI-01 | Approve the necessity, minimization, protection, retention, and deletion policy for sensitive private answers and report photographs before public/production use. | Section 6.2, NFR-SEC-07, SEC-05 |
| OI-02 | Approve or reject each proposed quality target before it is made a release acceptance gate. Unapproved targets remain non-normative. | UI-04, NFR-PER, NFR-USE-01, NFR-ACC-01, NFR-COMP, NFR-OPS |

Release 1.0 does not specify password reset, profile editing, in-app help, notifications, messaging, or ownership verification. Appendix A is informative future scope only and does not add requirements to this baseline. Public deployment is an operational deployment concern, not an excluded product capability.

## 11. Acceptance and requirement traceability

| Acceptance test | Requirement coverage | Scenario |
|---|---|---|
| AT-01 | FR-ACC-01 to 06, NFR-SEC-01 to 02 | Register (including password validators), authenticate with/without remember-me, sign out, and attempt cross-account or unauthorized actions. |
| AT-02 | UI-02 to 05, FR-REP-01 to 13, FR-VAL-01 to 06 | Complete five-stage reporting; provide required place name and location description and coordinates by map pin and by manual latitude/longitude entry; resume draft; change category and confirm old answers clear; check identifiers/QR UUID; submit invalid data and out-of-range coordinates. |
| AT-03 | FR-PHO-01 to 04, NFR-SEC-02, NFR-SEC-08, SEC-01, SEC-05 | Submit valid, oversized, unsupported, damaged, and unauthorized photo requests; verify owner/match-participant access boundaries, sensitive-media handling, metadata removal, and private/no-store response headers for report photos and label images. |
| AT-04 | FR-MAT-01 to 08, BR-02 to 03 | Test eligible/ineligible pairs, 69/70 score boundary, agreement minimum, unique pair, and private-data display. |
| AT-05 | FR-HND-01 to 09, BR-04 to 06, NFR-REL-01 to 02, NFR-LOC-01 | Propose/accept/dismiss, restore by dismisser and other participant, disclosure timing, concurrency, reservation, return-time boundary, and competing-match dismissal. |
| AT-06 | FR-HIS-01 to 06, FR-MOD-01 to 05 | Check owner-filtered history, ten-item pagination, control-character search rejection, audit attribution, moderator role, state eligibility, and match dismissal on close/removal. |
| AT-07 | FR-QR-01 to 11, SEC-03 to 04 | Scan report and personal labels signed out/in and active/inactive; self-use and closed-source refusal; six-month expiry/deactivate/reactivate; owner-only label image. |
| AT-08 | Approved targets only: NFR-PER, NFR-USE-01, NFR-ACC-01, NFR-COMP, NFR-OPS | Run performance, usability, accessibility, compatibility, availability, and recovery measurements only after the relevant proposed targets are approved and incorporated into the release baseline. |

At release approval, every in-scope High-priority requirement shall map to at least one passing acceptance test. Proposed targets remain non-normative until stakeholder approval incorporates them into the release baseline. Test results, date, environment, and deviations belong in the release test record, not this specification.

## Appendix A. Informative future roadmap (non-normative)

The following are candidate features only. They are not Release 1.0 requirements, are not acceptance gates, and shall not be treated as approved commitments. Each feature requires a separately approved release baseline before implementation or verification against these criteria.

| ID | Release | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-ID-01 | 2.0 | Each published report shall receive a short ID with kind letter and number (L or F). This would replace the Release 1.0 display identifier in FR-REP-13. | Every report shows the approved prefix and numeric suffix. |
| FR-ID-02 | 2.0 | Report IDs shall be unique and never reused. | Closing/removing a report does not allow its ID to be assigned again. |
| FR-ID-03 | 2.0 | The report ID shall appear on report, match, history, and notification views. | One test report's same ID appears consistently in applicable views/messages. |
| FR-ID-04 | 2.0 | Reports shall record event time of day in addition to date. | Valid date/time is stored and displayed in report detail. |
| FR-LIF-01 | 2.0 | The system shall show progress as Lost/Found, Matched, Owner Verified, Handover Scheduled, or Returned according to a future approved status model. | Each underlying state maps to its defined visible status. |
| FR-LIF-02 | 2.0 | Dashboard and history shall show each report's progress status. | Each listed report shows the correct status after each transition. |
| FR-VER-01 | 2.0 | The system shall ask the Lost reporter category-specific ownership challenge questions. | Claimant receives configured questions for that category. |
| FR-VER-02 | 2.0 | The system shall compare claimant answers with Found-report private answers and mark verified after the configured number of agreements. | Correct threshold marks verified; insufficient answers do not. |
| FR-VER-03 | 2.0 | The system shall prevent handover proposal until the match is Owner Verified. | Proposal before verification is denied; after successful verification it is accepted. |
| FR-VER-04 | 2.0 | Verification shall show only verified/not verified without revealing wrong answers or Found answers. | Claimant cannot infer which individual answers were correct. |
| FR-VER-05 | 2.0 | The system shall limit failed verification attempts and lock further attempts for a configured period. | Configured limit triggers lock until expiry. |
| FR-VER-06 | 2.0 | The system shall record each verification attempt, claimant, result, and time. | Each attempt produces an attributable event. |
| FR-NOT-01 | 2.0 | The system shall notify a reporter when a possible match is created. | Each report owner receives a notification identifying the event. |
| FR-NOT-02 | 2.0 | The system shall notify participants when a proposal is made, accepted, rejected, restored, or a message arrives. | Each event generates a notification for affected participants. |
| FR-NOT-03 | 2.0 | A notification shall identify the report and event and contain no private answers or phone numbers. | Templates include the event and omit prohibited data. |
| FR-NOT-04 | 2.0 | In-app notifications shall have read/unread state. | Opening/marking one updates only that recipient's state. |
| FR-NOT-05 | 2.0 | The system should send notifications by email and let users disable email notifications. | Opted-in user receives email; opted-out user does not. |
| FR-MSG-01 | 2.0 | Match participants shall be able to exchange text messages from match details. | Participant can send/read a message associated with the match. |
| FR-MSG-02 | 2.0 | Messages shall be visible only to the two match participants and authorized moderation process. | Unrelated account cannot retrieve message content. |
| FR-MSG-03 | 2.0 | Message text shall pass public-text identifier/control-character screening. | Configured prohibited text is rejected and safe text stored unchanged. |
| FR-MSG-04 | 2.0 | Each message shall record sender and time and appear oldest first. | Test messages display chronologically with correct sender/time. |
| FR-MSG-05 | 2.0 | A participant shall be able to report a message to moderators. | Report action creates a moderation item linked to message without public disclosure. |
| FR-MSG-06 | 2.0 | The system shall close the message thread when match returns or either report is closed/removed. | Closed thread rejects new messages under approved retention policy. |
| FR-SHP-01 | 2.0 | The system shall maintain approved safe handover points with name, address, coordinates, and opening hours. | Authorized staff can maintain a point; required fields precede activation. |
| FR-SHP-02 | 2.0 | Suggested safe handover points shall be ordered by distance from both reports. | Controlled fixture orders points under the approved formula. |
| FR-SHP-03 | 2.0 | Participants shall be able to choose a listed point or enter another public place. | Either selection creates a proposal with that location. |
| FR-SHP-04 | 2.0 | The system shall not suggest a point closed at the proposed time. | Closed point is omitted; open point may be selected. |
| FR-SHP-05 | 2.0 | Moderators shall be able to add, edit, and deactivate safe handover points. | Authorized changes persist; deactivated points are not offered. |
| FR-MAP-01 | Future | A reporter shall be able to view open reports of the opposite kind near a selected point within a chosen radius. | Results contain only open opposite-kind reports inside the radius. |
| FR-MAP-02 | Future | When two possible matches have the same score, the system shall list the report nearer to the reporter-selected point first. | Equal-score candidates are ordered by selected-point distance. |
| FR-MAP-03 | Future | Map views shall use only public report fields. | Map response contains no private answers or contact numbers. |
| FR-ORG-01 | Future | The system shall support an organization administrator role limited to one registered organization. | Administrator accesses only assigned organization. |
| FR-ORG-02 | Future | An organization administrator shall see reports and handovers in the organization's registered area or using approved handover points. | In-scope records are visible; out-of-scope records are denied. |
| FR-ORG-03 | Future | An organization administrator shall be able to close in-scope reports and manage its safe handover points under moderator eligibility rules. | Allowed in-scope actions succeed; out-of-scope/reserved actions fail. |
| FR-ORG-04 | Future | Organization dashboard shall show period-based report counts by kind, category, status, match counts, return share, and median days to return. | Metrics match controlled data for selected period. |
| FR-ORG-05 | Future | Organization analytics shall use aggregate counts only and shall not show private answers, phone numbers, or message text. | Analytics output contains no record-level sensitive data. |
| FR-ORG-06 | Future | Organization administrator shall not open any report, match, or message outside the organization's scope. | Out-of-scope requests are denied without content disclosure. |
| FR-IMG-01 | Future | Subject to separate privacy approval and release authorization, the system may compute visual similarity between photos for opposite-kind reports in the same category. | Similarity is computed only for eligible kinds/categories with photos. |
| FR-IMG-02 | Future | Image similarity shall be optional and shall never create a match on its own. | Without other qualifying score/evidence, similarity alone creates no match. |
| FR-IMG-03 | Future | Photos used for similarity shall remain protected by FR-PHO-04. | Processing does not broaden photo access. |
| FR-NFC-01 | Future | The system may support NFC tags that open a personal-label address and follow its expiry/revocation rules. | NFC scan follows the equivalent QR active/inactive behavior. |
| FR-NET-01 | Future | The system may allow multiple organizations to share a matching pool while retaining scoped administration. | Cross-organization candidates work while admins remain scope-limited. |

## 12. Source basis and revision

This document was aligned against the current implementation: `README.md`, `core/models.py`, `core/forms.py`, `core/services.py`, `core/views.py`, `config/urls.py`, `config/settings.py`, templates, `static/app.js`, image/QR helpers, migrations, and the implementation notes `matching-architecture.md`, `report-structure.md`, `report-wizard-flow.md`, and `osm-integration-guide.md`.

| Version | Change | Approval |
|---|---|---|
| 3.2 | Corrects mandatory location capture alternatives and required location description; aligns review-summary visibility with the wizard; classifies photos as sensitive personal data and strengthens photo/label-image acceptance-test traceability; separates future roadmap from normative Release 1.0 requirements; clarifies proposed quality targets, removes obsolete source-basis wording, and narrows the open approval decisions. | Review pending |

| Approval role | Name | Decision | Date |
|---|---|---|---|
| Project owner |  | Pending |  |
| User/stakeholder representative |  | Pending |  |
| Course reviewer |  | Pending |  |
