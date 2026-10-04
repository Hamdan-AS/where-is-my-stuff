# Login concept comparison

Open `/static/login-concepts/index.html` on the local v2 server. The current
`/login/` implementation is unchanged by this exploration.

## Design brief

Campus lost-and-found users need a clear way to sign in before reporting,
reviewing a match, or managing a QR label. Keep green and white, crisp campus
artwork without blur, compact readable text, and a discreet rounded recovery
notice that remains visible at the bottom.

Palette: forest `#244C32`, ink `#173D25`, muted green `#52675A`, pale green
`#EDF5EE`, border `#D5E2D7`, white `#FFFFFF`. Georgia supplies the editorial
headings from the reference; local Inter supplies labels, controls, and body
copy. Headlines range from 27 px on phones to 38 px on desktops. Phone inputs
use 16 px text and 44 px heights.

## Five layout directions and review

| Direction | Desktop structure | Phone adaptation | Assessment |
|---|---|---|---|
| Campus panorama | White copy over green campus scene / solid white form | Compact intro above form | Closest to reference; artwork competes with reading |
| White campus split | Copy and illustration window / unboxed form | Small illustration above form | Recommended balance of readability and identity |
| Return ticket | Forest claim-ticket half / white form half | Ticket heading and perforated form join | Distinct campus return motif, no background artwork |
| Quiet gateway | Small illustrated strip above centered form | Same focused stack | Simplest entry, less explanatory context |
| Campus side panel | Forest illustration column / white sign-in column | Illustrated header above full-width form | Practical desktop structure and predictable phone layout |

The first design draft risked five variants of the same rounded login card.
The final directions instead use different structures: a scene, a white split,
a return ticket, a centered gateway, and a full-height side panel. Alignment
remains left-aligned for reading; only the focused gateway centers its tabs.

```
Panorama      [ campus scene + copy | white form ]
White split   [ copy + image window | simple form ]
Return ticket [ forest ticket stub : white form ]
Gateway       [ compact campus strip ]
              [ centered form ]
Side panel    [ forest image column | white sign-in column ]
```

## Research

- [W3C authentication field guidance](https://www.w3.org/WAI/WCAG21/Techniques/html/H100):
  visible labels and correctly identified login/password fields support
  password managers and accessible authentication.
- [NN/g mobile registration and login guidance](https://www.nngroup.com/articles/checklist-registration-login/):
  keep the account flow familiar and allow users to reveal their password.

No invented social login or password-reset capability is shown. Forms are
visual prototypes: submission is intercepted locally and no account or login
request is made. Register tabs demonstrate styling, rather than a complete
registration flow. Selection is browser-local and does not apply the design.

## Validation

Playwright checked all five concepts at 1280 × 720, 390 × 844, and 320 × 844:
no horizontal overflow, no initial-page scroll, visible recovery notices,
submit buttons above the notices, and no backdrop blur. Password reveal and
preview submit feedback passed for all five. Gallery contains ten real iframe
viewports; switching to 320 px changed all five phone viewport widths to 320.
Selection feedback passed. No page JavaScript errors occurred in those checks.

Build the standalone HTML pages with `python scripts/build_login_concepts.py`.
Shared styling and scripts are in `static/login-concepts/`.
