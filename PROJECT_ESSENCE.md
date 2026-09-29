# Where Is My Stuff? — Project Essence & Necessary Improvements

> Single authoritative summary of the campus lost-and-found application, its current state, and the minimum improvements required to make it genuinely useful.

---

## Project Vision

**One sentence:** A campus lost-and-found where a student who loses an item files a 4-step report, the system silently compares it against every opposite report using private matching answers, and both parties are notified the moment a credible match exists — then they arrange a handover with zero admin intervention.

**Core promise:** *Friction between "I lost this" and "I found this" is minimal.*

---

## Current State (Increments 1 & 2 — Complete)

| Area | Status | Notes |
|------|--------|-------|
| Custom user model, email login, registration, CSRF, sessions | ✅ | AbstractUser, username=email |
| Four-step wizard (Type → Details → Matching → Review) | ✅ | Drafts saved server-side, no localStorage |
| Category-specific private matching questionnaire | ✅ | Dynamic fields via `schema()` |
| Matching engine (category 20, location 20, date 15/10/5, description 15, private 30) | ✅ | ≥70 points + ≥2 agreements |
| Handover workflow (Propose → Accept → Scheduled → Returned) | ✅ | Atomic, reservations, competing-match protection |
| Reject / Restore with re-scoring | ✅ | Only dismisser can restore |
| Staff moderation (Close / Remove) | ✅ | Audited, no admin UI for reports |
| Dashboard (stats, matches needing action, 3 open reports) | ✅ | Match-first, drafts inline |
| Report history with search/filter/pagination | ✅ | |
| 21 unit tests + 2 browser tests passing | ✅ | |
| System check clean, no migration drift | ✅ | |

---

## Necessary Improvements (Must-Do)

These are not "nice to have" — they remove real friction or are required for the app to be used by actual students.

### 1. Password Reset (Increment 3 — Critical)

**Why:** A forgotten password = permanent lockout = maximum friction. This is the single biggest blocker between a user and their item.

**Implementation:**
- Django's built-in `PasswordResetView` + development email backend (console or file)
- Template for reset email (include campus branding)
- Token expiry: 24 hours
- Tests: request → token → new password → login works

**Effort:** ~2 hours

---

### 2. Notifications for Matches & Handover Changes (Increment 3 — High)

**Why:** Today a user must log in and check the dashboard to discover a match. Notifications invert this: the system tells the user when action is needed.

**Minimum viable:**
- In-app notification bell (header) — stores `Notification` model (user, type, match_id, read, created_at)
- Types: `match_created`, `handover_proposed`, `handover_accepted`, `handover_scheduled`, `item_returned`, `match_restored`
- Email fallback (same dev backend as password reset) for users who haven't visited in 24h
- Mark-as-read on click; badge count in sidebar

**Effort:** ~4 hours

---

### 3. Profile Page (Increment 3 — Medium)

**Why:** Contact info must be accurate for handover. Users need one place to fix name, email, password.

**Fields:** full name, email (with re-verification flow), change password
**No:** avatar, bio, social links — keep it strictly functional

**Effort:** ~2 hours

---

### 4. Management Pagination (Increment 3 — Low)

**Why:** When reports exceed ~30, the management page becomes unusable.

**Implementation:** `Paginator` on `Report.objects.exclude(status="Removed")`, 20 per page, same filter/search as report history

**Effort:** ~1 hour

---

### 5. Production Settings (Increment 4 — Required for any real use)

**Why:** The app currently runs with dev defaults (debug on, weak secret, no HTTPS, no throttling).

**Minimum config (`config/settings_prod.py`):**
```python
DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
```

**Effort:** ~1 hour

---

### 6. Login Throttling (Increment 4 — Required for any real use)

**Why:** Brute-force protection on login/register is non-negotiable.

**Implementation:** `django-axes` or custom `LoginView` with cache-based attempt tracking (5 attempts / 15 min per IP)

**Effort:** ~1 hour

---

### 7. Static Collection & WSGI (Increment 4 — Required for deploy)

**Why:** `runserver` is not for production.

**Implementation:**
- `whitenoise` for static files
- `gunicorn` + `uvicorn` (ASGI) or `gunicorn` (WSGI)
- `Procfile` or systemd unit
- `collectstatic` in build step

**Effort:** ~1 hour

---

### 8. PostgreSQL Option & Migration Notes (Increment 4 — Required for scale)

**Why:** SQLite IMMEDIATE serializes writes but doesn't scale; campus deployment needs Postgres.

**Implementation:**
- `DATABASE_URL` env var with `dj-database-url`
- Document: `python manage.py migrate` works unchanged; `IMMEDIATE` removed in Postgres config
- Backup: daily `pg_dump` to object storage (doc only, not code)

**Effort:** ~2 hours (mostly documentation)

---

### 9. Dashboard Restructure (UX — High Impact)

**Why:** Matches are the unique value; reports are reference. Current dashboard buries matches below stats.

**Proposed layout:**
```
┌─────────────────────────────────────────────────┐
│  Stats row (Open / Matches / Handovers / Returned)  ← compact
├─────────────────────────────────────────────────┤
│  MATCHES NEEDING YOUR ACTION (full width)            ← hero section
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ Match A     │ │ Match B     │ │ Draft C     │  │
│  │ 87/100      │ │ 72/100      │ │ Black wallet│  │
│  │ Respond →   │ │ Accept →    │ │ Continue →  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘  │
├─────────────────────────────────────────────────┤
│  YOUR REPORTS (collapsible, default closed)         ← secondary
│  ▼ LFD-001 Black backpack  Open  [View] [Edit]    │
│  ▼ FND-003 Silver keys     Returned                │
└─────────────────────────────────────────────────┘
```

**Changes:**
- `dashboard.html`: move reports into `<details>` with `<summary>Your reports (N)</summary>`
- `views.dashboard`: add `drafts_count` to context (or reuse `drafts` queryset)
- Keep CTA inline in stats row or match section

**Effort:** ~1 hour

---

### 10. Stale Documentation Fixes (Immediate)

| File | Fix |
|------|-----|
| `TODO-INCREMENTAL.md` line 82 | "20 unit tests" → "21 unit tests" |
| `AGENTS.md` line 49 | Scoring doc: "location 20, date 15/10/5" (already fixed in this session) |
| `README.md` line 60 | "TODO.md" → "TODO-INCREMENTAL.md" (already fixed in this session) |

---

### 11. Private Report Photos (Increment 4 — Medium)

**Why:** Photos are the strongest handover confirmation. Both parties upload one optional image; neither is public and neither scores.

**Design (locked 2026-09-13):**
- Optional `image` field on `Report` (both Lost and Found) plus a mirror `Draft.image` field — `draft.data` is JSON and cannot carry a file
- Never scored, never public, no classifier/vision needed
- Revealed only after both participants accept (state `Handover Scheduled` and later), matching the existing contact gate
- Locked state renders no image URLs; page source leaks nothing
- Lost image absent does not block a match (bonus proof, not a requirement); mismatch at review uses the existing reject/restore flow
- Pillow dependency, size/type validation in `DetailsForm`

**Effort:** ~3 hours

---

### 12. QR Scan-to-Claim / Share Link (Increment 5 — Medium)

**Why:** A finder who holds the item should claim it in under a minute. The QR is the visual carrier for a public, tokenized share link; both carry the same URL.

**Design (locked 2026-09-13):**
- `Report.public_id` = random UUID, never expose `pk` in the QR URL
- `/r/<uuid:public_id>/qr/` renders the QR PNG on the fly via `qrcode[pil]`, nothing stored on disk
- `/r/<uuid:public_id>/found/` is `@login_required` and seeds a Found draft: `kind=Found`, category locked, title/location suggested from the lost report's public fields
- Match is **not** written by the view — submit → `publish()` → `recalculate()` → existing state machine (propose/accept/scheduled/returned)
- Resolved guard: token shows a closed notice and serves no form when `status != "Open"` or the report is reserved
- Token rotation on close/handover so stale physical tags die with the report

**Effort:** ~3 hours

---

### 13. Email Verification on Registration (Increment 3 — Medium)

**Why:** `Registration.clean_email` only checks uniqueness, so anyone can register another person's address and post in their name. Verification is the security floor.

**Implementation:** Email a one-time token on registration; account can't post until confirmed. Same dev email backend as password reset.

**Effort:** ~1.5 hours

---

### 14. Account Deletion & Retention (Increment 3 — Low)

**Why:** `db.sqlite3` holds private matching answers (CNIC suffixes, card details). A user who registers can never remove their own data.

**Implementation:** Self-service delete, allowed only when the user has no open reports or in-flight matches (`Report.owner` is `PROTECT`, so deletion must be gated); otherwise direct the user to moderation. Document retention for closed reports.

**Effort:** ~1.5 hours

---

## Optional / Deferred (Not Necessary for Core Promise)

| Item | Why Deferred |
|------|--------------|
| Public image gallery | Photos stay private; a public gallery contradicts the privacy design |
| Image classifier / vision | Photos are human confirmation at handover; deterministic scoring is trusted and auditable |
| Social/SSO login | Email is sufficient for campus |
| AI matching | Current deterministic scoring is auditable and trusted |
| Maps/location picker | Controlled location list is faster and more reliable |
| In-app chat | Handover contact release solves coordination |
| Production email notifications | Dev backend + in-app covers MVP |
| Native mobile app | Responsive web works; PWA later if needed |
| Child/sub-item reports | Single-report model covers 95% of cases |
| Auto-save while typing | Draft save-on-step is sufficient |
| Formal SRS/SDD | Architecture + TODO + tests serve as living docs |

---

## Architecture Snapshot (For Future Maintainers)

```
┌─────────────────────────────────────────────────────────────┐
│  MVT + Service Layer                                        │
├─────────────────────────────────────────────────────────────┤
│  models.py      → User, Report, Draft, Match, Event         │
│  views.py       → HTTP handling, auth, redirects            │
│  services.py    → publish, transition, moderate, score,     │
│                   recalculate, validated                    │
│  forms.py       → Registration, Login, Type, Details,       │
│                   Matching (dynamic), Meeting               │
│  templates/     → base, dashboard, wizard, match, reports,  │
│                   management, auth, report                  │
│  static/        → app.js (wizard refresh, meeting format,   │
│                   privacy hint, sidebar), auth.js           │
└─────────────────────────────────────────────────────────────┘
```

**Key invariants:**
- Private answers never rendered in match/management views
- `db.sqlite3` contains PII → protect with OS permissions
- Matches require ≥2 agreements + ≥70 score
- Reports lock on handover proposal (status Open + not reserved)
- Contacts released only after both parties accept handover
- Report photos and QR tokens expose public fields only; photos reveal after both accept

---

## Effort Summary

| Category | Hours | Priority |
|----------|-------|----------|
| Password reset | 2 | Critical |
| Notifications | 4 | High |
| Profile page | 2 | Medium |
| Management pagination | 1 | Low |
| Production settings | 1 | Required for deploy |
| Login throttling | 1 | Required for deploy |
| Static + WSGI | 1 | Required for deploy |
| PostgreSQL option + docs | 2 | Required for scale |
| Dashboard restructure | 1 | High UX impact |
| Doc fixes | 0.5 | Immediate |
| Private report photos | 3 | Medium (Increment 4) |
| QR scan-to-claim | 3 | Medium (Increment 5) |
| Email verification | 1.5 | Medium (Increment 3) |
| Account deletion | 1.5 | Low (Increment 3) |
| **Total** | **~24.5** | |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-12 | Match-first dashboard | Matches are the unique value; reports are reference |
| 2026-09-12 | Password reset before profile | Lockout is higher friction than wrong name |
| 2026-09-12 | In-app notifications first, email fallback | Most students check phone, not email |
| 2026-09-12 | Keep 4-step wizard | Private answers are the matching signal; cannot compress further |
| 2026-09-12 | SQLite for dev, Postgres for prod | Dev simplicity, prod scale |
| 2026-09-13 | Photos: private, both sides, unscored, revealed after both accept | Photos confirm, they don't match; avoids the image-comparison model |
| 2026-09-13 | QR scan-to-claim reuses the existing report pipeline | Scan seeds a Found draft; publish → recalculate creates the match; no new match API |
| 2026-09-13 | Neutral login placeholder | Removed institute-specific domain hint to avoid security concerns |

---

## How to Use This Document

- **New contributor:** Read "Current State" + "Architecture Snapshot" → run tests → pick top priority from "Necessary Improvements"
- **Reviewer:** Verify each "Necessary Improvement" has a checkbox in TODO-INCREMENTAL.md
- **Stakeholder:** "Project Vision" + "Effort Summary" = scope & timeline