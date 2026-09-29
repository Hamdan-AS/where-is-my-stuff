# 5 UI styling directions for Where Is My Stuff?

Scanned `/home/claude` — 118 template(s), 1 CSS file(s).

## Full-Bleed Field Report

Answers the full-bleed hero idea directly: a photographic gradient hero with the headline anchored bottom-left instead of centered, which also fixes the dead-space complaint since the copy now occupies an edge instead of floating in the middle. Fraunces gives the headline weight without needing a bigger size.

Preview: `style_suggestions/full-bleed-field-report.html`

## Ledger

Leans into what the app actually is: a register of claims. Reports read as ledger rows (date, item, status) instead of cards, so a long report history stays scannable rather than turning into a stack of boxes. No badges at all, so the all-caps badge problem cannot recur.

Preview: `style_suggestions/ledger.html`

## Signal Board

Literal campus corkboard, since that's the real-world thing this app replaces. The hero is one slightly rotated pinned notice instead of a centered banner, and the matches/reports panels are smaller notices with their own tilt so nothing lines up into a uniform card grid.

Preview: `style_suggestions/signal-board.html`

## Quiet Directory

The most restrained option: one typeface, one accent color, left aligned throughout, dividers instead of shadows. Section labels use small-caps rather than uppercase text, so they stay quiet instead of shouting like the old badge did. Best fit if the goal is to look like campus IT infrastructure, not a startup landing page.

Preview: `style_suggestions/quiet-directory.html`

## Match Signal

Ties directly into the QR scan-to-claim flow already planned: the hero and every report render as a claim-ticket stub, with a colored edge stripe carrying the status instead of a badge. Once real QR codes exist this is the direction that will feel least like it was bolted on afterward.

Preview: `style_suggestions/match-signal.html`
