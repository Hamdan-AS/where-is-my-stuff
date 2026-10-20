# Software Requirements Specification

## Where Is My Stuff? - Karachi Lost-and-Found Web Application

| Document field | Value |
|---|---|
| Version | 3.1 (review draft) |
| Standard layout | IEEE 29148 style, adapted for this project |
| Product scope | Release 1.0 baseline, with roadmap requirements explicitly labeled |
| Status | For stakeholder review; proposed quality targets and open decisions are not approved commitments |
| Change from 3.0 | Aligned with confirmed implementation behavior. See Section 12. |

## 1. Introduction

### 1.1 Purpose

This document specifies the externally observable requirements for Where Is My Stuff? It supports stakeholder review, design, implementation, and verification. Functional requirements use unique IDs and “shall” statements; each has an acceptance criterion. Requirements describe product behavior rather than source-code organization.

### 1.2 Scope

The system helps people in Karachi publish Lost and Found reports, find plausible opposite-kind reports, and coordinate an in-person return. It includes accounts, resumable report drafts, deterministic matching, report history, QR sharing, time-limited personal QR contact labels, and staff moderation. The service offers leads only: it does not establish real-world identity, possession, or ownership. It does not arrange payment, courier delivery, or police reporting.

### 1.3 Intended readers

Project owner, user/stakeholder representatives, developers, testers, maintainers, and course reviewers.

### 1.4 References

- IEEE Std 29148, Systems and software engineering—Life cycle processes—Requirements engineering.
- “Software Requirements Specification Where Is My Stuff?” supplied project SRS draft.
- “Where Is My Stuff Project Roadmap Initial Plan,” supplied project roadmap.
- CS-326 Software Engineering syllabus and supplied lecture notes, used as supporting course references.

### 1.5 Conventions and definitions

“Shall” denotes a mandatory requirement. Priority is High, Medium, or Low. Release 1.0 describes the current local product scope; Release 2.0 and Future mark proposed roadmap scope, without a delivery-date commitment.

| Term | Meaning |
|---|---|
| Report | A record of one Lost or Found item |
| Reporter | Registered user who owns a report |
| Draft | Unpublished report data saved for later completion |
| Private answers | Category-specific details withheld from public report views |
| Possible match | Lost/Found pair meeting eligibility, private-answer, and score rules |
| Participant | Owner of either report in a match |
| Handover | Agreed meeting place and time between match participants |
| Reserved | A report held by a proposed or scheduled handover, locking editing and moderation |
| Display identifier | Human-readable report label built from kind and database ID (`LFD-...` Lost, `FND-...` Found) |
| Personal label | Time-limited QR bearer link that deliberately displays its owner's phone number while active |
| Moderator | Staff user permitted to close or remove eligible reports |
| Acceptance criterion | Observable result that determines whether a requirement is satisfied |

## 2. Overall description

### 2.1 Product perspective

The product is a standalone browser-based lost-and-found service. It has no dependency on an authoritative lost-property registry, identity provider, payment provider, courier service, or notification provider. It may use a third-party map tile service for location selection. A readable place name is required so that report use does not depend solely on map availability.

### 2.2 Product functions

The system supports account registration and sign-in; creation, saving, resumption, and editing of Lost/Found reports; private category questions; deterministic match suggestions; handover proposal and acceptance; return recording; owner history; report QR sharing; personal QR labels; and staff moderation. Roadmap additions such as messaging, ownership challenge questions, notifications, safe handover points, and organizational dashboards are separately labeled below.

### 2.3 User classes

| User class | Goals and access |
|---|---|
| Reporter | Register, publish and manage own reports, review matches and history |
| Match participant | Coordinate a handover and report a return for a match involving their report |
| Report-QR finder | Sign in and start a Found draft from selected public hints |
| Personal-label finder | Scan an active label and view the phone number intentionally published by its owner |
| Moderator | Review, close, or remove eligible reports |
| Organization administrator | Future role; manage scoped reports, handover points, and aggregate statistics |

### 2.4 Operating environment

Current scope is a mobile- and desktop-browser web application. Users need internet access for the service and map imagery. The service requires a relational data store (SQLite for local use, PostgreSQL supported) and private media storage for photographs and QR images. Application time uses the `Asia/Karachi` timezone. Public deployment requires HTTPS and an agreed operational environment.

### 2.5 Constraints

| ID | Constraint |
|---|---|
| CON-01 | The product shall be a web application; a native mobile application is out of scope. |
| CON-02 | Matching shall be deterministic and rule-based; machine-learning or LLM ranking is out of scope for Release 1.0. |
| CON-03 | Release 1.0 shall target Karachi; places shall have readable names and coordinates. |
| CON-04 | No report, match score, verification result, or QR scan shall be represented as proof of identity, possession, or ownership. |

### 2.6 Assumptions and dependencies

Users provide accurate information, have an email account, and choose a safe public meeting place. Map imagery may be unavailable. Browser geolocation needs browser support, permission, and a secure context. A reachable phone number is needed for a handover. The service cannot enforce physical-world safety or truthfulness of reports.

## 3. External interface requirements

### 3.1 User interface

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| UI-01 | The system shall provide pages for registration, sign-in, dashboard, report wizard, history, match details, QR labels, and staff moderation. | High | A user with the applicable role can navigate to each listed function; protected pages disclose no data to signed-out users. |
| UI-02 | The report wizard shall present Type, Details, Location, Matching, and Review in that order. | High | A new reporter sees all five stages in order; an incomplete prerequisite prevents skipping ahead. |
| UI-03 | The location interface shall accept a typed place name, shall permit map-based point selection where map service is available, and shall keep editable latitude and longitude fields so the map is not the only input path. | High | A valid place name and manually typed coordinates can be submitted without map imagery; when imagery is available a point can be selected and reviewed. |
| UI-04 | The core reporting flow shall fit a 360-pixel-wide viewport without horizontal page scrolling. | Medium | At 360 CSS-pixel viewport, all required fields and actions are reachable without horizontal scrolling. |
| UI-05 | Validation errors shall identify the relevant field and preserve previously entered valid values. | High | Invalid submission displays an actionable field-level message and restores other submitted values. |

### 3.2 Hardware interfaces

No dedicated hardware is required. A phone camera and a standard QR scanner may be used by the user.

### 3.3 Software interfaces

| Interface | Requirement |
|---|---|
| Relational data store | Persist account, report, draft, match, event, verification, message, notification, label, and organization data as applicable to release scope. |
| Private media storage | Store report photographs and QR images and enforce the privacy requirements in Section 8. |
| Map tile service | May supply map imagery; its failure shall not prevent manual place-name entry. It is not an authoritative source of report truth. |
| QR reader | A standards-compliant scanner shall open encoded report or personal-label addresses in a browser. |

### 3.4 Communications interfaces

User traffic shall use HTTP(S). A public deployment shall use HTTPS for every page. State-changing requests shall include an anti-forgery token. Session and anti-forgery credentials shall not be exposed in page content or public QR data.

## 4. System features and functional requirements

### 4.1 Accounts and access

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-ACC-01 | The system shall let a visitor register with a name, unique email address, and a password that satisfies the configured password validators. | High | Valid unused credentials create one account and sign the user in; a duplicate email or a password failing the validators creates none and produces an error. |
| FR-ACC-02 | The system shall authenticate a registered user using email address and password and offer a remember-me session choice. | High | Valid credentials establish a session; invalid credentials establish none. The remember-me choice controls session expiry. |
| FR-ACC-03 | The system shall allow an authenticated user to sign out. | High | After sign-out, a protected request requires authentication. |
| FR-ACC-04 | The system shall require authentication for protected reports, drafts, matches, history, dashboard, and label management. | High | A signed-out request discloses no protected data and asks the visitor to authenticate. |
| FR-ACC-05 | The system shall restrict report/draft actions to the owner, match actions to participants, and moderation actions to staff. | High | An actor lacking the required relationship/role is denied and the record remains unchanged. |
| FR-ACC-06 | The system shall reject state-changing requests without valid anti-forgery protection. | High | A request with a missing or invalid token is rejected without changing data. |

### 4.2 Reports and drafts

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-REP-01 | The system shall let an authenticated user create a Lost or Found report. | High | User can select either report kind; all later report behavior preserves that selection. |
| FR-REP-02 | A report shall record category, title, event date, public description, contact phone, place name, latitude, and longitude. Coordinates are required to publish. | High | Valid values appear on the owner's report; missing or invalid mandatory data, including coordinates, prevents publication. |
| FR-REP-03 | A report shall include a location description and may include one photograph. | Medium | Publication requires a valid location description; a photograph may be omitted or, when supplied, is associated with the report. |
| FR-REP-04 | The system shall ask category-appropriate private questions and store answers with the report. | High | Each supported category presents applicable questions; required answers are validated before publication. |
| FR-REP-05 | The system shall save draft progress whenever a valid wizard step is submitted. | High | After submitting a valid step and leaving the flow, the draft contains that step’s values. |
| FR-REP-06 | The system shall let the owner resume a saved draft and restore all previously saved fields. | High | Given values saved through step 3, resuming restores those values in steps 1–3. |
| FR-REP-07 | The system shall require confirmation before discarding an existing draft to start another. | Medium | Cancel preserves the draft; confirmation discards it and starts a new draft. |
| FR-REP-08 | A user shall not be able to read, edit, or delete another user’s draft. | High | A different account receives denial/not-found and cannot alter or infer draft contents. |
| FR-REP-09 | The review step shall show the report’s public fields and keep private answers visible only to its owner. | High | Owner review contains public values; another user’s view contains no private answer values. |
| FR-REP-10 | The system shall let an owner edit an open report that is not reserved for handover. | Medium | Eligible report can be edited; closed or reserved report cannot be changed. |
| FR-REP-11 | The system shall run matching after a report is published. | High | A newly published report is evaluated against eligible opposite-kind reports and resulting qualifying matches are available to participants. |
| FR-REP-12 | When a draft's category is changed, the system shall clear private answers that belong to the previous category. | Medium | After a category change, answer keys of the old category appear in neither the revised draft nor the review. |
| FR-REP-13 | Each report shall have a display identifier built from its kind and database ID (`LFD-...` for Lost, `FND-...` for Found) and a separate random UUID used in report QR URLs. The database ID shall not appear in QR URLs. | Medium | A published Lost report shows an `LFD-` identifier and a Found report an `FND-` identifier; the report QR URL contains only the UUID. |

### 4.3 Input validation and photos

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-VAL-01 | The system shall reject public title, place, location-description, or report-description text that matches configured private-identifier patterns. | High | Test identifiers within the configured detection rules are rejected; submitted text is not silently rewritten. |
| FR-VAL-02 | The system shall reject public text containing invisible or control characters. | High | Submitted control/invisible characters cause a field error and no publication. |
| FR-VAL-03 | When text is rejected, the system shall explain the validation failure and preserve the submitted text for correction. | High | The user sees an actionable error and can edit the unchanged submitted value. |
| FR-VAL-04 | The system shall require the reported event date not to be in the future and not before 1 January 2000. | Medium | A future date or a date before 1 January 2000 is rejected; today or an allowed past date is accepted. |
| FR-VAL-05 | The system shall require latitude and longitude to fall within valid geographic ranges (latitude -90 to 90, longitude -180 to 180). The system does not restrict points to a service-area boundary. | Medium | A point inside valid ranges is accepted; a point outside them is refused. |
| FR-VAL-06 | The system shall render user-entered text as data rather than executable markup or script. | High | Script/markup test strings render inertly in report, match, history, and staff views. |
| FR-PHO-01 | The system shall accept a photo only if its file type, size, and pixel dimensions are within configured limits. | Medium | A valid in-limit photo is accepted; each out-of-limit sample is refused without losing other draft data. |
| FR-PHO-02 | The system shall decode each uploaded image and reject damaged or non-image files. | Medium | Renamed non-image and corrupted image files are refused. |
| FR-PHO-03 | The system shall normalize accepted photos to JPEG, resize the longest edge to at most 1,800 pixels, and discard source metadata before storage. | Medium | Retrieved image is JPEG, is no larger than 1,800 pixels on its longest edge, and carries no source metadata. |
| FR-PHO-04 | The system shall serve report photographs only to the report owner and an owner of the opposite report in a match involving that report. | High | Authorized requests return the image; unrelated/anonymous requests return no image bytes. |

### 4.4 Matching

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-MAT-01 | The system shall consider only reports owned by different users, of opposite kind, both open and unreserved, and in the same category. | High | Any pair violating one condition creates no possible match; an otherwise eligible pair proceeds to scoring. |
| FR-MAT-02 | The system shall require at least two meaningful private-answer agreements for a possible match. | High | Fewer than two agreements produce no match even when all other factors score maximally. |
| FR-MAT-03 | The system shall score an eligible pair from 0 to 100 using category (20), location (20), date (15), description (15), and private answers (30). | High | Controlled factor fixtures produce the documented weighted sum, always between 0 and 100. |
| FR-MAT-04 | The system shall create a possible match only when its score is at least 70. | High | Score 69 creates none; score 70 with at least two private agreements creates one. |
| FR-MAT-05 | The system shall store each match’s score and factor scores. | High | Match detail displays the correct factor totals for the test pair. |
| FR-MAT-06 | The system shall create at most one match for a given Lost/Found report pair. | High | Repeated publication/recalculation of the same pair does not create duplicate matches. |
| FR-MAT-07 | The match page shall show which factors agreed without exposing the other party’s private-answer values. | High | Participants can see factor agreement; raw private responses remain absent. |
| FR-MAT-08 | The match page shall state that a match is not proof of ownership. | High | The notice is visible on each match detail page. |

### 4.5 Handover and return

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-HND-01 | A participant shall be able to propose a meeting place and future time for a match. | High | A non-empty place and future time create a proposal; blank or non-future time is refused without reservation. |
| FR-HND-02 | The other participant shall be able to accept the pending proposal. Either participant may dismiss a possible match or a pending proposal. | High | The non-proposer's acceptance schedules the handover. Dismissal sets the match to Rejected and releases any reservation. Both are recorded. |
| FR-HND-03 | The proposer shall not accept their own proposal as the second participant. | High | Proposer acceptance is refused and state remains pending. |
| FR-HND-04 | Only the participant who dismissed a suggestion shall be able to restore it, and only if neither report is reserved and the pair still meets the current match rules. | Low | The dismissing participant restores an eligible pair; the other participant cannot restore it; a stale, ineligible, or conflicting pair remains rejected. |
| FR-HND-05 | Once a handover is scheduled or returned, the system shall show each participant the other's saved contact phone number. | High | After the other participant accepts, both authorized participants see the number; it remains visible when the match is Returned. |
| FR-HND-06 | Before the handover is scheduled, the system shall not show either party's saved phone number through the match. | High | Neither participant can retrieve the other's number before acceptance. |
| FR-HND-07 | A participant shall be able to record return only at or after the scheduled meeting time. On return, both reports become Returned, reservations are cleared, and competing possible matches of those reports are dismissed. | High | Return one second before scheduled time fails; at or after that time it succeeds, both reports become Returned, and no competing possible match of either report remains active. |
| FR-HND-08 | While a handover is active, the system shall reserve its reports against editing, removal, or a second active handover. | High | Competing concurrent proposals yield at most one active reservation; edit/remove attempts fail while reserved. |
| FR-HND-09 | Only a participant of a match shall be able to view or change its state. | High | Nonparticipant read and action requests are denied without disclosure or state change. |

### 4.6 History and dashboard

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-HIS-01 | The dashboard shall show the signed-in user’s open reports, drafts, and active matches. | High | Each owned item appears with current state; another user’s items do not appear. |
| FR-HIS-02 | The history page shall list the user's non-Removed reports and support search by text and filters for kind and status. | Medium | Combined query and filters return only matching records owned by that user. |
| FR-HIS-03 | The history page shall divide long lists into pages of ten reports. | Low | More than ten records are accessible across numbered/next pages. |
| FR-HIS-04 | The user shall see only their own reports in dashboard and history. | High | Two-account fixture demonstrates strict owner separation. |
| FR-HIS-05 | The system shall record actor and time for report publication, edit, match, close, removal, and return events. | Medium | Each specified action produces an event containing its actor and timestamp. |
| FR-HIS-06 | The system shall reject history search strings that contain invisible or control characters. | Medium | Such a query returns a client error and exposes no additional report data. |

### 4.7 Report QR and personal labels

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-QR-01 | The system shall generate a QR code for an eligible Lost report, encoding its UUID URL. | Medium | Scanning the generated code opens the associated Lost-report entry; the database ID does not appear in the URL. |
| FR-QR-02 | A signed-in finder opening the report QR shall be able to start a Found draft prefilled with selected public Lost-report hints (kind, category, title, and coarse place). | Medium | Draft contains the approved hints and remains unpublished until the finder completes submission. Exact coordinates, location description, private answers, and contact are not copied. |
| FR-QR-03 | The report QR shall not reveal private answers or the owner's phone number. | High | QR destination and encoded content contain neither private answer nor contact number. |
| FR-QR-04 | A signed-out finder opening the report QR shall be asked to sign in before report hints are copied. | Medium | Before sign-in no draft or protected seed data is disclosed; after sign-in eligible hints may be copied. |
| FR-QR-05 | A user shall be able to create a personal label with an item name and phone number. The label's expiry is fixed at six months after creation. | Medium | A created label has an expiry six months after creation; a scan after that time displays no phone number. The user cannot choose another expiry. |
| FR-QR-06 | The system shall store only a non-reversible digest of each personal-label bearer token. | High | Persisted label record contains no raw token; token resolution still works. |
| FR-QR-07 | Scanning an active personal label shall show the phone number its owner chose to publish. | Medium | Active, unexpired, unrevoked token displays its associated number. |
| FR-QR-08 | Scanning an expired, revoked, or deactivated label shall not show a phone number. | High | All three inactive conditions suppress the number. |
| FR-QR-09 | A user shall be able to deactivate a personal label at any time and to reactivate it. Reactivation extends the expiry by six months. | Medium | Deactivation immediately prevents subsequent scans from displaying contact. After reactivation the printed code resolves again and the expiry is six months later. |
| FR-QR-10 | The system shall refuse self-use of a report QR and shall show a notice when the source report is closed or reserved. | Medium | The report owner opening their own QR is returned to their own report. A closed or reserved source report seeds no Found draft and shows a notice. |
| FR-QR-11 | The label owner shall be able to view and download the label's QR image. Other accounts shall not be able to access it. | Medium | The owner receives the image; a non-owner receives denial or not-found. |

### 4.8 Moderation

| ID | Requirement | Priority | Acceptance criterion |
|---|---|---|---|
| FR-MOD-01 | The system shall provide moderators with a report-management list of non-Removed reports. | Medium | Authorized moderator can access the list of manageable reports; Removed reports are absent. |
| FR-MOD-02 | A moderator shall be able to close or remove an open report that is not reserved. Closing or removing shall dismiss the report's possible matches. | Medium | Eligible report changes state and its possible matches become Rejected; closed, removed, or reserved report action is refused. A Removed report leaves the ordinary history and management lists. |
| FR-MOD-03 | The management list shall not show private answers. | High | Private answer values do not appear in management output. |
| FR-MOD-04 | Each moderation action shall record the acting moderator and event time. | Medium | Resulting event identifies the moderator and timestamp. |
| FR-MOD-05 | A non-staff user shall be denied access to management functions. | High | Non-staff request is denied without exposing the management list. |

### 4.9 Roadmap requirements (not Release 1.0 commitments)

Requirements in this subsection are included for scope traceability only. Their acceptance criteria apply only if the corresponding release is approved.

| ID | Release | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-ID-01 | 2.0 | Each published report shall receive a short ID with kind letter and number (L or F). | Every published Lost/Found report shows an ID with the correct prefix and numeric suffix. |
| FR-ID-02 | 2.0 | Report IDs shall be unique and never reused. | Closing/removing a report does not allow its ID to be assigned again. |
| FR-ID-03 | 2.0 | The report ID shall appear on report, match, history, and notification views. | One test report’s same ID appears consistently in all applicable views/messages. |
| FR-ID-04 | 2.0 | Reports shall record event time of day in addition to date. | Valid date/time is stored and displayed in the report detail. |
| FR-LIF-01 | 2.0 | The system shall show progress as Lost/Found, Matched, Owner Verified, Handover Scheduled, or Returned according to BR-07. | Each underlying match/report state maps to exactly its defined visible status. |
| FR-LIF-02 | 2.0 | Dashboard and history shall show each report’s progress status. | Each listed report shows the correct status after each state transition. |
| FR-VER-01 | 2.0 | The system shall ask the Lost reporter category-specific ownership challenge questions. | Claimant receives the configured questions for that report category. |
| FR-VER-02 | 2.0 | The system shall compare claimant answers with the Found report’s private answers and mark verified after the configured number of agreements. | Correct answer threshold changes match to Owner Verified; insufficient answers do not. |
| FR-VER-03 | 2.0 | The system shall prevent handover proposal until the match is Owner Verified. | Proposal before verification is denied; after successful verification it is accepted. |
| FR-VER-04 | 2.0 | The system shall show verification only as verified/not verified, without revealing wrong answers or Found answers. | Claimant cannot infer which answers were correct from result or response content. |
| FR-VER-05 | 2.0 | The system shall limit failed verification attempts and lock further attempts for a configured period. | Attempt at configured limit triggers lock; requests are rejected until lock expiry. |
| FR-VER-06 | 2.0 | The system shall record each verification attempt, claimant, result, and time. | Each attempt produces a corresponding attributable event. |
| FR-NOT-01 | 2.0 | The system shall notify a reporter when a possible match is created. | Each report owner receives a notification identifying the match event. |
| FR-NOT-02 | 2.0 | The system shall notify participants when a proposal is made, accepted, rejected, restored, or a message arrives. | Each event generates a notification for the affected participant. |
| FR-NOT-03 | 2.0 | A notification shall identify the report and event and contain no private answers or phone numbers. | Inspection of every notification template finds the identifying event and no prohibited data. |
| FR-NOT-04 | 2.0 | In-app notifications shall have read/unread state. | Opening or marking a notification updates its state for its recipient only. |
| FR-NOT-05 | 2.0 | The system should send notifications by email and let the user disable email notifications. | Opted-in user receives email; opted-out user does not. |
| FR-MSG-01 | 2.0 | Match participants shall be able to exchange text messages from match details. | Participant can send and read a message associated with the match. |
| FR-MSG-02 | 2.0 | Messages shall be visible only to the two match participants and authorized moderation process. | Unrelated account cannot retrieve message content. |
| FR-MSG-03 | 2.0 | Message text shall pass the public-text identifier/control-character screening. | Configured prohibited text is rejected and safe text is stored unchanged. |
| FR-MSG-04 | 2.0 | Each message shall record sender and time and appear oldest first. | Two test messages are displayed in chronological order with correct sender/time. |
| FR-MSG-05 | 2.0 | A participant shall be able to report a message to moderators. | Report action creates a moderation item linked to the message without exposing it publicly. |
| FR-MSG-06 | 2.0 | The system shall close the message thread when match returns or either report is closed/removed. | A closed thread rejects new messages and remains readable only under approved retention policy. |
| FR-SHP-01 | 2.0 | The system shall maintain approved safe handover points with name, address, coordinates, and opening hours. | Moderator can maintain a point; required fields are present before activation. |
| FR-SHP-02 | 2.0 | Suggested safe handover points shall be ordered by distance from both reports. | Controlled fixture orders nearer point before farther point under the approved distance formula. |
| FR-SHP-03 | 2.0 | Participants shall be able to choose a listed point or enter another public place. | Either selection creates a proposal with the chosen location. |
| FR-SHP-04 | 2.0 | The system shall not suggest a point closed at the proposed time. | A closed point is omitted for that time; an open point may be selected. |
| FR-SHP-05 | 2.0 | Moderators shall be able to add, edit, and deactivate safe handover points. | Authorized changes persist; deactivated points are not offered for new proposals. |
| FR-MAP-01 | Future | A reporter shall be able to view open reports of the opposite kind near a selected point within a chosen radius. | Results contain only open opposite-kind reports inside the selected radius. |
| FR-MAP-02 | Future | When two possible matches have the same score, the system shall list the report nearer to the reporter-selected point first. | For equal-score candidates at different distances from the selected point, the nearer candidate appears first. |
| FR-MAP-03 | Future | Map views shall use only public report fields. | Map response contains no private answers or contact phone numbers. |
| FR-ORG-01 | Future | The system shall support an organization administrator role limited to one registered organization. | Administrator can access only the organization assigned to that account. |
| FR-ORG-02 | Future | An organization administrator shall see reports and handovers in the organization's registered area or using its approved handover points. | In-scope records are visible and out-of-scope records are denied. |
| FR-ORG-03 | Future | An organization administrator shall be able to close in-scope reports and manage the organization's safe handover points under moderator eligibility rules. | Allowed actions succeed for in-scope eligible records; out-of-scope or reserved actions fail. |
| FR-ORG-04 | Future | The organization dashboard shall show period-based report counts by kind, category, and status, match counts, return share, and median days to return. | Each displayed metric matches a controlled data fixture and selected period. |
| FR-ORG-05 | Future | Organization analytics shall use aggregate counts only and shall not show private answers, phone numbers, or message text. | Analytics output contains no record-level personal or private data. |
| FR-ORG-06 | Future | An organization administrator shall not open any report, match, or message outside the organization's scope. | Out-of-scope object request is denied without disclosing content. |
| FR-IMG-01 | Future | The system may compute visual similarity between photos for opposite-kind reports in the same category. | Similarity is computed only for reports that satisfy the stated kind/category conditions and have photos. |
| FR-IMG-02 | Future | Image similarity shall be an optional factor used only when both reports have a photo and shall never create a match on its own. | Removing all other qualifying score/evidence leaves no match regardless of image similarity. |
| FR-IMG-03 | Future | Photos used for similarity shall remain protected by FR-PHO-04. | Image processing and results do not make either photo available to unauthorized users. |
| FR-NFC-01 | Future | The system may support NFC tags that open a personal-label address and follow its expiry/revocation rules. | NFC scan resolves to same active/inactive behavior as its equivalent QR label. |
| FR-NET-01 | Future | The system may allow multiple organizations to share a matching pool while retaining scoped administration. | Cross-organization candidate matching works while administrators remain restricted to their own scope. |

## 5. Business rules

| ID | Rule |
|---|---|
| BR-01 | A match or QR scan is only a lead; it shall never change a report to Returned without a participant recording return. |
| BR-02 | Release 1.0 match score is the sum of category (20), location (20), date (15), description (15), and private-answer agreement (30). The total shall not exceed 100. |
| BR-03 | A candidate pair requires a score of at least 70 and at least two meaningful private-answer agreements. |
| BR-04 | A match transitions through Possible Match, Handover Proposed, Handover Scheduled, and Returned. Dismissal moves it to Rejected, which only the dismissing participant may restore, and only if the pair is still eligible and unreserved. |
| BR-05 | A report is Open until Closed, Removed, or Returned. Only open, unreserved reports are considered for new matches. |
| BR-06 | Match contact numbers are revealed only once the other participant has accepted the same handover (scheduled or returned). An active personal label separately reveals the number its owner chose to publish. |
| BR-07 | Roadmap status path: Lost/Found means open with no match; Matched means Possible Match; Owner Verified means challenge passed; Handover Scheduled means accepted proposal; Returned means participant-confirmed return. |
| BR-08 | Roadmap matching weights conflict with BR-02 by proposing time and image factors and removing private answers. A revised scoring scheme requires an approved decision and revised tests before implementation. |
| BR-09 | A report is reserved while a handover is proposed or scheduled. Reserved reports cannot be edited, removed, or moderated. |

### 5.1 Score interpretation

| Factor | Maximum | Rule |
|---|---:|---|
| Category | 20 | Full points for exact category match |
| Location | 20 | Haversine distance: <0.5 km: 20; <1 km: 15; <2 km: 10; <5 km: 5; otherwise 0. Missing coordinates score 0. |
| Date | 15 | Absolute difference in days: 0 days: 15; 1 day: 10; 2–3 days: 5; otherwise 0. |
| Description | 15 | Jaccard overlap of lowercased alphanumeric tokens of at least three characters, after removing configured stop words; score is rounded `15 × intersection / union`. Empty token union scores 0. |
| Private answers | 30 | Applicable normalized answers agree when trimmed, case-insensitive values match. Configured non-evidence/placeholders are ignored. Bank issuer/suffix pairs are compared as pairs regardless of entry order. Score is rounded proportion of agreeing evidence; at least two meaningful agreements are also required. |

## 6. Data requirements

### 6.1 Logical data dictionary

| Entity | Principal data | Visibility and relationship |
|---|---|---|
| User | email, password hash, display name, staff role | Owns reports, drafts, labels; password is never stored in plaintext |
| Report | owner, kind, category, title, date/time, public text, phone, place, coordinates, photo, status, private answers, public UUID, display identifier | One owner; private answers restricted; may participate in matches; display identifier derives from kind and database ID |
| Draft | owner, entered report data, current step, optional report being edited | Owner only; removed or finalized according to draft lifecycle |
| Match | Lost report, Found report, score, factor breakdown, state, proposer, meeting data, return time | Exactly two report participants; one record per pair |
| Event | report, actor, event kind, time | Attributable history entry for report/workflow actions |
| Personal label | owner, item name, phone, token digest, QR image, expiry, active/revoked state | Public number only while active; raw token is not persisted; image is owner-only |
| Verification attempt (2.0) | match, claimant, outcome, timestamp | Restricted; attempts count toward configured limit |
| Message (2.0) | match, sender, text, timestamp | Participants only; lifecycle and retention policy required |
| Notification (2.0) | recipient, report, event type, read state, timestamp | Recipient only; no private answers or phone numbers |
| Safe handover point (2.0) | name, address, coordinates, hours, active state | Managed by authorized staff |
| Organization (Future) | name, registered area, administrators | Defines administrative scope |

### 6.2 Sensitive-data requirement

Some current category questions request a complete national identity or bank-card number. That collection is a high-impact privacy decision. Before production use, the owner shall approve necessity, minimization, protection, retention, and deletion. Prefer issuer, presence, or short suffix evidence where it can satisfy matching need. See NFR-008 and open decisions in Section 10.

### 6.3 Report input boundaries

| Data | Constraint |
|---|---|
| Report kind | Lost or Found |
| Category | Wallet / Purse; Cards / IDs; Keys; Electronics; Bag; Documents; Cash / Money; Other |
| Title | Required; maximum 120 characters; likely personal identifiers rejected |
| Public description | Required; maximum 2,000 characters; likely contact/account identifiers rejected |
| Contact phone | Eleven digits beginning with 0 |
| Event date | Not in the future; earliest supported date is 1 January 2000 |
| Place name | Required readable text; maximum 100 characters |
| Location description | Required; maximum 255 characters; public-text screening applies |
| Latitude/longitude | Required to publish. Valid geographic decimal coordinates (latitude -90 to 90, longitude -180 to 180); no service-area boundary is enforced. |
| Photo | Optional JPEG, PNG, or WebP; maximum 5 MiB, 6,000 pixels per side, and 24 megapixels; damaged or non-image content rejected |
| Handover place | Required readable public place; maximum 255 characters |
| Handover time | Must be in the future in Asia/Karachi local time when proposed |
| Personal-label item name | Maximum 80 characters |
| Personal-label phone | Eleven digits beginning with 0; expiry is fixed at six months after creation and extends by six months on reactivation |

## 7. Non-functional requirements

“Proposed” thresholds are targets for approval and measurement; they are not claims of achieved performance.

| ID | Category | Requirement and acceptance criterion | Priority |
|---|---|---|---|
| NFR-SEC-01 | Security | Every protected page/action shall require a valid authenticated session. Acceptance: signed-out request reveals no protected content. | High |
| NFR-SEC-02 | Security | Every protected object access shall enforce owner/participant/staff scope. Acceptance: cross-account access matrix denies all unauthorized reads/actions. | High |
| NFR-SEC-03 | Security | Every state-changing browser form shall require anti-forgery protection. Acceptance: absent/invalid token is rejected with no state change. | High |
| NFR-SEC-04 | Security | State transitions shall be authorized and validated at the time of the request. Acceptance: stale UI state cannot bypass current eligibility/reservation checks. | High |
| NFR-SEC-05 | Privacy | Private answers shall not appear in pages, responses, notifications, or logs visible to another user or moderator. Acceptance: role-based output review finds none. | High |
| NFR-SEC-06 | Privacy | Secrets and credentials shall be supplied through protected deployment configuration, not committed source. Acceptance: release security review finds no live secret in distributable source. | High |
| NFR-SEC-07 | Data protection | Before production, the owner shall approve minimization, protection, retention, and deletion of sensitive answer data. Acceptance: policy is approved and verified against collected fields. | High |
| NFR-REL-01 | Reliability | Publishing a report, generating matches, and changing handover state shall complete fully or not at all. Acceptance: induced failure leaves no partial state. | High |
| NFR-REL-02 | Reliability | Concurrent proposals involving the same report shall permit at most one active reservation. Acceptance: concurrent test yields one winner and a clear rejection for others. | High |
| NFR-REL-03 | Reliability | A Lost/Found pair shall have at most one match, and a score shall never exceed 100, both enforced by the database. Acceptance: repeated and concurrent match generation leaves one pair record; an out-of-range score is refused. | High |
| NFR-REL-04 | Reliability | Persistent schema changes shall be delivered through versioned migrations. Acceptance: a clean install and prior-version upgrade both reach the declared schema. | Medium |
| NFR-SEC-08 | Media security | Photo and label image files shall be served only through authorization-aware views, never a public media URL, and responses shall be private and marked `no-store`. Acceptance: an unauthorized or anonymous request returns no image, and authorized responses carry private, no-store cache headers. | High |
| NFR-LOC-01 | Localization | User-facing dates and meeting-time behavior shall use the `Asia/Karachi` timezone. Acceptance: a meeting time entered in local time is stored, compared against now, and displayed in `Asia/Karachi` time. | Medium |
| NFR-PER-01 | Performance | **Proposed:** with up to 1,000 open reports on agreed reference hardware, 95% of ordinary page loads shall complete within 2 seconds, excluding map tiles. Acceptance: load test meets threshold. | Medium |
| NFR-PER-02 | Performance | **Proposed:** matching after publication shall finish within 5 seconds with up to 1,000 open reports. Acceptance: benchmark meets threshold. | Medium |
| NFR-USE-01 | Usability | **Proposed:** in a moderated test, at least 8 of 10 first-time participants shall publish a report without assistance, and median completion time shall not exceed 5 minutes. Acceptance: observed success reaches 8/10 and median time is at most 5 minutes. | Medium |
| NFR-USE-02 | Usability | Text fields shall have visible labels and errors shall say what to fix. Acceptance: review confirms every core form field label and actionable error. | Medium |
| NFR-USE-03 | Usability | Place input shall accept free-text Karachi place names without a map selection. Acceptance: submit valid typed location when tile service is unavailable. | High |
| NFR-MNT-01 | Maintainability | Matching, state-transition, and moderation rules shall be independently verifiable from page rendering. Acceptance: rule-level tests can exercise behavior without browser interaction. | Medium |
| NFR-MNT-02 | Testability | Each High-priority FR shall have at least one acceptance test; all other FRs shall have a test before their release. Acceptance: RTM has no untested in-scope requirement at release approval. | High |
| NFR-ACC-01 | Accessibility | **Proposed:** core flows shall meet WCAG 2.2 AA for keyboard use, labels, focus, contrast, and error identification, including entering coordinates by keyboard without the map. Acceptance: documented audit has no blocking failures. | High |
| NFR-COMP-01 | Compatibility | **Proposed:** core workflows shall work in current and previous major Chrome, Edge, Firefox, and Safari on desktop and mobile. Acceptance: defined browser matrix passes. | Medium |
| NFR-OPS-01 | Recoverability | **Proposed:** production database backups shall run daily, retain 14 daily points, and pass a quarterly restore exercise with recovery point no older than 24 hours. Acceptance: restore evidence meets targets. | Medium |
| NFR-OPS-02 | Availability | **Proposed:** public service shall achieve 99.5% monthly availability excluding announced maintenance. Acceptance: monitoring report meets target for the measured month. | Medium |

## 8. Security, privacy, and trust requirements

| ID | Requirement | Acceptance criterion |
|---|---|---|
| SEC-01 | Protected objects shall be accessible only to their owner, authorized participant, or authorized staff role. | Unauthorized role tests deny access and reveal no protected data. |
| SEC-02 | Contact details shall remain hidden until mutual handover acceptance, except contact deliberately published through an active personal label. | Pre-acceptance match responses contain no contact; active label displays only its own configured number. |
| SEC-03 | Report QR data shall include only approved public hints and shall omit private answers, contact number, and exact coordinates. | Decode/inspect QR and seeded draft; prohibited values are absent. |
| SEC-04 | Personal-label bearer tokens shall be stored as digests, and expired/revoked/deactivated labels shall disclose no number. | Stored data contains no raw token; each inactive scan omits contact. |
| SEC-05 | Uploaded photos shall be decoded and re-encoded, stripped of source metadata, and served under the photo-access rule. | Image boundary/privacy tests pass and metadata inspection shows normalized output. |
| SEC-06 | A public deployment shall use HTTPS, secure session/anti-forgery cookies, explicit allowed hosts, secret configuration, and production-safe response headers. | Security review confirms deployment configuration and browser-visible transport/header behavior. |
| SEC-07 | User-visible copy shall state that matching, QR scanning, and account creation do not prove identity, possession, or ownership. | Review confirms notice on relevant match and QR flows. |
| SEC-08 | The system shall reject likely sensitive identifiers in public report text under the configured detection rules. | Adversarial field cases are rejected; residual detection limitations are documented. |

The system reduces accidental disclosure but cannot verify truthful claims or guarantee safe physical meetings. Full identifiers in private answers require minimization/protection approval before production.

## 9. Use cases

| ID | Use case | Primary actor | Related requirements |
|---|---|---|---|
| UC-01 | Register and sign in | Reporter | FR-ACC-01 to 06 |
| UC-02 | Create, review, and publish Lost/Found report | Reporter | FR-REP-01 to 13, FR-VAL-01 to 06, FR-PHO-01 to 04 |
| UC-03 | Save and resume a draft | Reporter | FR-REP-05 to 08, FR-REP-12 |
| UC-04 | Review a possible match | Reporter | FR-MAT-01 to 08 |
| UC-05 | Arrange a handover | Match participant | FR-HND-01 to 06, FR-HND-08 to 09 |
| UC-06 | Record an item returned | Match participant | FR-HND-07, FR-HIS-05 |
| UC-07 | Browse report dashboard and history | Reporter | FR-HIS-01 to 06 |
| UC-08 | Start a Found report from a report QR | Finder | FR-QR-01 to 04, FR-QR-10 |
| UC-09 | Create, deactivate, reactivate, and scan personal label | Reporter, label finder | FR-QR-05 to 09, FR-QR-11 |
| UC-10 | Moderate a report | Moderator | FR-MOD-01–05 |

### UC-02 main success flow

1. Reporter selects Lost or Found and enters details, location, private answers, and optional photo.
2. System saves each valid step as draft progress and shows a review.
3. Reporter submits the review; system validates the entire report and publishes it.
4. System compares the report with eligible opposite-kind reports and creates qualifying matches.

**Exceptions:** Invalid step shows an actionable error and retains draft values. Category change removes inapplicable private answers. An unauthorized or locked report cannot be edited. Failed final validation does not publish.

### UC-05 main success flow

1. Participant opens a possible match and proposes a public place and future time.
2. System reserves both reports and records the proposal.
3. The other participant accepts.
4. System reveals contact numbers to both participants and records the scheduled handover.
5. At or after the scheduled time, either participant records the return.
6. System marks both reports Returned, dismisses competing possible matches, clears reservations, and records actor/time events.

**Exceptions:** Nonparticipant requests are denied; proposer cannot accept own proposal; reserved report cannot be used in another proposal; early return is refused; dismissal releases the reservation, and only the dismissing participant may later restore the match.

### UC-08 main success flow

Finder scans a Lost-report QR. If signed out, the system requests sign-in. Once authenticated, it starts a Found draft containing only approved public hints; finder completes and submits it. Scanning does not publish automatically or prove possession.

## 10. Open requirements decisions and exclusions

| ID | Decision needed | Affected scope |
|---|---|---|
| OI-01 | Keep Release 1.0 weights or approve roadmap weights that add time/image and reduce/remove private-answer points? | BR-02, BR-08, FR-MAT-03 |
| OI-02 | Does matching agreement itself count as ownership verification, or is a fresh claimant challenge required? | FR-VER-01–06 |
| OI-03 | Are phone numbers prohibited in messages even after mutual acceptance, or may participants share them then? | FR-MSG-03, FR-HND-05–06 |
| OI-04 | Who approves safe handover points and defines organization scope? | FR-SHP-01–05, FR-ORG-01–06 |
| OI-05 | Are notifications in-app only, in-app plus email, or later SMS? What are consent and opt-out rules? | FR-NOT-01–05 |
| OI-06 | Confirm the browser-only constraint or approve a separate native mobile product. | CON-01 |
| OI-07 | Approve sensitive-answer minimization, protection, retention, and deletion policy before production. | NFR-SEC-07, Section 6.2 |
| OI-08 | Approve proposed performance, recovery, availability, compatibility, accessibility, and usability targets. | NFR-PER, NFR-OPS, NFR-COMP, NFR-ACC, NFR-USE |

Release 1.0 exclusions: password reset, profile editing, in-app help, notifications, messaging, public deployment, and ownership verification. Roadmap features are not silently included in the Release 1.0 baseline.

## 11. Acceptance and requirement traceability

| Acceptance test | Requirement coverage | Scenario |
|---|---|---|
| AT-01 | FR-ACC-01 to 06, NFR-SEC-01 to 02 | Register (including password validators), authenticate with and without remember-me, sign out, and attempt cross-account or unauthorized actions. |
| AT-02 | FR-REP-01 to 13, FR-VAL-01 to 06 | Complete five-stage reporting, resume draft, change category and confirm old answers clear, check required location description, display identifiers and QR UUID, and submit invalid data and out-of-range coordinates. |
| AT-03 | FR-PHO-01 to 04, SEC-05, NFR-SEC-08 | Submit valid, oversized, unsupported, damaged, and unauthorized photo requests; inspect normalized metadata and no-store headers. |
| AT-04 | FR-MAT-01–08, BR-02–03 | Test eligible/ineligible pairs, 69/70 score boundary, agreement minimum, unique pair, and private-data display. |
| AT-05 | FR-HND-01 to 09, BR-04 to 06, NFR-REL-01 to 02, NFR-LOC-01 | Propose/accept/dismiss, restore by dismisser and by the other participant, disclosure timing, concurrency, reservation, return time boundary, and competing-match dismissal on return. |
| AT-06 | FR-HIS-01 to 06, FR-MOD-01 to 05 | Check owner-filtered history, ten-item pagination, control-character search rejection, audit event attribution, moderator role, state eligibility, and match dismissal on close or removal. |
| AT-07 | FR-QR-01 to 11, SEC-03 to 04 | Scan report and personal labels signed out/in and active/inactive; self-use and closed-source refusal; six-month expiry/deactivate/reactivate; owner-only label image. |
| AT-08 | NFR-PER, NFR-USE, NFR-ACC, NFR-COMP, NFR-OPS | Run agreed performance, usability, accessibility, compatibility, availability, and recovery measurements. |

At release approval, every in-scope High-priority requirement shall map to at least one passing acceptance test. Proposed targets require stakeholder sign-off before serving as pass/fail gates. Test results, date, environment, and deviations belong in the release test record, not in this specification.

## 12. Revision and approval

| Version | Change | Approval |
|---|---|---|
| 1.1 | Supplied project SRS draft: scope, initial FR/NFR set, roadmap, use cases, and domain model. | Approval not recorded |
| 3.0 | Reframed as a normative SRS; added individual acceptance criteria, clarified release scope, consolidated domain/privacy requirements, and added acceptance-test traceability. | Review pending |
| 3.1 | Aligned with confirmed implementation behavior. Restore limited to the dismissing participant (FR-HND-04). Label expiry fixed at six months with reactivation (FR-QR-05, FR-QR-09). Coordinate check is valid geographic range only (FR-VAL-05). Added remember-me and password validators (FR-ACC-01, FR-ACC-02), category-change answer clearing (FR-REP-12), display identifiers and QR UUID (FR-REP-13), control-character history search rejection (FR-HIS-06), self-use QR refusal (FR-QR-10), label image download (FR-QR-11), competing-match dismissal on return and moderation (FR-HND-07, FR-MOD-02), `no-store` media (NFR-SEC-08), and `Asia/Karachi` timezone (NFR-LOC-01). | Review pending |

| Approval role | Name | Decision | Date |
|---|---|---|---|
| Project owner |  | Pending |  |
| User/stakeholder representative |  | Pending |  |
| Course reviewer |  | Pending |  |
