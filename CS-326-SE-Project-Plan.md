# CS-326 Software Engineering project plan

## Project title

**Design and Development of a Web-Based Lost and Found Management System for NED University**

## Course

**Course code:** CS-326  
**Course title:** Software Engineering  
**Project type:** Individual web application

## Problem statement

At NED University, students commonly rely on friends, WhatsApp groups, departments, and security offices when they lose or find an item. These methods create scattered records, expose contact details, and make it difficult to connect a finder with the person who lost an item.

The proposed system creates one web-based record of Lost and Found reports. A user can report an item, receive an explainable match, propose or accept a private handover, and record the completed return.

## Objectives

- Allow users to register and log in securely.
- Allow one user to submit both Lost and Found reports.
- Provide complete report CRUD: create, view, edit, close, and delete a user’s own reports.
- Record a specific item title, a broad item category, description, approximate NED location, location description, and date.
- Suggest possible matches using category, location, date, and shared description keywords.
- Exclude a user’s own Lost and Found reports from matching.
- Compare complete category-specific private questionnaires from both reports without exposing their values.
- Require both participants to accept a Security or Department Office handover before contacts are revealed.
- Record the returned-item handover.

## Scope

### Included

- Registration, login, logout, and session-based access control.
- Lost and Found report CRUD.
- NED campus location selection and an approximate-location description.
- Rule-based matching with an explainable score.
- Bilateral category questionnaires, deterministic matching, mutual handover acceptance, contact release, and return status.

### Excluded from the first version

- Image recognition and AI matching.
- GPS and live maps.
- Chat, email, push notifications, QR codes, and mobile applications.
- University-wide official deployment and real identity verification.

## Users and core rule

The same account can be both an owner who lost an item and a finder who reports another item. Lost and Found are report types, not user roles.

Every report stores `user_id` and `type`. The matching rule is:

```text
Match only Lost reports with Found reports where lost.user_id is different from found.user_id.
```

This prevents a user from receiving a false suggestion between their own reports.

## Main workflow

```text
Register/Login
      ↓
Create Lost or Found report
      ↓
System checks eligible reports from other users
      ↓
Possible match appears with score breakdown
      ↓
Either participant proposes a handover
      ↓
The other participant accepts or rejects
      ↓
Users record handover as Returned
```

## Matching method

The system uses simple, explainable rules instead of AI:

| Factor | Maximum score |
|---|---:|
| Same item category | 20 |
| Same NED location | 20 |
| Date distance | 0 to 15 |
| Description Jaccard similarity | 0 to 15 |
| Five private fields | 0 to 30 |

A score of 70 or higher, with at least two private fields agreeing, becomes a possible match. The score suggests a candidate; it does not prove ownership.

## Proposed technology stack

| Area | Technology |
|---|---|
| Frontend | HTML, CSS, Bootstrap, basic JavaScript |
| Backend | PHP 8 |
| Database | MySQL |
| Local environment | XAMPP: Apache, PHP, MySQL, phpMyAdmin |
| Development tools | Visual Studio Code and GitHub |
| Testing | Browser testing, PHP validation, and MySQL test data |
| Documentation | Markdown, draw.io, Mermaid diagrams |

The system uses PHP sessions for login and prepared MySQL statements for database queries.

## Database plan

| Table | Purpose |
|---|---|
| `users` | Account name, email, password hash, and creation time |
| `reports` | Lost/Found item details, creator, location, contact, and report status |
| `report_answers` | Five normalized private answers per report |
| `matches` | Eligible Lost/Found pairs and their score breakdown |
| `handovers` | One proposed location and time, proposer, state, and completion timestamp |

## Development plan

| Increment | Work | Result |
|---|---|---|
| 1 | MySQL schema, registration, login, sessions | Users have secure accounts |
| 2 | Report CRUD and NED location details | Users manage their own Lost/Found reports |
| 3 | Matching algorithm and same-user exclusion | Eligible possible matches appear |
| 4 | Mutual handover, contact release, return status, and documentation | Complete lost-to-returned demo |

## CS-326 Software Engineering coverage

| CS-326 area | Evidence in this project |
|---|---|
| Software attributes | Privacy, security, usability, reliability, and maintainability requirements |
| Process models | Incremental development chosen after comparing waterfall and reuse-oriented approaches |
| Requirements engineering | Functional, non-functional, and NED University domain requirements with acceptance criteria |
| Analysis modelling | ER diagram, class/domain model, use-case diagram, and report state diagram |
| Project management | Four implementation increments, estimates, task board, and schedule |
| Risk management and RMMM | Risks for false matches, privacy leaks, unauthorized edits, and scope growth |
| Architecture and design | Browser → PHP modules → MySQL; separate matching rules from report CRUD |
| Agile and XP | Small releases, review after each increment, refactoring, and tests |
| Verification and validation | Code inspection, input validation, security tests, matching tests, and user task feedback |
| SQA and metrics | Defect count, test results, response time, and actual development hours |
| Cost estimation | Size/function-oriented estimate and COCOMO calculation using the instructor’s model |
| Maintenance | One documented change with impact analysis and regression test |

## Test cases

- An unauthenticated visitor cannot access report or handover pages.
- A user cannot edit or delete another user’s report.
- A user can create both Lost and Found reports.
- A user’s own Lost and Found reports never match.
- Similar reports from different users produce a score of 70 or higher and at least two private fields agree.
- Different item categories do not match.
- Category-specific private answers never appear in the dashboard, staff page, or match response.
- Only the two participants can open a match or change its handover state.
- Contact details stay hidden until both participants accept the same proposal.
- A participant can reject a Possible Match or proposed handover.
- Returned reports no longer appear as active matches.

## Demonstration scenario

Ahmed reports a black wallet lost near the Central Library and completes the Wallet / Purse questionnaire, including explicit card-presence and masked-digit fields. Sara reports finding a black wallet near the Central Library and completes the same fields. The system suggests a match because category, location, date, description, and private fields agree. Either participant proposes a Security Office handover; the other accepts it; both contacts then appear, and either participant records the return.

## Future work

Future versions may add a clickable NED map, optional GPS coordinates, image upload, image similarity, notifications, QR labels, and a moderator dashboard.
