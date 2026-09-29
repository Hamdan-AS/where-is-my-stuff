# Wireframe brief for an image generation model

Purpose: hand this file to an image generation model to produce greyscale wireframes
for **Where Is My Stuff?**, a lost-and-found web app that runs on any campus. Every screen name,
field label, and constraint below was read out of the running code, so the wireframes
match what the app actually does rather than an idealised version of it.

How to use it:

1. Copy the **Global style preamble** into every prompt.
2. Copy one **Screen block** per prompt, one image per screen.
3. Paste the **Negative prompt** at the end of every prompt.
4. Assemble the individual screens into one board using the **Board** block.

Write the output to `ui-previews/wireframes/`.

---

## The app in one paragraph

A lost-and-found service for any campus. A member signs in, reports an item they lost or found
in a five-step wizard, pins a location on a map, answers private matching questions, and
the system scores their report against everything else turned in. When two reports score
high enough the two owners see a side-by-side comparison, agree a public meeting place and
time, and hand the item over. Staff get a moderation queue. Losers can print a QR code on
a notice; finders scan it to claim the item.

---

## Global style preamble

Paste this at the top of every prompt.

```
A greyscale low-fidelity web wireframe for a university lost-and-found web app.

Render style: flat vector wireframe on a pure white canvas. Hairline 1px grey (#C8CCD0)
borders and 1px grey dividers. No shadows, no gradients, no rounded corners above 4px,
no colour, no filled colour blocks, no drop shadows, no 3D, no isometric, no glass or
blur effects, no textures, no photos, no illustrations, no people, no mascots, no
device frames, no laptop or phone mockup chrome, no browser chrome, no URL bar, no
traffic lights.

Type: labels and headings are short real English words, left aligned, dark grey #33363A.
Placeholder text inside inputs is light grey #9AA0A6. Body text is set small enough that
a 1280px wide page holds 4 to 5 labelled fields per column without crowding.

Accent: exactly one accent colour, a single desaturated blue #1F5FA8, used only for the
primary button fill, the active step marker, and the active sidebar item. Nothing else
is coloured. Status is a small dot plus a word, never a badge and never uppercase.

Input style: white fill, 1px grey border, 4px radius, 36px tall, label sitting directly
above the box. Every input shows a short format hint underneath in grey when the format
is unusual.

Buttons: 36px tall, 4px radius, label in plain sentence case.

Canvas: 1280 x 800 minimum, one screen per image, generous 32px outer margin.
```

---

## Non-negotiable rules

These are behaviour, not taste. If the wireframe contradicts them, the wireframe is wrong.

1. **Never draw a private matching answer as visible text.** Answers stay in masked boxes
   or read as "answered" ticks.
2. **Never draw a phone number, email, CNIC, card number, or roll number inside a public
   field.** The app screens those out of titles, descriptions and places on purpose.
3. **The contact field is private.** It is shown to the other party only after both sides
   accept a handover, so on the review screen it sits in a visually separate private block.
4. **Status is never a filled pill or an uppercase badge.** Use a dot plus a sentence-case
   word: Open, Returned, Closed, Removed, Match found.
5. **Dates are `DD-MM-YYYY`** in report dates. **Meeting date and time is
   `DD-MM-YY hh:mm AM/PM`**, for example `08-09-26 09:25 PM`.
6. **The map always keeps visible Latitude and Longitude inputs** next to it, because they
   are the keyboard and no-JS fallback when tiles or GPS fail.
7. **The sidebar is 240px and never collapses into a card.** Below 700px it becomes a
   single menu button bar.
8. **CNIC and card answers are 13 and 16 digits.** Show the length, never a value.

---

## The shared app shell

Nine of the ten screens sit inside this shell. Describe it once in each prompt.

```
Left sidebar, 240px, full height, white with a 1px right border:
  top: square logo mark, then "Where Is My Stuff?" and beneath it in smaller grey text
       "Lost & Found"
  nav, four items, 16px apart, each an icon outline plus a label:
    Dashboard
    My reports
    Create report
    Management        (staff only)
  bottom: a small bordered note, 1px blue border, pale blue fill, titled "Privacy",
          one line: "Keep identifiers out of public descriptions."

Right workspace, the remaining 1040px:
  top bar, 62px, white with a 1px bottom border, left side grey small text
  "Signed in" above a bold name, right side a circular avatar initial and a
  "Log out" text button
  content column, centred, max 1120px, 28px padding
```

---

## Screens

### Screen 1. Sign in and register

Route `/login/` and `/register/`. Two tabs, "Login" active.

```
Split screen, left 50% right 50%.

Left half: pale background.
  a small pill with a dot reading "Lost &amp; Found Service"
  large headline, two lines: "Reunite with what / you've misplaced."
  one paragraph of body text: "Report something you lost or found. We check it against
   every other report and help you get it back."
  a row of three short stats, each a bold word over a grey line:
    Report  / Lost or found items
    Review  / Possible matches
    Arrange / Safe handovers
  a bordered privacy note with a small shield icon:
    "We value your privacy. Your contact details are shared only after both
     people accept a handover."

Right half: a white card, 400px wide, centred vertically.
  two tabs side by side, "Login" active with a 2px blue underline, "Register" inactive
  small heading "Welcome back", grey line "Log in with the email you registered."
  labelled input, placeholder "Email", small envelope icon inside at the left
  labelled input, placeholder "Password", small eye icon at the right
  full-width primary blue button "Login"
  centred grey line: "Don't have an account?" then blue link "Register"
```

### Screen 2. Continue a saved draft

Route `/reports/new/` when a draft already exists. A small, calm screen.

```
The app shell, content column holding a single centred card, 480px wide.
  heading "You have an unfinished report"
  one grey line: "Saved 3 minutes ago."
  the draft's title in bold, with a small grey draft dot beside it
  two stacked full-width buttons:
    primary blue "Continue report"
    outlined secondary "Fill a new one"
  a grey footnote under the second button, two lines, beginning
  "This discards the unfinished report and starts over."
```

### Screen 3. Dashboard

Route `/`. The busiest screen. Draw the shell, then the content column in this order.

```
1. Page head
   h1 "Your lost and found activity"
   grey line "Here's what's happening with your reports."
   primary blue button on the right "Report another item"

2. Row of four equal stat cards, each: small grey label, large number, small grey line
     Open reports      2   Still being checked
     Matches to review 1   Compare the report details
     Handovers         1   Proposed or scheduled
     Returned          3   Completed reports
   the second card has a 2px blue left edge to mark it as the one needing action

3. "Needs your response" panel, full width, 2px blue left edge
   heading, grey line "A match was found. Compare the details and decide how to proceed."
   left half: two stacked mini rows, each a bold title and a grey location line
   right half, narrower:
     large "92%" then a horizontal progress bar, 92% filled in blue
     a small 5-row score table, label left, fraction right:
       Category 20/20, Location 18/20, Date proximity 15/15,
       Description 9/15, Private answers 24/30
     a bordered note: "This is a suggestion, not proof of ownership."
     two buttons side by side:
       primary blue "Respond to match"
       outlined "Dismiss"

4. "Also needs attention" panel
   heading plus grey line "Drafts and pending handovers, lower priority than a match."
   two rows, each: bold title, grey meta line, and on the right a small score
     "Blue Hydro Flask · Grey backpack"     right: "92/100"
     "Untitled report"  Saved 12-09-26 14:20   right: a grey dot and "Draft"

5. "Your active reports (2)" panel
   two rows. Each row is a 3-column grid, aligned vertically across rows:
     left, 90px, monospace: "LFD-001"
     middle, flexible, two lines: bold title, then grey "Lost on 12-03-25 · Main Library"
     right, 120px: a coloured dot plus the status word, then an outlined "View report"
   statuses on the two rows: "Open" and "Open"

6. A collapsed row, full width, a chevron and the text
   "History — returned reports (3)"

7. Status legend, small, four items on one line, each a dot plus a word
   Draft · Open · Match found · Returned
```

### Screen 4. Wizard, step 1 of 5, Type

Route `/drafts/<id>/?step=1`. The stepper is repeated on steps 2 to 4.

```
The app shell.

Stepper, full width, five numbered circles joined by a thin line:
  1 Type (filled blue, label bold) - 2 Details - 3 Location - 4 Matching - 5 Review
  steps 2 to 5 are hollow grey circles

Below, a two column content area, 60/40:

Left column:
  h2 "1. Type"
  grey line "Let's start with the basics."
  a bold mini heading "I want to report a"
  two radio cards side by side, each a card with an icon, a bold title, a grey line,
  and a radio at the right. The first is selected, 2px blue border:
     Lost item  / "I lost an item"
     Found item / "I found an item"
  labelled input "Item title", placeholder "e.g. Wallet, ID card, Keys"
  labelled select "Category", placeholder "Select a category"

Right column:
  labelled input "Date", placeholder "DD-MM-YYYY", with a small calendar icon at the right
  a small grey note under it: "Between 2000 and today."
  a bordered pale-blue note titled "Public fields" with two lines:
    "Your title, description and place appear on the public board."
    "Do not include phone numbers or ID numbers here."
  a full-width primary blue button, right aligned, "Next", with a chevron
```

### Screen 5. Wizard, step 2 of 5, Details

```
The app shell. Stepper, step 2 filled blue.

Single column, max 620px:
  h2 "2. Details"
  grey line "Describe the item so the right person recognises it."
  labelled textarea, 4 rows, "Public description",
    placeholder "e.g. Black leather wallet with a scratch on the front"
  labelled input "Contact", placeholder "Phone number or email",
    small help text under it, grey:
      "Shared only after both participants accept a handover."
  a bordered note with a small lock icon, two lines:
    "Move phone numbers, emails, CNIC, card and roll numbers into the private
     matching questions."
  two buttons at the bottom, right aligned:
    outlined "Back"
    primary blue "Save and next"
```

### Screen 6. Wizard, step 3 of 5, Location

```
The app shell. Stepper, step 3 filled blue.

Two column, left 42% right 58%, stacked on narrow screens:

Left column:
  h2 "3. Location"
  grey line "Where did this happen?"
  labelled input "Place", placeholder "e.g. Gulshan Block 7, near Ayesha Manzil"
  labelled textarea, 3 rows, "Location description", placeholder "e.g. Near the stairs"
  two labelled inputs side by side, half width each:
    "Latitude"  placeholder "24.8607"
    "Longitude" placeholder "67.0011"
  a small grey line under the pair:
    "Drag the pin or type the coordinates."
  a full-width outlined button with a target icon, "Use my location"
  a one-line grey status strip with a small info icon:
    "Location sharing is off. The map and the fields above still work."

Right column:
  a map placeholder, 340px tall, 4px radius, light grey fill, 1px border
  inside it, faint street-grid lines drawn in a slightly darker grey
  one pin marker, a circle with a small point, sitting near the centre
  bottom left of the map, a scale bar and a small "© OpenStreetMap" line in tiny grey
  beneath the map, a grey caption "Map data from OpenStreetMap"
```

### Screen 7. Wizard, step 4 of 5, Matching

The questions change with the category chosen in step 1. Draw the wallet variant.

```
The app shell. Stepper, step 4 filled blue.

  h2 "4. Matching"
  grey line "Only you and a confirmed match will ever see these answers."

  A bordered notice strip, pale blue, with a small lock icon, two lines:
    "These answers are private. They are never shown on the public board and
     never visible to staff."

  Two column form, 50/50:
    left:  select "Colour"                    placeholder "Select a colour"
           select "Wallet material"           placeholder "Select a material"
           select "Visible logo?"              placeholder "Yes or no"
    right: a field group titled "What was inside" with a checkbox row of five,
           each a square checkbox plus a label:
             CNIC  ·  Bank cards  ·  Cash  ·  Driving licence  ·  Other items
           below the checkbox row, one labelled input, a 13 character
           format hint in grey:
             "Full 13-digit CNIC"  placeholder "4210112345671"
           a second group titled "Bank cards", containing:
             select "Number of bank cards" placeholder "1"
             select "Bank card 1 bank or payment service"
             one labelled input "Bank card 1 full 16-digit number",
               placeholder "4111111111111111", grey hint "16 digits"
    full width, below both columns:
      select "Wallet distinguishing mark" placeholder "None, Scratch, Sticker, Tear, Initials"

  A small ghost button on the right, no border, grey text:
    "Update questions from my selections"

  A grey hint line above the buttons:
    "Save and next keeps completed answers."

  Two buttons at the bottom, right aligned:
    outlined "Back"
    primary blue "Save and next"
```

### Screen 8. Wizard, step 5 of 5, Review

```
The app shell. Stepper, step 5 filled blue.

  h2 "5. Review"
  grey line "Check this before you publish."

  Two stacked bordered panels.

  Panel 1, heading "Public details", with a small pencil icon and a
  right aligned outline "Edit" text button:
    a two column definition list, label left in grey, value right:
      Type          Lost
      Item title    Black leather wallet
      Category      Wallet / Purse
      Date          12-03-25
      Description   Black leather wallet with a scratch on the front
      Place         Main Library
      Coordinates   24.8607, 67.0011
      Contact       shown as a grey masked row of dots with the grey note
                    "Visible to a confirmed match only"

  Panel 2, heading "Private matching answers", lock icon, and a grey note
  "Never shown to other users or staff":
    a two column list, each row a grey question on the left and a masked
    value on the right, drawn as dots, each with a small grey tick:
      Colour Black · Material Leather · Logo No · CNIC matched · Mark Scratch

  A pale amber warning strip, one line, with a small warning icon:
    "You already have an open report titled 'Black leather wallet'."

  A full-width primary blue button: "Submit report"
  A grey line beneath it, centred, two lines:
    "Your report becomes visible to other students. You can close it any time."
```

### Screen 9. Report detail

Route `/reports/<id>/`.

```
The app shell.

  Breadcrumb, small grey: "My reports / LFD-001"
  Row: h1 "Black leather wallet" on the left,
       on the right a grey dot plus "Open", and an outlined "Edit" button
  A grey meta line under the title:
    "Lost on 12-03-25 · Main Library · Reported 12-03-26"

  Two column, 62/38:

  Left column:
    a bordered panel, heading "Public details"
      a two column definition list, same style as screen 8
    a bordered panel, heading "Matches for this report"
      if none: a centred empty state, a small outlined document icon,
        bold "No matches yet", grey line "We'll email you when something lines up."
      if one: one row, bold title, grey location line, and on the right
        "92/100" in monospace

  Right column:
    a bordered panel, heading "QR code", centred:
      a 160px square placeholder drawn as a simple 9x9 grid of
      irregular grey squares, a finder pattern in three corners
      grey line "Print this on a notice for the finder."
      an outlined button with a download icon "Download QR"
      a small grey note "Only lost reports show a claim code."
    a bordered panel, heading "Activity log"
      a vertical timeline, 4 entries, each a small dot on a vertical line,
      a grey timestamp and one line of text:
        12-03-26 09:14  Report published
        12-03-26 09:15  3 possible matches screened
        12-03-26 10:02  No match above threshold
        12-03-26 10:02  Waiting for more reports
```

### Screen 10. Match review and handover

Route `/matches/<id>/`. The most important screen.

```
The app shell.

  A back link, small: "← Back to matches"
  h1 "Potential match"
  A pale amber notice strip, full width, warning icon, two lines:
    "Similarity suggestion, not proof of ownership."
    "Review the details carefully and agree a safe handover place."

  Two equal columns, each a bordered panel:

  Left panel, heading "Lost report" with a grey dot and the word "Lost":
    a definition list, grey labels:
      Item      Black backpack
      Category  Bag
      Date      12-03-25
      Location  Main Library
      Description  Black backpack with red stripe.

  Right panel, heading "Matched report (Found)" with a blue dot and "Found":
    the same definition list, same row order, so the two can be read across

  A third full width panel, heading "Match details":
    two columns of five rows, each row a small green tick, a question, and
    a green "Yes" or amber "No":
      Same item title, Same category, Similar date, Similar location,
      Similar description
    then a divider, then five rows reading "Similar CNIC / Similar card
    number / Similar brand / Similar colour / Similar mark" with a mix of
    Yes and No, and the last two greyed out
    a bordered green note with a lock icon, two lines:
      "Private details. Visible to the other person or staff only after
       you both confirm. Do not write down what you saw here."

  Two panels side by side at the bottom:
    Left, a blue bordered panel, heading "Propose a handover", with a location pin:
      labelled input "Meeting place",
        placeholder "e.g. Gulshan Library, Admin Block"
      labelled input "Suggested date and time",
        placeholder "DD-MM-YY hh:mm AM/PM", with a calendar icon
      a full-width primary blue button with a send icon "Propose handover"
    Right, a red bordered panel, heading "Dismiss this suggestion",
      with a trash icon:
      grey line "Not a match? You can dismiss this suggestion."
      a full-width red outlined button with a trash icon "Dismiss this suggestion"
      a grey footnote, two lines:
        "You will be asked to confirm, and you can restore it later."
```

### Screen 11. Reports history

Route `/reports/`. The list screen, where density matters.

```
The app shell.

  Page head: h1 "My reports", grey line "Everything you have reported.",
  a primary blue button on the right "Report another item"

  A filter strip, one row, small:
    segmented control: All · Open · Returned · Closed
    a small search input, placeholder "Search title or ID"
    a small sort select "Newest first"

  A single table, 7 columns, 5 rows, zebra free, 1px row dividers only:
    ID (90px, monospace)  LFD-001
    Item (flexible, bold) Black backpack
    Type (80px)          Lost
    Date (110px)         12-03-25
    Created (110px)      12-03-26
    Status (130px)       a dot plus a sentence-case word
    (100px, right)       a blue text link "View"
  the 5 rows use IDs LFD-001 to LFD-005 and statuses
  Open, Possible match, Returned, Open, Closed

  Pagination under the table, small: "‹ 1 2 ›" and "Showing 5 of 5"

  A grey footnote under it: "Reports you close stay here permanently."
```

### Screen 12. Management queue

Route `/management/`, staff only. Denser than the student screens.

```
The app shell. The sidebar's "Management" item is the active one.

  Page head: h1 "Report management", grey line "Review, park and close reports."
    a right aligned outlined button "Export CSV"

  A row of four small stat chips, label and number inline, not cards:
    Needs review 4 · Parked 2 · Open 27 · Closed today 6

  A two column layout, 70/30:

  Left: a table, 6 columns, 6 rows:
        ID | Item | Type | Status | Owner | Age
        LFD-004 | Calculator | Found | Open | 2h
        LFD-002 | Water bottle | Lost | Parked | 5h
        ...
      a grey line under it: "Sorted by newest first."

  Right: a "Selected report" panel, showing the staff view of LFD-004:
        a grey dot plus "Open"
        bold "Calculator", grey "Found on 09-03-25 · Cafeteria"
        a divider
        a 4 row definition list: Owner (email, greyed), Public ID, Created, Last activity
        a divider
        a small grey line "Private answers are not shown to staff."
        three stacked full-width buttons:
          primary blue "Close as returned"
          outlined "Park for review"
          red outlined "Remove report"
        a grey footnote, two lines:
          "Removing hides the report from both sides. It cannot be undone."
```

### Screen 13. Public claim page

Route `/r/<uuid>/found/`. This is the page a member of the public opens from a printed
notice. No sidebar, no app chrome.

```
Narrow centred column, 460px wide, on a pale background, no shell.

  A small centred logo mark and the wordmark "Where Is My Stuff?"
  A bordered card:
    a small grey label "CLAIM CODE"
    h1 "Black leather wallet"
    grey line "Reported lost on 12-03-25 · Main Library"
    a divider
    a 3 row detail list:
      Colour   Black
      Material Leather
      Mark     Scratch, front left corner
    a divider
    a labelled input "Your contact details", placeholder "Phone or email"
    a labelled textarea, 3 rows, "How do you recognise this item?",
      placeholder "Describe a detail only the owner would know"
    a full-width primary blue button "Claim this item"
  A grey privacy line under the card, two lines:
    "Your contact details go to the person who reported the item, not to staff."
```

---

## Component inventory

If the model needs a component sheet, ask for it with this block.

```
A greyscale component sheet, 1280 wide, on white, arranged in a 4 column grid with
one line of caption under each item. No colour except one desaturated blue #1F5FA8.

Column 1, navigation:
  sidebar, 240px, with logo block, four nav rows, one of them active in blue
  top bar, 62px, with a name block, an avatar circle and a text button
  mobile menu bar, 56px, with a "Menu" button and a compact logo
  a 5 step stepper, circles 1 to 5, the first filled blue

Column 2, input and controls:
  labelled text input, 36px, 4px radius, with placeholder
  the same input in an error state, 2px red border, red helper line underneath
  the same input in a disabled state, grey fill, grey placeholder
  labelled textarea, 3 rows
  select with a chevron, showing "Select a category"
  date input with a calendar icon at the right, showing "DD-MM-YYYY"
  a password style input, digits only, showing dots, with "16 digits" as a grey hint
  a radio card, 1px border, icon, bold title, grey line, radio at the right
  a checkbox row of five items, square checkboxes
  a segmented control of four options, the first active

Column 3, buttons and status:
  primary button, blue fill, white label
  secondary button, 1px grey border, dark label
  destructive button, 1px red border, red label
  a ghost button, no border, grey label
  a status dot plus word, four variants: Open, Returned, Closed, Match found
  a score readout, large "92%", with a 92% filled progress bar
  a 5 row score table, label left, "20/20" right

Column 4, containers:
  a panel, white, 1px border, 8px radius, 20px padding
  a notice strip, three variants: pale blue informational, pale amber warning,
  pale red error, each with a leading icon
  a definition list, 6 rows, grey label left, dark value right
  a table, 6 columns, 4 rows, 1px row dividers, no vertical lines, no zebra
  a map placeholder with a pin and a scale bar
  an empty state, centred icon, bold line, grey line
```

---

## Sample data to place in the wireframes

Fictional, but shaped like the real thing so spacing stays honest.

```
Report IDs        LFD-001, LFD-002, FND-003
Titles            Black leather wallet, Grey backpack, Calculator,
                  Blue Hydro Flask, Water bottle, Student ID card
Categories        Wallet / Purse, Bag, Electronics, Cards / IDs, Keys
Kinds             Lost, Found
Places            Main Library, Central Cafeteria, Civil Engineering block,
                  Gulshan Block 7
Dates             12-03-25, 09-03-25, 28-02-25  (all DD-MM-YY)
Statuses          Open, Returned, Closed, Removed
Match states      Possible Match, Handover Proposed, Handover Scheduled, Returned
Scores            92/100, 78/100, 64/100
Score breakdown   Category 20/20, Location 18/20, Date proximity 15/15,
                  Description 9/15, Private answers 24/30
Meeting time      08-09-26 09:25 PM
Names             Ali Khan, Sara Ahmed
Numbers to mask   any CNIC, card number, phone or email
```

---

## Negative prompt

Append to every prompt.

```
Do not draw: colour beyond the single blue accent, gradients, shadows, glow, glass,
blur, 3D, isometric, neon, drop shadows, photos, photographs, stock imagery, people,
faces, hands, mascots, cartoons, illustrations, clip art, laptop frames, phone frames,
tablet frames, browser chrome, URL bars, traffic light buttons, macOS window buttons,
lorem ipsum, filler paragraph text, all-caps labels, uppercase badges, filled status
pills, gradient buttons, neon borders, handwritten text, illegible squashed text,
text longer than six words, real student names, real email addresses, real phone
numbers, real CNIC numbers, real card numbers, QR codes that contain data, flag
emoji, country flags, watermarks, signature text, page numbers, decorative icons
that carry no meaning, more than two typefaces.
```

---

## Board

Once the individual screens exist, assemble them with this block.

```
A presentation board, 2000 x 1400, white, showing 6 wireframe screens in a 3 by 2 grid
with even gutters, each screen scaled to fit its cell, each with a caption above it
in dark grey:
  1  Sign in and register
  2  Dashboard
  3  Wizard step 1, Type
  4  Wizard step 3, Location
  5  Match review and handover
  6  Management queue

Left margin, a narrow vertical strip of short grey notes, one per screen, stating the
user goal in under 8 words. No numbers beyond the captions. No logos, no mascots.
Keep every wireframe in the same flat greyscale style with the single blue accent.
```

---

## Known limits, and how to work around them

Image models garble text, badly, and this brief has a lot of real labels. Three
mitigations, in order of preference:

1. **Use the brief for layout, not for final text.** Take the generated wireframe as
   the composition, then set the real labels in the browser from the source. The
   per-screen blocks above double as a written spec for whoever types the labels.
2. **Ask for short text only.** Every label in this brief is one to three words on
   purpose. If the model still garbles, regenerate with the "no text" variant below.
3. **No-text variant.** Append this to any screen block when the model keeps inventing
   words:

```
Render the layout with no readable text at all. Replace every string with a light
grey rounded placeholder bar whose width matches the length of the real label. Keep
numbers as real digits. Keep one blue accent. The result should read as pure layout.
```

Also worth knowing before you spend tokens: the existing `ui-wireframe-final.png` in the
project root is stale. It shows a four-step wizard and a sidebar with "Possible matches"
and "My profile", neither of which exists any more. The wizard is five steps
(`views.py:201` passes `[(1,"Type"),(2,"Details"),(3,"Location"),(4,"Matching"),(5,"Review")]`)
and the sidebar is Dashboard, My reports, Create report, Management.
