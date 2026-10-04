# Responsive repair verification

Completed 2026-10-03 in v2. The older sibling was left unchanged.

The app reflows by viewport width rather than device identity. At 900 pixels
and below, navigation moves to a drawer and the report wizard uses horizontal
progress links. At 760 pixels and below, comparisons, metadata, report filters,
QR label rows, and report history stack vertically. History keeps every field,
including the reported date, with labels instead of a wide scrolling table.
Mobile controls have larger touch areas and text inputs retain 16-pixel text.

The drawer includes Close menu and Log out, makes hidden navigation inert,
keeps keyboard focus inside the open drawer, closes on Escape, and resets when
the viewport switches to desktop. Leaflet recalculates its size when its
container changes width.

Playwright runs against Django's isolated test database with fictional users
and reports. The responsive regression checks dashboard, history, report,
match/handover form, QR labels, management, and all five wizard steps at
320, 390, 768, 900, 1024, and 1440 pixels. It checks page overflow, drawer focus,
logout availability, resize behaviour, and retention of history fields.
Phone screenshots were visually reviewed for dashboard, history, match,
location, matching questions, and QR labels.

## Playwright MCP follow-up

After session permissions changed, Playwright MCP became available. It checked
66 page/width combinations on an isolated preview at localhost:8087 with no
horizontal overflow or JavaScript errors. The menu, focus, Escape, and mobile
logout visibility passed. External map tiles returned HTTP 200. A fictional
handover was proposed by the owner and accepted by a second account at phone
width; contact details stayed locked before acceptance and appeared afterward.
The preview was left open on the dashboard at 390 by 844 pixels. The only
initial console error was a missing favicon. Existing app data was untouched.

All 101 tests passed after the repair; the strengthened wizard navigation
assertions were then rerun successfully. No migration changes were detected.
All six Playwright browser tests passed again after adding the map resize observer.
External map tiles did not load during the initial restricted run;
the pin and coordinate controls rendered, but tile delivery needs verification
on an unrestricted connection. Real iOS/Android browser testing remains useful.

Initial tool availability: the computer-use skill was read and initialized. @Browser
reported unavailable and the Playwright MCP endpoint returned an approval-policy
block. Verification therefore used the installed Python Playwright runner and
Chrome, not Playwright MCP. No local user reports were changed.
