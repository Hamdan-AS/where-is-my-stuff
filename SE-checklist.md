# CS-326 Software Engineering checklist

Compared with the supplied full-SDLC checklist on 8 September 2026. Evidence documents added 12 September 2026 close the process gaps listed below.

Legend: [x] complete, [~] partly covered or needs formal evidence, [ ] not done.

Evidence documents: srs.md, analysis-models.md, project-management.md, rmmm.md, design-record.md, verification-and-validation.md, sqa-report.md, cost-estimation.md, maintenance-record.md.

## 1. Project initiation

- [x] Define project scope, objectives, and deliverables. Evidence: scope-freeze.md and CS-326-SE-Project-Plan.md.
- [x] Identify software attributes: maintainability, dependability, efficiency, and acceptability.
- [x] Select the Incremental process model.
- [x] Justify the Incremental model against Waterfall.
- [x] Identify stakeholders and roles: Student, Finder, Moderator, Admin, and NED security or department staff.
- [ ] Set up a version-control repository and record the repository URL. Open item (no git in this project).

## 2. Requirements engineering

- [x] Document functional requirements for accounts, reports, matching, handover, return, and staff access. Evidence: srs.md section 4 (FR-01 to FR-11 plus GPS deltas).
- [x] Document non-functional requirements for security, privacy, usability, reliability, and maintainability. Evidence: srs.md section 5.
- [x] Capture domain constraints: NED locations, Lost/Found report types, and campus handover locations. Evidence: srs.md section 6, scope-freeze.md.
- [~] Perform a feasibility study. The small PHP/MySQL scope is justified in cost-estimation.md and project-plan.md, but there is no separately named feasibility record.
- [x] Produce an SRS. Evidence: srs.md (standalone SRS with sign-off placeholder).
- [ ] Get stakeholder sign-off on requirements. Open item: signature table in srs.md section 8.
- [x] Define acceptance evidence for each requirement. Evidence: srs.md FR table and architecture.md.

## 3. Analysis modelling

- [x] Produce a data model. ER diagram and data dictionary in analysis-models.md section 1.
- [x] Produce an object model with domain class and object diagrams. Evidence: analysis-models.md section 2.
- [x] Produce behavioural models. Use-case, sequence, and state diagrams in analysis-models.md section 3 and matching-architecture.md.
- [x] Validate the models against requirements. Evidence: analysis-models.md section 4 traceability table.
- [~] Resolve and record model conflicts or ambiguities. The reopened-report ambiguity is recorded as an open item in analysis-models.md section 5.

## 4. Software project management

- [x] Develop a formal Work Breakdown Structure. Evidence: project-management.md WBS diagram.
- [~] Create a Gantt chart or Critical Path schedule. Schedule table and milestones in project-management.md section 2; a draw.io/Gantt export is still desired.
- [x] Identify technical, privacy, security, scope, false-match, and database risks.
- [x] Maintain an RMMM risk register. Evidence: rmmm.md with probability/impact/exposure/response/monitoring columns.
- [x] Assign application roles and responsibilities.
- [x] Define a communication and reporting plan. Evidence: project-management.md section 4.
- [x] Track the four implementation increments in TODO.md and scope-freeze.md.

## 5. Software design

- [x] Define the architecture: browser, PHP application, matching/workflow rules, and MySQL.
- [x] Produce an architectural design record. Evidence: design-record.md and architecture.md.
- [x] Apply and document a named design pattern. Evidence: design-record.md section 3 (layered, table-driven, strategy, repository, decorator/transaction, template method).
- [x] Design the database schema for users, reports, report_answers, matches, and handovers.
- [~] Produce UI wireframes or mockups. Evidence: ui-wireframes-redesign.png and the implemented responsive report form.
- [ ] Conduct a formal SOLID review. Open item.
- [ ] Conduct and record a design walkthrough. Open item; review checklist in verification-and-validation.md section 6.

## 6. Agile and development process

- [x] Define and prioritize a product backlog. Evidence: project-management.md section 3 backlog mapped to FRs plus TODO.md.
- [x] Plan four incremental development stages with goals.
- [ ] Record daily standups and sprint reviews. Single-developer project; standup minutes are not recorded. Sprint review is recorded via scope-freeze.md checkpoint.
- [~] Apply and record XP practices. Continuous-integration syntax gate and deliberate refactoring are recorded in project-management.md; TDD and pair programming were not used.
- [ ] Maintain a sprint burndown chart. Open item.
- [~] Conduct retrospectives. GPS-change retrospective recorded in project-management.md section 3.1; a longer review set is pending.

## 7. Implementation

- [~] Follow a basic PHP/HTML naming and formatting style. Strict types and guarded helper rules apply; a formal style guide is still needed.
- [~] Write readable application code with separate matching and workflow files. Further modularity work is intentionally deferred.
- [ ] Perform documented code reviews or peer inspections. Open item; inspection checklist in verification-and-validation.md.
- [ ] Maintain a CI/CD pipeline. Open item.
- [~] Track and resolve bugs through an issue tracker. Defect log D1/D2 maintained in verification-and-validation.md; no issue-tracking tool.

## 8. Verification and validation

- [~] Conduct formal software inspections or walkthroughs. Inspection checklist prepared in verification-and-validation.md section 6; execution pending.
- [~] Write unit-style matching checks. tests/matching_test.php exists for haversine scoring; it currently fails assertion 1 (defect D1) and is pending update.
- [~] Write and execute integration tests. tests/integration_test.py written; needs isolated MySQL socket and lat/lng updates (D2) before it can run.
- [ ] Conduct system tests. Pending browser verification (scope-freeze item 6).
- [ ] Conduct acceptance testing with NED stakeholders. Pending.
- [~] Perform documented regression testing after fixes. `php -l` regression passes; scoring regression recorded for D1.
- [x] Produce a test-case, result, and defect log. Evidence: verification-and-validation.md.
- [x] Record systematic debugging evidence. Evidence: verification-and-validation.md section 5.

## 9. Software quality assurance

- [x] Define a formal SQA plan. Evidence: sqa-report.md section 1.
- [x] Select and report metrics such as LOC, complexity, defect density, and test pass rate. Evidence: sqa-report.md section 3 (measured LOC and function counts).
- [ ] Conduct formal technical reviews. Open item.
- [ ] Perform process-compliance audits. Open item.
- [~] Measure and report quality attributes. Mapped to sqa-report.md and srs.md section 5.
- [~] Apply measurements throughout the lifecycle. Measurement process in sqa-report.md section 4; collection started, re-collection pending at submission.

## 10. Cost estimation

- [x] Estimate size using LOC. Evidence: cost-estimation.md section 1.
- [x] Estimate size using Function Points. Evidence: cost-estimation.md section 2 (124 FP).
- [x] Apply Basic, Intermediate, or Detailed COCOMO. Evidence: cost-estimation.md section 3.
- [x] Estimate cost, duration, and staffing. Evidence: cost-estimation.md section 4 (basic 3.0 PM / 3.8 months; intermediate 3.5 PM / 3.9 months).
- [x] Document estimation assumptions and rationale. Evidence: cost-estimation.md section 5.

## 11. Software maintenance

- [x] Record known defects and planned enhancements. Evidence: maintenance-record.md change log and verification-and-validation.md.
- [x] Classify maintenance as corrective, adaptive, perfective, or preventive. Evidence: maintenance-record.md section 3.
- [x] Select and document a maintenance process model. Evidence: maintenance-record.md section 1 (IEEE 1219 stages).
- [~] Establish a change-management process. scope-freeze.md acts as the change record; a formal change-request form is pending.
- [x] Update the main project documents after the matching and handover design changed.
- [ ] Plan retirement or migration. Open item.

## 12. Final deliverables

- [x] SRS document. srs.md.
- [x] SDD document. design-record.md.
- [x] RMMM or risk register. rmmm.md.
- [~] Project schedule or Gantt chart. project-management.md schedule; graphic export pending.
- [~] Test plan and test report. verification-and-validation.md; executed results pending for D1/D2.
- [x] SQA plan and metrics report. sqa-report.md.
- [x] Cost estimation report with COCOMO. cost-estimation.md.
- [x] Source code and README.
- [~] Final project report. The evidence documents now exist; they need to be assembled into one submission package.
- [ ] Presentation and demo script. Open item.

## What is complete enough for the current code scope

The application has a frozen problem statement, Incremental model choice, requirements, database design, deterministic GPS matching rules, report CRUD, bilateral category-specific questionnaires, same-user exclusion, dashboard status, mutual handover, private contact release, return status, Admin/Moderator controls, and setup instructions.

With the 12 September 2026 evidence documents, the SDLC coverage is now broad: SRS, analysis models, project schedule, RMMM, design patterns, agile records, defect and debugging log, SQA plan and metrics, cost estimation, and maintenance process model.

The remaining gaps are execution evidence rather than documents: the two test suites still need updating for haversine scoring (D1/D2) and an executed browser pass, plus a formal inspection, SOLID review, stakeholder sign-off, and assembled final report.