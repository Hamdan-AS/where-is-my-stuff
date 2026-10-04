# UI/UX design brief

This document says what the interface should do, for whom, and why. It is the design
counterpart to `UI-UX-OVERHAUL-BRIEF.md` at the repository root, which covers architecture,
routes, and the server and browser contract. Read that one for how the system is built; read
this one for what to build. Where the two overlap, this document wins on anything visual or
structural, and the other wins on anything technical.

Screen numbers match `docs/WIREFRAME-BRIEF.md` so the two can be read side by side.

Every claim is read out of the source on 29-09-2026, with file and line references. Nothing
here has been seen in a browser; there is no running environment available. Statements about
behaviour are statements about code.

## Contents

1. [What the product is](#1-what-the-product-is)
2. [The people using it](#2-the-people-using-it)
3. [What people are trying to do](#3-what-people-are-trying-to-do)
4. [Design principles](#4-design-principles)
5. [Information architecture](#5-information-architecture)
6. [Journey A, I lost something](#6-journey-a-i-lost-something)
7. [Journey B, I found something](#7-journey-b-i-found-something)
8. [Journey C, the handover](#8-journey-c-the-handover)
9. [Screen-by-screen direction](#9-screen-by-screen-direction)
10. [The three structural problems](#10-the-three-structural-problems)
11. [Design system direction](#11-design-system-direction)
12. [Content and voice](#12-content-and-voice)
13. [Accessibility targets](#13-accessibility-targets)
14. [Responsive strategy](#14-responsive-strategy)
15. [States every screen needs](#15-states-every-screen-needs)
16. [Trust and privacy as a design surface](#16-trust-and-privacy-as-a-design-surface)
17. [Consistency defects to fix first](#17-consistency-defects-to-fix-first)
18. [Open questions](#18-open-questions)
19. [Suggested sequence](#19-suggested-sequence)
20. [Related documents](#20-related-documents)

---

## 1. What the product is

A campus lost and found. A person reports an item they lost, or an item they found. The server
compares every new report against all open reports of the opposite kind in the same category
and scores them out of 100 (`core/services.py:50-85`). A pair needs 70 or more points and at
least 2 agreeing private answers before it appears as a match. The two people then compare both
reports, agree a public place and time, and only then see each other's contact details.

The whole product is one loop: describe an item well enough to be recognised by a stranger,
then agree a meeting. Everything in the interface should serve that loop and nothing else.

**The distinctive thing about this product is that it asks strangers to trust each other with
a process, not a platform.** There is no chat, no rating, no public board. The entire
reputational surface is whether a match turns out to be real, and the entire safety surface is
where two people meet. Design accordingly. There is no social feature to add later that would
change the character of the app, and `TODO-INCREMENTAL.md` defers in-app chat and image
uploads, which is the right call.

## 2. The people using it

No usability testing, interviews, or analytics are recorded anywhere in this repository. The
situations below are hypotheses inferred from the category list, the matching model, and the
privacy rules. Treat them as starting assumptions to check with real students, not as findings.

**A. The owner.** Has just realised something is gone. Knows roughly what it was and roughly
when, but is reconstructing the details from memory. The design implication: they arrive
without a name for the item, they will guess wrong at dates and places, and they cannot search
for a lost item because they have nothing to search by.

**B. The finder.** Has a physical object and no idea whose it is. Knows where and roughly when
they picked it up. The design implication: they have nothing to type into a search box, they
cannot describe the owner, and the fastest possible path from object to handover is the whole
point.

**C. The person doing both.** Owns a lost report *and* has filed a found report for something
else. This is ordinary, not an edge case, and the code already handles it: the dashboard
comparison swaps which side is labelled "Your report" per match (`templates/dashboard.html:46`,
`:63`). The design implication: interface language must never imply a user's two reports belong
to two different people in a way that gets the comparison backwards, and a person scanning the
dashboard may hold both sides of several simultaneous matches.

**D. The finder who is also the match.** Someone scans a QR sticker, files a found report, and
the system immediately pairs it. The design implication: the first-time experience for a
stranger starts mid-flow, at the QR scan, on a phone, with no prior account and possibly no
context for what the app is. This is the least-designed surface in the product and the one with
the most strangers.

**E. Staff.** Moderates reports, closes resolved ones, removes listings. Low volume, high
consequence, and one click from irreversible. The design implication: destructive actions need
confirmation, and the queue needs to be navigable at a volume the current list cannot handle.

## 3. What people are trying to do

Ordered by how much the interface should care about each.

1. **Find out whether my item has been reported.** Highest stakes, least supported. The app has
   no search for a lost item, only a history of your own reports (`templates/reports.html:10`).
2. **File a good report in under two minutes.** The wizard is five steps and can expand to about
   27 fields on step 4 (section 10.1). Length is the main risk here.
3. **Decide whether a match is real.** The comparison screen is the highest-stakes judgement in
   the product, and the user has only public fields plus a score to go on. Their own memory of
   their item is the real evidence.
4. **Agree where and when to meet.** A form with two fields, one of which is a hand-typed date
   string, currently the only way to schedule a meeting.
5. **Close the loop and confirm the item came back.** One button, available too early, with a
   server-only time gate.
6. **Correct a mistake later.** Edit is available only while a report is `Open` and not
   `reserved` (`core/views.py:137-139`), and the error message is not shown because the redirect
   carries no message on that path. A user who tries to edit a locked report gets a silent
   redirect.

## 4. Design principles

Each principle is stated with what it forbids, because the forbids are the useful part.

**1. Never display a score as a probability.** The number is a similarity sum, not a likelihood.
`templates/dashboard.html:83` calls it "Match confidence" and renders it as a percentage, which
invites "85% sure" reasoning. The match page gets it right at `templates/match.html:16`: "A
score is a report comparison. Confirm the item in person before recording return." Apply the
second wording everywhere and drop the word confidence. Show the components, because the
components are what a person can actually verify: a wallet matching on category and colour but
zero on location is a different situation from one matching on all three.

**2. Ask for the sensitive data, then show exactly what happens to it.** Step 4 asks for full
16-digit bank card numbers and full 13-digit CNICs. That is the only way the matching works, and
it is the single biggest trust decision a user makes here. The current interface offers one muted
sentence and a native browser tooltip on each field
(`core/forms.py:218`, `templates/wizard.html:34`). This is not enough. Say what is compared, what
is never shown, and to whom, at the point of asking, not only on the login page.

**3. Meet in public, on purpose.** The meeting place is a free-text field with the help text
"Any public, safe place for the handover" (`core/forms.py:233`). Make that a real prompt, not a
placeholder. Offer suggestions of the kinds of places the campus already implies, and never
reveal a report's coordinates to the matched party, because the map is the owner's memory, not
an observation.

**4. Keep a person's two reports straight at all times.** One person can be on both sides of
the campus at once. Every comparison needs a consistent, unmistakable "yours / theirs" treatment,
and it must not be conveyed by colour alone.

**5. Say what is happening and when.** The app is a slow, server-driven process spread over
days. A report filed today may match tomorrow. Say "we will keep checking" rather than leaving
the user to infer it, and never imply that a report with no matches has been rejected.

**6. Do not add a social surface.** No public listings, no chat, no profiles visible to other
users, no item images. Every one of these would change what the product is and would make the
handover less safe. `TODO-INCREMENTAL.md` defers them; this principle says why.

## 5. Information architecture

Four top-level destinations behind the sidebar, and the sidebar already hides items based on
report count (`templates/base.html:34-39`):

| Destination | Route | Shown when |
|---|---|---|
| Dashboard | `/` | User has at least one visible report |
| New report | `/reports/new/` | Always |
| My reports | `/reports/` | User has more than one report |
| Management | `/management/` | Staff only |

Plus two entry points outside the sidebar: the QR scan target `/r/<uuid>/found/`, which is the
only route a stranger can reach, and the claim QR image `/r/<uuid>/qr/`.

**The sidebar's conditional nav is a design problem, not a feature.** A user with exactly one
report sees two items. A first-time user who has just registered, with zero reports, is
redirected to the wizard (`core/views.py:29-31`), so they never see the shell at all until they
publish. A redesign should decide deliberately between an always-four-item sidebar with disabled
states, and the current progressive disclosure. What it should not do is keep the current rule
by accident, since unit tests assert on it (`core/tests.py:206`, `:225`).

**URLs carry state.** `?step=`, `?q=`, `?status=`, `?kind=`, `?page=`, and the post-publish
`?new=<pk>#report-<pk>` fragment. The redesign should keep URL state for filters and paging, and
keep the wizard step in the URL, because the step gates are enforced server-side
(`core/views.py:145-152`).

**One structural gap.** `docs/WIREFRAME-BRIEF.md` describes a "Screen 13. Public claim page".
No such template exists. The QR scan seeds a draft and redirects into the wizard
(`core/views.py:279-286`), or shows `closed_notice.html` if the report is dead. The redesign has
to decide: does a stranger scanning a QR land on a claim page that explains the situation, or
straight into step 3 of the wizard with a stranger's draft already filled in? This is question
one in section 18.

## 6. Journey A, I lost something

Seven moments. The design job at each is given against the current behaviour.

**1. Land on login.** The page already explains the product in three steps: Report, Review,
Arrange (`templates/auth.html:34-38`), and states the privacy promise
(`:39`). Keep that. It is the best-written copy in the product. What is missing is any hint that
a lost item cannot be searched for, which is the question every first-time visitor arrives with.

**2. Register.** Name and email only, no password confirmation field visible in
`form.visible_fields` output, and the two password fields render through the reveal toggle
(`templates/auth.html:64-68`). Check whether the confirm field exists at all before redesigning;
if it does not, add it, because a mistyped password with no reset path (section 17) is a dead
end. Note the password placeholder is Roman Urdu, "Yahan Apni email dalo" (`:99`), while every
other string in the product is English. Decide one language policy; mixing them reads as
unfinished.

**3. Redirected into the wizard.** The first screen after registering is step 1
(`core/views.py:29-31`). The heading is "What happened to your item?" (`wizard.html:15`), which
is a good question. Keep it.

**4. Step 1, type and category.** Two radios for Lost or Found, a title, one of eight
categories, and a date. The category drives everything in step 4, so a wrong choice costs the
user their questionnaire later (section 17, defect 2). This is the screen where category should
be explained rather than merely labelled.

**5. Step 2, details.** A 3-row textarea (`core/forms.py:123`) and a contact field. The
privacy hint appears on this step and is driven by JS as the user types
(`static/app.js:20-31`), which is good, but it is a status line under a field, and it does not
replace the server rejection. The textarea should grow with content instead of scrolling
internally at 2000 characters.

**6. Step 3, location.** The hardest step, and the only one with a real spatial decision. See
section 10.3.

**7. Step 4, the questionnaire.** The problem screen. See section 10.1.

**8. Step 5, review and submit.** The review shows six fields and says the questionnaire is
complete but does not show it (`templates/wizard.html:93`). That is correct for privacy, and
wrong for confidence: a user who spent effort on 27 answers gets no confirmation they were
recorded. Show a count and a "change answer" link back to step 4 rather than the values.

**After submitting.** The user is redirected to
`dashboard?new=<pk>#report-<pk>` (`core/views.py:196`). No template reads `request.GET`, and
`dashboard.html` emits no `report-<pk>` anchor, so the user lands at the top of the dashboard
having just created the single thing they most want to see. This is defect 1 in section 17 and
the highest-value fix in the whole product.

## 7. Journey B, I found something

**Entry 1, a stranger scans the QR.** This is the highest-value, worst-designed path in the
product. The scan seeds a draft with the owner's kind, category, title, location and today's
date, then deliberately drops the coordinates, description, contact, and private answers
(`core/views.py:284-285`). The user lands on step 3 with a partly filled form and no
explanation of where those values came from, nor why the map is empty. The map being empty is
correct and must stay empty, but it needs a sentence, because an empty map next to a prefilled
place name reads as a bug.

**Entry 2, someone tells the owner about it.** The owner is not in the app. Nothing in the
interface supports this, and the login page does not tell anyone to scan a QR or report a find.
There is no in-product path for "I saw this, what do I do". Either design a shareable claim link
or state plainly in the copy that a finder must create an account and file a report.

**Then the same seven steps.** The difference is step 1: a finder has no lost item, so the
"what happened to your item?" framing is slightly off for half the users. The wizard should
speak about reporting rather than losing, with the lost or found distinction as a choice rather
than a premise.

**After a find is submitted.** The finder's report may match immediately, on the same submit.
The current dashboard treats that as a hero card. That is right, and the timing is
counterintuitive enough to deserve a short explanation, because the finder did nothing special
and now has a match.

## 8. Journey C, the handover

The only flow with two people in it, and the one the design has to carry. The states are in
`core/services.py:118-168`; the current interface is in `templates/match.html`.

**Possible Match.** The comparison. Two report panels side by side, plus a third panel for the
factor breakdown (`templates/match.html:19-65`). The user is asked to make a trust decision from
public fields only.

Design direction: this is the most important screen in the product and it is currently the
least composed. The two reports share a three-column grid with the score breakdown, so the
things being compared get half the width. Make the two reports the primary axis, full width,
aligned field by field so a difference is visible as a difference. Put the breakdown below or
beside them, not as an equal third column.

The notice at `templates/match.html:15-17` is correct and should be promoted, not demoted.

**Proposing.** A two-field form, rendered through Django's `as_p` (`templates/match.html:78`),
so it does not use the app's field component and inherits only the generic `label`, `form p`,
`helptext` and `errorlist` rules in `static/app.css`. Server-side errors therefore appear as a
red list next to an unstyled input with no red border and no field-level message, because the
red border rule is scoped to `.field:has(.errorlist)`
(`static/app.css:705-711`). Two field styles coexist in the codebase as an accident. Fix by
rendering the handover form with the same markup as the wizard, not by adding more `form p`
selectors.

**Handover Proposed.** The other party sees a waiting state with an accept button
(`templates/match.html:91-97`). The proposer sees the meeting details and nothing to do. Neither
side is told what happens if the other person never responds, and the meeting can be proposed
for a time that is then never attended.

**Handover Scheduled.** Contacts unlock (`core/views.py:242`) and the meeting is shown
(`templates/match.html:83-89`). The "Confirm item returned" button is rendered whenever the
state is `Handover Scheduled` (`templates/match.html:114`), but the server refuses until
`meeting_at` has passed (`core/services.py:160-161`). So a user can click a live button and get
a server error. The button should be disabled with an explanation until the meeting time has
passed, showing the time in the user's own timezone framing even though the value is Pakistan
time (`Asia/Karachi`, `config/settings.py:11`).

**Returned.** The match page's eyebrow still reads "Possible match" (`templates/match.html:8`)
because it is hardcoded, and the state name appears far below in the handover panel
(`:70`). A completed handover is titled "Possible match". Every state needs its own heading.

**Rejected.** Dismissal is confirmable and restorable
(`templates/match.html:106-112`, `static/app.js:157-171`), which is the one place the app gets
recoverable destructive actions right. The rejected state shows a restore option only to the
user who dismissed it, which is correct but unexplained in the copy.

## 9. Screen-by-screen direction

### Screen 1. Sign in and register

Keep the split layout, the three-step explainer, and the privacy promise. Fix the mixed-language
placeholder, verify the password confirmation field, and add one line answering the question a
first-time visitor actually has: you cannot search for a lost item, you report it and we check.
The "Forgot password?" link is currently unreachable, see section 17, defect 6.

### Screen 2. Continue a saved draft

Twenty-two lines, and it asks the right question. The problem is the framing: it offers "continue
the Lost draft" or "fill a new one", and the second destroys the first
(`templates/resume_draft.html:19`, the handler deletes the existing draft). Discarding a saved
draft needs a confirmation, not a bare button. Also, "you already have an unfinished draft"
(`:13`) does not explain that only one is kept, so a user with two half-finished reports has
already lost one.

### Screen 3. Dashboard

Redesign this one first. It currently stacks four concerns in 211 lines: four stat cards, an
optional hero match, a secondary attention list mixing matches and drafts, the active reports,
and a collapsible history. The hero card duplicates the whole comparison block twice
(`templates/dashboard.html:46-78`) purely to swap the yours and theirs labels, which is a
template that is asking to become a reusable partial.

Direction: one clear primary action at the top, which is either the single match that needs a
response or a clear "nothing needs you" state. The four stat cards are summary information that
duplicates information the sections below already show, and they push the hero card down. Consider
moving them below the fold or into the reports page. The history should be collapsed by default
and stay collapsed. The colour legend at the bottom (`dashboard.html:203-208`) explains four
pill colours that are also the only status signal, so status must not be carried by colour alone.

### Screens 4 to 8. The wizard

Keep the step rail (`templates/wizard.html:22-29`) and the explicit save. Give each step a real
question as its heading, not a field-group label: step 2 is "Item details", which tells the user
nothing about why they are being asked. The step 5 review needs a count of the private answers
recorded, and a link back to step 4. Error messages must be the validator's own text, see section
17, defect 3.

### Screen 9. Report detail

The quietest screen and the one that most needs an explicit empty state. When there are no
matches, the whole matches panel disappears (`templates/report.html:43`), so a report that is
still being checked looks identical to a report that will never match. For a lost and found app
this is the wrong default silence. Show "no matches yet, we keep checking", with the date the
report was filed, so the user knows the wait has started.

The QR block (`templates/report.html:25-32`) is well handled: it appears only for Lost reports
(the Found-on-Found problem it fixed is recorded in `TODO-INCREMENTAL.md`), and it comes with a
download link, which is what makes the claim flow work when the two people are not in the same
room.

### Screen 10. Match review and handover

Section 8 covers this fully. In short: two reports as the primary axis, aligned field by field,
with the breakdown subordinate, state-correct headings, and the return button gated on time.

### Screen 11. Reports history

A competent table with filters that preserve themselves across pagination
(`templates/reports.html:25-27`). Two things to change. Seven different date formats are in use
across the app and this screen uses `d-m-Y` (`:20`); pick one. And the search placeholder says
"Title or location" (`:11`), which is honest but leaves the user not knowing that description
text is not searched. Either search everything and say so, or keep the honest placeholder and
make it a proper label rather than a placeholder.

### Screen 12. Management queue

Needs the most work for the least glamorous reason. "Remove from listings" is a single click
with no confirmation and no undo (`templates/management.html:33`), while the match dismissal
right next door in the product does confirm
(`static/app.js:159`). Close and Remove are styled almost identically and sit adjacent
(`templates/management.html:32-33`), which is a misclick waiting to happen. There are no filters
and no pagination; `TODO-INCREMENTAL.md` lists pagination as pending increment 3 work. The queue
shows the full public description with no indication of report volume, so at any real campus
size it becomes unusable.

### Screen 13. Public claim page

Does not exist. The wireframe brief describes it; the code redirects into the wizard. See
section 18, question 1.

## 10. The three structural problems

These are the three findings that should shape the redesign, because fixing them changes the
product's shape rather than its paint.

### 10.1 Step 4 can ask for 27 fields with no grouping

`core/forms.py:143-211` builds step 4 from the category. For a wallet the base is colour,
material, and visible logo (`:153-156`), plus contents as five checkboxes (`:159`). Selecting CNIC
adds a 13-digit field (`:163`). Selecting bank cards adds a count from 1 to 5 (`:165`) and then
per card an issuer, an optional free-text issuer, and a full 16-digit number (`:171-174`), which
is 15 fields at five cards. Cash adds two (`:176-177`), a driving licence adds one (`:179`),
other items adds one (`:181`), and a distinguishing mark is always there (`:182`). That is
roughly 27 fields on one step.

Every one of them renders as a flat sibling `<div class="field">` in the same loop
(`templates/wizard.html:40-60`). There is no fieldset, no group heading, no progressive
disclosure, and no summary. A user who selected "Bank cards" and typed a 5 gets three new
questions per card, up to fifteen at once, in the middle of a flat list.

Direction: group step 4 into labelled sections the user can collapse and confirm, treat each
selected contents checkbox as a small sub-form with its own heading, and give step 4 a review
and correct affordance. Splitting step 4 into two steps is defensible if the 5-step rail is
reworked, since the rail is already the strongest piece of wizard design in the product.

The refresh round trip that grows the form is a full page load with no progress indicator
(`static/app.js:10-19`). On a 15-field expansion that will feel slow on a phone. Whatever design
you choose, the round trip needs to be visible.

### 10.2 The dashboard carries four jobs and one of them is broken

Covered in screen 3. The structural point: the dashboard is a priority-ordered task list, but it
is built as a set of stacked sections with a duplicated comparison block, and the most important
destination after a submit does not exist as an anchor. The post-submit redirect has been
pointing at an element that was never rendered.

### 10.3 Step 3 puts a spatial decision in three controls

The Leaflet map, the geolocation button, and the latitude and longitude number fields all write
`Report.lat` and `Report.lng`, and all three are correct and must survive. The design problem is
that they are presented as equals. In practice a person who lost a wallet remembers a building,
not a coordinate, so the map and the place name are the real controls and the numbers are a
fallback for a person who genuinely knows their coordinates. The interface currently gives the
numbers equal visual weight, and the map is injected before its own field group
(`templates/wizard.html:41-49`) so it is not visually attached to the values it writes.

Also note the map has no test of any kind, in either the unit or the browser suite, and it
depends on a JavaScript patch to Leaflet's marker path that would silently break the pin on
nested URLs (`static/app.js:41-42`). Treat step 3 as untested and re-verify it by hand after any
change.

## 11. Design system direction

The honest starting position: there is almost no system. `static/app.css` is 1,964 lines with 17
colour custom properties in `:root`, a light theme only, no dark mode, no spacing scale, no
elevation scale, and **no type system at all**. It contains exactly one `font-family`
declaration, a monospace stack, used for one element. The four font files in `static/fonts/` and
their four `@font-face` rules live in `static/auth.css` (`static/auth.css`, referenced by
`templates/auth.html:8`), so Fraunces and Inter load on the login and registration pages and
nowhere else.

**Start here.** Move the `@font-face` block into `app.css`, set `font-family` on `body`, and the
whole application gains a type system from assets that are already in the repository. Carry
`static/Fraunces-OFL.txt` and `static/Inter-OFL.txt` with them. Then define, in this order:

- **A type scale** with a small number of steps and named roles, replacing the current ad-hoc
  sizes. Headings, body, small print, and the two dense contexts (the wizard fields, the report
  comparison) need explicit roles.
- **A spacing scale** on a consistent step. The stylesheet currently uses many one-off margins.
- **A colour role set** mapping the 17 existing variables onto roles rather than colours, so
  `var(--blue)` becomes "action" or "focus" and can be re-themed without hunting. The current
  17 are already close to this: five blues, four semantics, and a set of surfaces.
- **One field component.** Not two, and not a `form p` fallback. The wizard loop at
  `templates/wizard.html:40-60` and the handover's `as_p` at `templates/match.html:78` must
  produce identical markup, so error treatment, help text, and focus rings cannot diverge.
- **One status treatment.** Open, returned, closed, removed, draft, and the four match states are
  currently a mix of `.pill`, `.badge`, `.tag`, and `.dot` with overlapping meanings. Pick one
  component and map every state onto it, with a text label always present.

**Iconography.** There is no icon set. The only vector art is an inline SVG wordmark
(`templates/auth.html:16-21`) and a pair of character entities used as arrows and chevrons
(`templates/dashboard.html:54`, `:183`). Introducing an icon library means a build step or
vendored files; the current character-entity approach has run out of road for a real
destructive-versus-reversible distinction.

## 12. Content and voice

The existing copy is better than most of the interface. `templates/match.html:16` and
`templates/auth.html:39` are exactly the right register: plain, specific, and honest about
limits. Keep that voice and apply it to the rest.

Rules worth writing into the redesign:

**Second person, active, present tense.** "Compare the details and decide how to proceed"
(`dashboard.html:42`) is right.

**Say the limit.** "We cannot guarantee the recovery of your item"
(`templates/auth.html:95`) and "Match scores indicate similarity"
(`templates/wizard.html:94`) are both good and both rare. More of these, not fewer.

**Never promise a match.** The app has no way to tell a user their item will be found, and no
interface should imply it. The absence of a "no matches yet" state on the report screen is the
clearest violation of this in the product.

**Name the time.** "Saved 14:05" is fine. "Saved 2 hours ago" would need care, because the
timezone is `Asia/Karachi` (`config/settings.py:11`) and the user may not be. Prefer absolute
local times on anything the user will compare against a meeting, since the meeting is stored and
displayed in the same zone.

**Pick one language.** The email placeholder is Roman Urdu (`templates/auth.html:99`); everything
else is English. This is the kind of inconsistency that reads as a bug rather than a choice.

**Avoid the word confidence** for match scores, per principle 1.

## 13. Accessibility targets

Present today and worth preserving: `role=status` on the message loop and the privacy hint,
`role=alert` on the field error and the meeting error, `aria-expanded` on all three disclosure
controls, `aria-controls` wiring the sidebar and the history toggle, `aria-label` on icon-only
controls, `:has()` selectors for error states, a `prefers-reduced-motion` block
(`static/app.css`, `227-238`), and a 3px focus ring on form controls (`:1049`). The browser test
checks computed fonts, contrast, ARIA, and the mobile drawer
(`core/test_browser.py:11`).

Gaps to close, in order of how much they matter here:

1. **The generic error string.** `templates/wizard.html:54` renders "Invalid input. Please enter
   a correct value." for every field error, and the validator's actual message, which is
   specific and useful, is discarded. This is both an accessibility failure and the most common
   thing a user will read. Fix first.
2. **Status by colour.** Four pill colours plus dots, with meaning carried mostly by hue. Every
   status must carry a text label. The status badge and the pill are different components doing
   the same job.
3. **Focus management on page transitions.** The wizard is a sequence of full page loads. Focus
   after a step change lands wherever the browser decides, usually the top. Announce the step
   change, and move focus to the step heading.
4. **Step 4 field grouping.** Grouping the 27 fields into fieldsets, as section 10.1 requires,
   also gives every group a legend and makes it navigable by heading. Solve the design and
   accessibility problems with the same change.
5. **Map alternatives.** A Leaflet map has no keyboard equivalent, and the number fields are its
   only accessible path. Label the group, keep the number fields reachable and clearly
   associated, and make the status line announce pin changes.
6. **Live region discipline.** The privacy hint uses `role=status` and the geolocation failure
   uses `role=alert`. Keep the distinction, and do not put the whole score breakdown in a live
   region when it updates.
7. **Target sizes** on the disclosure controls, which are clickable `<div>` elements for the
   history toggle (`templates/dashboard.html:181`) and the sidebar toggle. A clickable div is not
   focusable and has no role.

## 14. Responsive strategy

Three breakpoints exist today: 900, 700, and 640 px (`static/app.css:1055`, `:1100`, `:1360`).
The sidebar becomes an off-canvas drawer below 700 px, opened by a mobile bar button
(`templates/base.html:13-19`, `static/app.js:173-193`). The mobile drawer is covered by a
browser test at 390 px (`core/test_browser.py:11`).

**Mobile is the primary case, not a fallback.** A person who loses a wallet on campus is
standing there with no laptop. A finder scanning a QR is on a phone. The current 390 px test
covers the drawer and the wallet wizard flow, so those two paths are known to work at phone
width. Everything else is unverified.

Specific things to check by hand, because nothing tests them: the two-column report comparison
in `templates/match.html:19` at 390 px, the two-up yours and theirs comparison in
`templates/dashboard.html:48-59`, the 27-field step 4, and the handover form with its error
list. Step 4 at phone width is the highest-risk screen in the product and has no coverage.

Decide one question for the redesign and state it: is this a mobile-first app with a desktop
layout as the second case, or a desktop app that degrades? The current stylesheet reads as the
latter, and the users read as the former.

## 15. States every screen needs

The app has five empty states in total and almost no error states. This is the checklist to work
through, because the missing states are where lost and found apps lose trust.

| State | Where it is needed | Status today |
|---|---|---|
| First run, zero reports | Dashboard, sidebar | Sidebar hides nav; no welcome |
| No matches yet, still checking | Report detail | Panel absent, silence |
| No matches after a handover elsewhere | Report detail | Panel absent, silence |
| Match found, nothing to do | Dashboard hero | Section hidden entirely |
| Draft exists, wizard abandoned | Dashboard, login redirect | Banner only |
| Loading, step 4 refresh | Wizard step 4 | None, full page load |
| Loading, geolocation pending | Wizard step 3 | Status line only |
| Server error, form resubmitted | All forms | Django 500, no template exists |
| Form validation failed, all errors | All forms | Generic string, defect 3 |
| Network failure on submit | All forms | None |
| Permission denied, not your report | Report, match | None found |
| Report already resolved, QR scanned | `closed_notice.html` | Exists, good |
| Staff queue empty | Management | Exists, good |
| Search returned nothing | Reports | Exists, good |
| Contact details still locked | Match | Exists, but as a permanent empty box |

The last row deserves attention. The contact box always renders
(`templates/match.html:122-130`), so in every state before scheduling there is a labelled
"Participant contact details" section containing only the sentence explaining why it is empty.
That reads as a failed load rather than a designed state. Make it a locked affordance that says
what is needed to unlock it, or hide it.

## 16. Trust and privacy as a design surface

The product's whole argument is that private data stays private. That argument is currently made
in four places: the login page (`:39`), one muted sentence on step 4 (`wizard.html:34`), a
native tooltip on every private field (`core/forms.py:218`), and one line on the match page
(`match.html:63`). Four mentions across a five-step flow that collects a full bank card number.

Design this as a surface, not as copy:

**Explain the mechanism.** The user should be able to say, after reading, that the private
answers are compared between reports to produce a score and are never displayed to anyone,
including staff. The current tooltip says "not visible to other users or staff", which is
correct and is the right sentence in the wrong place, in the wrong form, at the wrong moment.

**Show the shape of the comparison, not the values.** Step 5 already says the questionnaire is
complete without showing it. Extend that idea: after a match, show which categories of evidence
agreed, so a user can trust the mechanism worked without seeing the values. The breakdown
already computes this shape at `core/services.py:77-83`; the private component is one number out
of 30 and cannot be decomposed without care, so agree on the granularity before building it.

**Never leak through a redesign.** `Report.answers` must not appear on the report detail screen,
the dashboard, the management queue, or any new notification surface. Increment 3 plans
notifications (`TODO-INCREMENTAL.md:58`), and notifications are the most likely place for a
private answer to escape into a message. Write that constraint into the notification design.

**Public fields are enforced, not filtered.** Ten regexes reject phone numbers, emails, CNICs,
roll numbers, IBAN phrasing, and "last 4 digits" from public fields
(`core/forms.py:37-53`), and the rejection tells the user to move the data into the private
questions (`:55-57`). So the product will hand a user a validation error for being helpful. The
interface should pre-empt it: show the rule on the field before the user types, not after.

**The map is a privacy surface too.** Coordinates are shared indirectly through the location
score, which is why a finder's map is deliberately empty
(`core/views.py:284-285`). The design should not offer a "show the owner exactly where" option
as an enhancement, and should not display a minified location to the matched party.

## 17. Consistency defects to fix first

Every one of these is verified in the source. The first three are the highest value in the
product.

1. **The post-submit jump is dead.** `core/views.py:196` redirects to
   `dashboard?new=<pk>#report-<pk>`. No template reads `request.GET`, and the only `id` in
   `dashboard.html` is `historyBody`. Add the anchor and a highlight, or drop the fragment.
2. **Changing category silently destroys the private questionnaire.**
   `core/views.py:170-171` drops `answers` when the category changes, with no warning. Warn,
   and offer to keep what still applies.
3. **Every wizard field error says the same thing.**
   `templates/wizard.html:54` prints a fixed string and discards `field.errors`. Print the real
   message, and put the field-specific help text in a form users can act on.
4. **Seven date formats in the templates.** `d-m-Y` six times, `M d` four times, then
   `d-m-y h:i A`, `d M Y, H:i`, `d M Y`, `H:i`, `d-m-Y H:i`. `M d` renders month first
   ("Sep 5") in a product that asks for `DD-MM-YYYY` everywhere (`core/forms.py:115`). Pick one
   format, and one time format.
5. **The score is presented four different ways.** "85%" with a bar on the dashboard
   (`dashboard.html:84`), "85/100" in a pill on the dashboard (`:133`), the match page (`:12`)
   and the report page (`report.html:57`), and bare component numbers with no denominator on the
   match page (`match.html:60`). One component, one presentation, and never a percentage.
6. **There is no password reset, and the link that would reach it is dead.**
   `templates/auth.html:80-81` guards `{% url 'password_reset' as password_reset_url %}` behind
   an `{% if %}`, so the unresolvable route silently yields an empty string and the "Forgot
   password?" link never renders. `config/urls.py` has no such route, and no `EMAIL_BACKEND` is
   configured. A user who forgets their password has no recovery at all. Increment 3 plans this
   (`TODO-INCREMENTAL.md:56`).
7. **"Remove from listings" has no confirmation and no undo.**
   `templates/management.html:33`, with Close styled almost identically beside it
   (`:32`). The match dismissal, a far less destructive action, does confirm
   (`static/app.js:159`). Give Remove the same treatment, and require a reason.
8. **"Possible match" is hardcoded on the match page.** `templates/match.html:8`, so a
   `Returned` handover is still titled "Possible match". Derive the eyebrow from `match.state`.
9. **Empty parentheses in two places.** `templates/match.html:32` and `:50`, and
   `templates/wizard.html:90`, render `{{ location }} ({{ location_detail }})` unconditionally,
   producing "Gulshan Block 7 ()" when the detail is empty. `templates/report.html:20` uses a
   period separator instead, so location renders three different ways across the app.
10. **The handover form bypasses the field component.** `templates/match.html:78` uses
    `as_p`, so server-side errors get a red list but no red input border, because
    `static/app.css:705-711` scopes that treatment to `.field`. Two field styles, one of them
    accidental.
11. **The return button is live before its time gate.**
    `templates/match.html:114` renders it whenever the state is `Handover Scheduled`, but
    `core/services.py:160-161` refuses until the meeting time has passed. Disable it and say
    when it will open.
12. **The contact box is permanently half empty.** `templates/match.html:122-130` always renders
    a labelled section that, in most states, contains only a sentence about why it is empty.
13. **A silent redirect on a locked report.** `core/views.py:137-139` redirects when a report is
    not `Open` or is `reserved`, without a message, so a user who clicks Edit after a handover
    is proposed gets no explanation. The `reserved` case has copy on the report page
    (`report.html:39`); the non-`Open` case has none.

## 18. Open questions

These need an answer from you before layout decisions harden. Each one changes the design
materially.

1. **Does a QR scan land on a claim page or in the wizard?** `docs/WIREFRAME-BRIEF.md` describes
   a public claim page; the code redirects into the wizard with a seeded draft
   (`core/views.py:279-286`). A claim page can explain the situation, set expectations, and
   collect consent to share the location. Redirecting straight to step 3 is faster and dumber.
   Which do you want?
2. **Can a lost item ever be searched for?** The only search is over your own reports. A public
   lost and found board is the obvious feature and would change the product's character, the
   privacy model, and the moderation load all at once. It is not currently deferred in
   `TODO-INCREMENTAL.md`, so the absence may be an oversight rather than a decision.
3. **Mobile-first or desktop-first?** Section 14. The answer decides the whole layout approach.
4. **What can be shown about a match without leaking private answers?** Related to principle in
   section 16. The breakdown is computed but the private component is a single number out of 30.
5. **Should step 4 split into two steps?** It can reach 27 fields. Splitting it means reworking
   the step rail, which is currently good.
6. **Does the dashboard need the four stat cards at all?** They duplicate the sections below and
   push the hero match down the page.
7. **Is a profile page wanted?** Increment 3 lists one (`TODO-INCREMENTAL.md:57`). It is a
   destination, which makes it an IA question as well as a feature question.

## 19. Suggested sequence

Ordered so that each step is verifiable and none of them depends on an unanswered question
except where noted.

1. **Fix defects 1, 3, 8, 9, 11, 12, and 13.** Small, local, and each is independently
   verifiable. Do these before touching layout, because they change what the layout has to
   carry.
2. **Fix defects 4, 5, and 10.** Introduce the one date format, the one score presentation, and
   the one field component. These are the foundations the redesign builds on.
3. **Answer open questions 1 and 3.** They determine the shell and the entry experience.
4. **Build the type system and the one field component properly** (section 11). Do this before
   any screen work, so the screen work is not done twice.
5. **Redesign the dashboard.** Highest traffic, and it has a browser test to hold it to.
6. **Group step 4** (section 10.1), then re-verify step 4 at 390 px by hand.
7. **Redesign the match screen** (section 8). It is the most important screen and the one with
   no browser coverage.
8. **Add a browser test for the map** before any map work, and one for the match screen.
9. **Then** consider dark mode, an icon set, and a build step, each as its own decision.

## 20. Related documents

- `UI-UX-OVERHAUL-BRIEF.md` at the repository root, the engineering counterpart: architecture,
  routes, data model, the server and browser contract, and the remaining defects.
- `docs/WIREFRAME-BRIEF.md`, the written screen spec for wireframe generation. Screen numbers
  match this document.
- `AGENTS.md`, the operating rules and project conventions.
- `TODO-INCREMENTAL.md`, live status. Increments 3 and 4 are pending and cover password reset,
  profile, notifications, management pagination, and deployment.
- `matching-architecture.md`, the scoring rules, including the NED-only baseline.
- `report-wizard-flow.md`, the step-by-step field contract.
- `report-structure.md`, the report and match data contract.
- `osm-integration-guide.md`, the Leaflet and tile setup.
- `PROJECT_ESSENCE.md`, the project vision.
