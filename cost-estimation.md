# Software Cost Estimation

Where Is My Stuff? GPS-enabled Lost and Found System. CS-326 evidence for size-oriented metrics, function-oriented metrics, and COCOMO algorithmic cost modelling.

All sizes are measured from the current codebase on 12 Sep 2026. All effort and duration figures are estimates, not logs of actual hours (actual-hours logging is an open item in project-management.md).

## 1. Size-oriented metrics

Measured application size excluding tests: 1249 LOC, 44 functions (sqa-report.md section 3.1). Test code: 68 LOC.

| Estimate model | Input | Result |
|---|---|---|
| LOC-based estimate | 1249 LOC app code | see COCOMO below |
| LOC/FP productivity | 1249 LOC / 124 FP | 10.1 LOC per function point |

| Module | LOC | Share | Rationale |
|---|---|---|---|
| Bootstrap/config | 88 | 7% | Session, DB, routing, setup check |
| Helpers + validation | 325 | 26% | Questionnaire engine and security rules |
| Matching | 83 | 7% | Deterministic scoring, small but critical |
| Workflow | 137 | 11% | Handover state machine and transactions |
| Presentation pages | 616 | 49% | Forms, dashboards, staff pages |
| Total | 1249 | 100% | |

## 2. Function-point (function-oriented) estimate

Systems were counted with the standard five FP types using average weights (EI 4, EO 5, EQ 4, ILF 10, EIF 7).

| Type | Count | Reasoning | Contribution |
|---|---|---|---|
| External inputs (EI) | 12 | register, login, logout, create/edit report, close, delete, propose, accept, reject, returned, set role | 48 |
| External outputs (EO) | 2 | dashboard, match detail page | 10 |
| External inquiries (EQ) | 4 | report form, report view, admin page, moderation page | 16 |
| Internal logical files (ILF) | 5 | users, reports, report_answers, matches, handovers | 50 |
| External interface files (EIF) | 0 | no external system interfaces | 0 |
| Total function points | | | 124 FP |

The 10.1 LOC/FP ratio is consistent with a small data-oriented PHP application with heavy form logic and thin business rules.

## 3. COCOMO (Constructive Cost Model)

### 3.1 Basic COCOMO (organic project)

Small team, familiar problem domain, no strict real-time constraints. Organic parameters: a = 2.4, b = 1.05, c = 2.5, d = 0.38.

E = a · KLOC^b = 2.4 · 1.249^1.05 = 3.0 person-months
D = c · E^d = 2.5 · 3.031^0.38 = 3.8 months
Staffing = E / D = 0.8 people

### 3.2 Intermediate COCOMO

Intermediate organic: a = 3.2, b = 1.05. Cost drivers selected for this project:

| Cost driver | Rating | Multiplier |
|---|---|---|
| Required software reliability | High (financial data, privacy) | 1.15 |
| Database size | High (5 tables, many indexes) | 1.08 |
| Product complexity | Low (rule-based matching, no AI) | 0.85 |
| Analyst capability | High | 0.86 |
| Programming language experience | High (PHP, MySQL) | 0.95 |
| Effort adjustment factor (EAF) | product of above | 0.86 |

E = 3.2 · 1.249^1.05 · 0.86 = 3.5 person-months
D = 2.5 · 3.5^0.38 = 3.9 months
Staffing = 0.9 people

### 3.3 Effort allocation to increments

| Increment | Effort share | Person-months (basic) |
|---|---|---|
| Accounts | 15% | 0.45 |
| Reports + GPS coordinates | 35% | 1.05 |
| Matching (haversine) | 20% | 0.60 |
| Handover + return | 20% | 0.60 |
| Documentation and evidence | 10% | 0.30 |

## 4. Cost summary

| Model | Effort (person-months) | Duration (months) | Average team |
|---|---|---|---|
| Basic COCOMO | 3.0 | 3.8 | 0.8 |
| Intermediate COCOMO | 3.5 | 3.9 | 0.9 |
| Assumed one-student rate | 1 person over ~4 months | | rounds to the same envelope |

Notes: the estimate assumes a single developer with high tool familiarity and no formal project-management overhead. It excludes the deferred map display (Leaflet.js) and image recognition, which remain out of scope (scope-freeze.md).

## 5. Assumptions and rationale

- 1249 LOC is the executable baseline; generated or vendor code is absent (no Composer).
- The defect correction effort for D1/D2 (verification-and-validation.md) is estimated at one to two days and is not yet in the COCOMO totals.
- All monetary costing is omitted; this is a university project without a client budget.