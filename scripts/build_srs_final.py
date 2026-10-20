"""Build the course-format LaTeX source from the reviewed requirement baseline.

The PDF must be compiled with XeLaTeX; this script does not substitute a PDF renderer.
Run from any directory. Final editable source is output/pdf/SRS-Where-Is-My-Stuff.tex.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
baseline = (ROOT / 'docs/SRS-STAKEHOLDER-REVIEW.md').read_text(encoding='utf-8')

def esc(s):
    s = str(s).replace('**', '').replace('`', '')
    for a,b in [('→',' to '),('–','-'),('—','-'),('×',' x '),('>=','at least '),('<=','at most '),('≥','at least '),('≤','at most ')]: s=s.replace(a,b)
    return ''.join({'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}.get(c,c) for c in s)

parts=[]
def raw(s): parts.append(s.strip()+'\n')
def para(s): raw(esc(s)+'\n')
def heading(level,s):
    if level == 'section': raw(r'\Needspace{14\baselineskip}')
    elif level == 'subsection': raw(r'\Needspace{12\baselineskip}')
    raw('\\'+level+'{'+esc(s)+'}')
def bullets(items):
    raw(r'\begin{itemize}')
    for s in items: raw(r'\item '+esc(s))
    raw(r'\end{itemize}')
def table(headers,rows,widths=None):
    if widths is None: widths=[1/len(headers)]*len(headers)
    # Widths total exactly the usable line after intercolumn padding.
    cols='@{}'+''.join('P{'+str(round(w,4))+r'\dimexpr\textwidth-'+str(12*(len(headers)-1))+r'pt\relax}' for w in widths)+'@{}'
    raw(r'\begin{longtable}{'+cols+'}')
    head=r'\toprule '+' & '.join(r'\textbf{'+esc(h)+'}' for h in headers)+r' \\ \midrule'
    raw(head+r'\endfirsthead'); raw(head+r'\endhead');raw(r'\bottomrule\endfoot')
    for row in rows: raw(' & '.join(esc(v) for v in row)+r' \\ \addlinespace[3pt]')
    raw(r'\end{longtable}')
def req(i,text,accept,priority='High'):
    raw(r'\Needspace{6\baselineskip}\noindent\begin{minipage}{\linewidth}\textbf{'+esc(i)+r'}\hfill\textit{'+esc(priority)+r'}\par\nopagebreak')
    para(text); raw(r'{\color{muted}\textbf{Acceptance:} '+esc(accept)+r'\par}\end{minipage}\par\vspace{5pt}')

raw(r'''
\documentclass[12pt,a4paper,oneside]{report}
\usepackage[margin=1in,headheight=15pt]{geometry}
\usepackage{fontspec}
\IfFontExistsTF{Arial}{\setmainfont{Arial}\setsansfont{Arial}}{\setmainfont{TeX Gyre Heros}\setsansfont{TeX Gyre Heros}}
\IfFontExistsTF{Consolas}{\setmonofont{Consolas}[Scale=MatchLowercase]}{\setmonofont{lmmono10-regular.otf}[Scale=MatchLowercase]}
\usepackage{graphicx,xcolor,booktabs,longtable,array,enumitem,needspace,float}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,shapes.geometric,fit,calc}
\usepackage{fancyhdr,titlesec,caption,amsmath}
\usepackage[unicode,bookmarksnumbered,colorlinks=true,linkcolor=ink,urlcolor=ink]{hyperref}
\definecolor{ink}{HTML}{183C32}
\definecolor{muted}{HTML}{465552}
\definecolor{pale}{HTML}{EDF3EF}
\hypersetup{pdftitle={Software Requirements Specification - Where Is My Stuff?},pdfauthor={Project team},pdfsubject={CS-326, implementation-aligned SRS, version 1.0}}
\graphicspath{{assets/}{../output/pdf/assets/}{output/pdf/assets/}}
\newcolumntype{P}[1]{>{\raggedright\arraybackslash}p{#1}}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}
\setlength{\emergencystretch}{3em}
\setlist{nosep,leftmargin=1.5em,topsep=5pt}
\renewcommand{\arraystretch}{1.08}
\raggedbottom
\titleformat{\chapter}[display]{\raggedright\color{ink}\bfseries\Large}{\chaptername\ \thechapter}{7pt}{\huge}
\titlespacing*{\chapter}{0pt}{0pt}{20pt}
\titleformat{\section}{\large\bfseries\color{ink}}{\thesection}{0.6em}{}
\titleformat{\subsection}{\normalsize\bfseries\color{ink}}{\thesubsection}{0.6em}{}
\titlespacing*{\section}{0pt}{16pt}{6pt}
\titlespacing*{\subsection}{0pt}{12pt}{5pt}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\small Where Is My Stuff?}
\fancyhead[R]{\small SRS / Version 1.0}
\fancyfoot[C]{\small\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[C]{\small\thepage}\renewcommand{\headrulewidth}{0pt}}
\captionsetup{font=small,labelfont=bf,skip=8pt}
\setcounter{tocdepth}{2}
\tikzset{box/.style={draw=ink,rounded corners=3pt,fill=pale,align=center,minimum height=1cm,text width=3.3cm,font=\small},arr/.style={-{Stealth[length=2mm]},draw=ink},lab/.style={font=\footnotesize,align=center,fill=white,inner sep=2pt}}
% Edit these cover fields before submission. Student details intentionally left blank.
\newcommand{\GroupName}{\rule{7cm}{0.35pt}}
\newcommand{\SubmissionDate}{\rule{4cm}{0.35pt}}
\begin{document}
\fontsize{11}{13.2}\selectfont
\begin{titlepage}
\centering
{\color{ink}\bfseries\LARGE SOFTWARE REQUIREMENTS\par SPECIFICATION\par}
\vspace{1.1cm}
{\color{ink}\bfseries\Huge Where Is My Stuff?\par}
\vspace{0.35cm}
{\Large Lost and Found Web Application\par}
\vspace{0.4cm}
{\large Version 1.0\par}
\vspace{1.2cm}
{\bfseries Prepared by\par}\vspace{0.3cm}
Group: \GroupName\par\vspace{0.3cm}
\begin{tabular}{p{7cm}p{4cm}}
\textbf{Student name} & \textbf{Roll number}\\[15pt]
\hrulefill & \hrulefill\\[19pt]
\hrulefill & \hrulefill\\[19pt]
\hrulefill & \hrulefill\\[19pt]
\hrulefill & \hrulefill
\end{tabular}
\vfill
{\bfseries CS-326: Software Engineering\par}
Complex Engineering Activity\par
TE Batch 2024 / Fall Semester 2026\par
\vspace{0.6cm}
Submitted to\par
{\large\bfseries Dr. Fakhra Aftab\par}
\vspace{0.7cm}
Department of Computer \& Information Systems Engineering\par
NED University of Engineering and Technology\par
\vspace{0.6cm}
Submission date: \SubmissionDate\par
\end{titlepage}
\pagenumbering{roman}
\tableofcontents
\clearpage
\listoffigures
\clearpage
\pagenumbering{arabic}
\setcounter{page}{1}
''')

heading('chapter','Introduction')
para('Where Is My Stuff? helps people report lost and found belongings, review possible matches and arrange an in-person return. This specification defines the Release 1.0 behavior of the current web application.')
heading('section','Document Purpose')
para('This SRS records implemented functions, interfaces, quality requirements, data and acceptance criteria for developers and course reviewers. It is aligned with the project source inspected on 10 October 2026; proposed targets and known limitations are identified separately.')
heading('section','Product Scope')
para('The application supports registration, Lost/Found reporting, saved drafts, private category questions, deterministic matching, handover proposals, return recording, report history, report and personal QR codes, and staff moderation. It is intended for Karachi, but coordinate validation does not enforce a Karachi boundary. A match is a lead and does not verify identity, possession or ownership.')
heading('section','Intended Audience and Document Overview')
table(['Reader','Interest and suggested reading'],[('Course instructor / assessor','Chapters 1-2 for scope and stakeholders; Chapter 3 for requirements and models; Chapter 5 and Appendices A-D for data, traceability and evidence.'),('Project team / developers','Chapters 3-5 and Appendix A for behavior, field rules and data definitions.'),('Reviewers / future testers','Acceptance criteria beside requirements, Chapter 4 for quality targets and Appendix B for acceptance coverage.'),('Reporters, finders and moderators','Chapters 2-3 for user roles and interface behavior.')],[.29,.71])
heading('section','Definitions, Acronyms and Abbreviations')
table(['Term','Definition'],[
('Acceptance criterion','Observable condition used to decide whether a requirement is satisfied.'),('Actor','External person or service interacting with the application.'),('Bearer token','Secret URL value whose possession permits the corresponding personal-label scan.'),('CNIC','Computerized National Identity Card; a private questionnaire may request all 13 digits.'),('CPA','Complex problem-solving attribute in the supplied course brief.'),('CSRF','Cross-site request forgery; Django protects submitted POST forms with a token.'),('Draft','An owner-specific, unpublished set of report fields, optionally linked to an existing report.'),('Foreign key (FK)','Database reference to another table row.'),('Handover','The proposal and acceptance of a place and time to return an item.'),('HTTPS','HTTP protected by Transport Layer Security.'),('JSON','Structured key-value data used for drafts, private answers and score breakdowns.'),('Match participant','Owner of either report in a Lost/Found match.'),('MiB','1,048,576 bytes; the upload limit is 5 MiB.'),('Moderator','Staff account authorized to close or remove eligible reports.'),('ORM','Object-relational mapping; Django access to database records.'),('Primary key (PK)','Unique row identifier within a table.'),('QR','Quick Response code containing a report-entry URL or personal-label URL.'),('Reserved report','An Open report committed to a proposed or scheduled handover.'),('SRS','Software Requirements Specification.'),('UUID','Universally unique identifier used in report QR URLs.'),('WCAG','Web Content Accessibility Guidelines; accessibility conformance is a proposed target.')],[.27,.73])
heading('section','Document Conventions')
para('The document uses A4 pages, one-inch margins, single-spaced 11-point Arial text and numbered chapters aligned to the supplied template. Shall states required behavior. May identifies an optional feature. High, Medium and Low express relative priority, not verification status. Proposed explicitly marks an unapproved quality or operational target.')
para('FR identifies a functional requirement, UI an interface requirement, NFR a nonfunctional requirement, SEC a security rule, SAFE a safety requirement, BR a business rule, UR a user need, UC a use case and AT an acceptance scenario family. Functional IDs are retained from the earlier working draft. Version 1.0 is the formal document version. Requirement identifiers remain stable when chapter numbers change. Code names in the data dictionary retain their actual spelling.')
heading('section','Project Sources')
para('Requirements are based on the current project source: core/models.py, forms.py, services.py, views.py, templates and static assets. The public site was supplied by the project owner; its registration and login pages were observed on 10 October 2026. See Appendix D for deployment details.')

heading('chapter','Overall Description')
heading('section','Product Perspective')
para('Where Is My Stuff? is a Django web application for desktop and mobile browsers. It uses server-rendered pages, JavaScript map enhancements, a relational database, private media storage and OpenStreetMap tiles. It has no native mobile application or public report-search API.')
raw(r'''
\begin{figure}[H]\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  ctx/.style={draw=ink,rounded corners=4pt,fill=pale,align=center,
    text width=3.15cm,minimum height=1.25cm,inner sep=6pt,font=\small},
  flow/.style={-{Stealth[length=2mm]},draw=ink,line width=.6pt},
  flowboth/.style={{Stealth[length=2mm]}-{Stealth[length=2mm]},draw=ink,line width=.6pt},
  flowlabel/.style={font=\footnotesize,fill=white,inner sep=2pt,align=center}]
\node[ctx] (people) at (0,1.4) {Reporter / finder\\Moderator};
\node[ctx] (browser) at (5.3,1.4) {Web browser\\HTML, CSS, JavaScript};
\node[ctx] (app) at (10.6,1.4) {Django application\\Forms, views, services};
\node[ctx] (tiles) at (5.3,-1.8) {External map tiles\\OpenStreetMap};
\node[ctx] (db) at (10.6,-1.8) {Relational database\\SQLite / PostgreSQL};
\node[ctx] (files) at (10.6,4.3) {Private file storage\\Photos and QR images};
\draw[flow] (people.east)--(browser.west);
\draw[flowboth] (browser.east)--(app.west);
\node[flowlabel] at (7.95,2.25) {HTTP(S)};
\draw[flowboth] (browser.south)--node[flowlabel,left]{HTTPS tiles}(tiles.north);
\draw[flowboth] (app.south)--node[flowlabel,right]{ORM}(db.north);
\draw[flowboth] (app.north)--node[flowlabel,right]{read / write}(files.south);
\end{tikzpicture}
\caption{System context. The browser requests map tiles directly; Django reads and writes application data and private media.}\label{fig:context}
\end{figure}
''')
heading('section','Product Functionality')
bullets(['Register an account, sign in by email and password, select session persistence, and sign out.','Create a Lost or Found report through Type, Details, Location, Matching and Review steps; save progress on valid submissions.','Compare eligible reports using five weighted factors and a minimum private-evidence agreement rule.','Review a match, propose or accept a meeting, dismiss or restore an eligible suggestion, and record return.','View own dashboard and searchable history, including report status and activity events.','Generate a report QR entry route and create, deactivate or reactivate personal item labels.','Allow authorized staff to close or remove Open, unreserved reports without exposing private answers.'])
heading('section','Users and Characteristics')
table(['Viewpoint / actor','Needs, characteristics and authority'],[
('Primary: reporter','An everyday user with basic browser skills. May report both Lost and Found items, manage own drafts and labels, and view own reports.'),('Primary: match participant','A reporter involved in a specific pair. Reviews similarities and coordinates return. Can see report contacts only after acceptance.'),('Primary: report QR finder','A person following a report code. Must sign in, then independently complete a Found report using limited prefilled hints.'),('Public: personal-label finder','A person scanning an active item label. No account is needed to see the contact phone intentionally published by its owner.'),('Operational: moderator','Staff account using the management view. Can close/remove eligible reports; has no private-answer inspection function.'),('Operational: system administrator','Deploys the application, manages backups, configuration and account permissions. Database access is outside ordinary browser permissions.'),('Project / assessment','Student team and instructor review scope, traceability and quality; no end-user privileges are implied.')],[.29,.71])
para('The application shows public item details while withholding matching answers. Match participants receive contact numbers after the proposed handover is accepted. Moderators can manage reports without viewing private answers.')
heading('section','Operating Environment')
para('The local project uses Python 3.10 and Django 5.2.17. Development defaults to SQLite; production settings require PostgreSQL, private persistent storage, configured hosts, a secret key and HTTPS. User-facing dates use Asia/Karachi.')
heading('subsection','Observed Live Deployment')
raw(r'The owner-supplied registration entry point is \url{https://lost-and-found.54.252.227.103.sslip.io/register/}. The public origin is \url{https://lost-and-found.54.252.227.103.sslip.io/}.')
table(['Deployment detail','Observed value / evidence'],[
('Public identity','Where Is My Stuff? branding and the Report, Review and Arrange workflow appear on the live account pages.'),('DNS destination','The hostname resolved to IPv4 address 54.252.227.103 on 10 October 2026.'),('Transport','Chrome connected with normal certificate validation over TLS 1.3; the certificate subject matched the supplied hostname.'),('Public pages','GET /register/ and GET /login/ returned HTTP 200 and displayed the expected account forms.'),('Access boundary','Anonymous GET requests to /, /reports/, /labels/ and /management/ redirected to /login/ with the requested destination in next.'),('Reported edge server','HTTP Server header reported nginx/1.28.3 (Ubuntu). This identifies the reported web edge, not the complete hosting infrastructure.'),('Code correspondence','The served auth JavaScript was byte-identical to local static/auth.js. Branding, field names and anonymous route behavior also matched the inspected project.'),('Evidence scope','The live database engine, application commit, Python/Django versions, hosting account and authenticated workflows were not exposed by these public observations.')],[.27,.73])
para('A modern browser, cookies and JavaScript are required. Camera/QR scanning and printing are optional. No dedicated hardware is required. Minimum server capacity has not been measured; the proposed performance workload is defined in Chapter 4.')
raw(r'''
\begin{figure}[H]\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  env/.style={draw=ink,rounded corners=4pt,fill=pale,align=center,
    text width=3.6cm,minimum height=1.25cm,inner sep=6pt,font=\small},
  flowboth/.style={{Stealth[length=2mm]}-{Stealth[length=2mm]},draw=ink,line width=.6pt},
  flowlabel/.style={font=\footnotesize,fill=white,inner sep=3pt,align=center}]
\node[env] (client) at (0,1.3) {Client device\\Desktop or mobile browser};
\node[env] (host) at (6.2,1.3) {Application host\\Python / Django / WSGI};
\node[env] (persist) at (6.2,-1.8) {Persistent resources\\Relational database + private media};
\draw[flowboth] (client.east)--node[flowlabel,above]{HTTPS\\production}(host.west);
\draw[flowboth] (host.south)--node[flowlabel,right]{database / files}(persist.north);
\end{tikzpicture}
\caption{Deployment environment. Public traffic uses HTTPS; localhost development uses HTTP.}
\end{figure}
''')
heading('section','Design and Implementation Constraints')
bullets(['DC-01: Use the existing Django 5.2.17 monolith and server-rendered template architecture.','DC-02: Keep matching deterministic with the documented weights, minimum score and minimum private agreements; photographs do not contribute to similarity.','DC-03: Persist schema changes through Django migrations and preserve unique Lost/Found pairs. PostgreSQL workflows use a transaction advisory lock; the default SQLite configuration uses IMMEDIATE transactions.','DC-04: Store uploaded media outside a publicly served directory and authorize each media request.','DC-05: Preserve the five-step report workflow and the eight defined categories.','DC-06: Use Asia/Karachi for user-facing date/time interpretation. Event dates use DD-MM-YYYY; meetings use DD-MM-YY hh:mm AM/PM.','DC-07: Keep readable location text and manual latitude/longitude available independently of map tile loading. No geocoding service is implemented.','DC-08: Do not present a match, account or QR scan as proof of ownership or a guaranteed return.','DC-09: Production requires environment-supplied secrets, explicit allowed hosts, PostgreSQL and persistent private storage; development defaults are not a production acceptance result.'])
heading('section','User Documentation')
para('The interface provides field labels, hints and validation errors. The project README covers setup; a user guide is not included in the current application.')
heading('section','Assumptions and Dependencies')
bullets(['Users supply truthful item descriptions, independently observed locations and reachable contact numbers; the system cannot validate these claims.','Users can reach the app and allow session cookies. JavaScript supports dynamic questionnaires and maps; server validation remains authoritative.','Django, Pillow, qrcode, dj-database-url, python-dotenv and the PostgreSQL driver are application dependencies. The pinned Django version is 5.2.17; other declared dependency ranges remain those in requirements files.','External map tiles may be unavailable; typed location details and valid coordinates remain required and can be supplied manually. Browser geolocation depends on device permission and browser support.','Public QR URLs depend on a stable, reachable application hostname. Codes created on localhost are demonstration artifacts.','Operators are responsible for secure hosting, storage access and backup policy. Public deployment requires decisions on sensitive identifier collection and retention.'])

heading('chapter','Specific Requirements')
heading('section','External Interface Requirements')
heading('subsection','User Interfaces')
table(['Screen / UI ID','Required behavior'],[
('UI-01: account screens','Register with full name, unique email and validated password; sign in with email/password and remember-me; display actionable validation errors.'),('UI-02: report wizard','Show five ordered stages: Type, Details, Location, Matching, Review. Save a valid step on Save and next. Back links permit changes. Do not claim keystroke autosave.'),('UI-03: location','Provide a readable place, location description, map pin controls, optional device location, and manual latitude/longitude fields.'),('UI-04: dashboard / history','Show owner-specific summaries, saved drafts and active matches. Show all non-Removed owned reports through searchable, filtered, paginated history.'),('UI-05: review / match','Review public report fields and photo; keep phone/private answers on their earlier steps. Match page shows paired public descriptions and factor scores, meeting controls and conditional contacts.'),('UI-06: QR labels','Show item name, chosen phone, expiry and activation status; allow owner image download and state controls. Public scan distinguishes active from inactive.'),('UI-07: moderation','Expose a staff-only report list and eligible close/remove controls without private answers.'),('UI-08: responsive target','Proposed: at 360 CSS pixels width, core form controls and primary actions shall be usable without horizontal page scrolling. Verify separately from desktop observations.')],[.27,.73])
para('Common interface conventions are labeled fields, consistent navigation, back/cancel actions, visible report IDs and status, and inline form errors. Success notices follow a saved step or action. Appendix C contains localhost screenshots using synthetic data. Appendix D contains live registration/login screenshots. The figures identify their environment and do not constitute a complete usability or accessibility audit.')
para('Figures 3.1-3.2 show the dashboard, report flow and match-review design. Current implementation screens are shown in Appendix C.')
raw(r'\begin{figure}[H]\centering\includegraphics[width=\textwidth,height=.48\textheight,keepaspectratio]{wireframe-live-reference.png}\caption{Dashboard and match-review wireframes; the adjacent QR and live-login panels are design references.}\end{figure}')
raw(r'\begin{figure}[H]\centering\includegraphics[width=\textwidth,height=.24\textheight,keepaspectratio]{wireframe-report-flow.png}\caption{Five-step report flow: Type, Details, Location, Matching and Review.}\end{figure}')
heading('subsection','Match Review and Handover Interaction')
para('The match view shows paired public summaries and score factors. It withholds contacts until the other participant accepts; private answers remain hidden. A match score does not verify ownership.')
heading('subsection','Hardware Interfaces')
para('The application has no direct proprietary hardware interface. Browser file upload accepts an optional image from disk or a camera source supported by the device. Browser geolocation may provide latitude and longitude after user permission. QR codes are PNG images that can be printed and scanned by standard camera software; printing and scanning remain device/browser functions.')
heading('subsection','Software Interfaces')
table(['Component','Interface and exchanged information'],[
('Django and operating system','Python processes read static resources and configuration, use the system clock and write media through filesystem APIs. A writable private media directory is required.'),('Relational database','Django ORM reads/writes User, Report, Draft, Match, Event and QRLabel records. SQLite is the development default; PostgreSQL is required by the production settings.'),('Pillow / QR generation','Pillow decodes and normalizes image uploads. The qrcode library encodes report-entry or label URLs as PNG images.'),('Leaflet / map tiles','Locally served Leaflet displays externally fetched map tiles. Coordinates are form data; place text is not sent to a geocoding API.'),('Browser sessions','Django session cookie associates requests with an authenticated user. CSRF tokens protect submitted POST forms.')],[.29,.71])
heading('subsection','Communications Interfaces')
para('Browser requests use HTTP on localhost. The owner-supplied public deployment uses HTTPS, with TLS 1.3 observed on its account pages. Forms use ordinary encoded POST data and multipart upload for images. Views return HTML or protected PNG/JPEG streams; no email, SMS or chat delivery interface is implemented. The browser fetches HTTPS map tiles from tile.openstreetmap.de and retains OpenStreetMap attribution.')
para('Production settings enable secure session/CSRF cookies, HTTPS redirection, explicit hosts and response protections. Uploaded photos and owner-only label images use private, no-store responses. Public personal-label responses also use no-referrer. Only the token digest is stored in the label database field; the downloadable QR image necessarily encodes the bearer URL and must remain protected.')
heading('section','Functional Requirements')
heading('subsection','User Requirements and System Allocation')
userneeds=[
('UR-01','Access my account securely.','FR-ACC-01 to 06 / UC-01 / AT-01'),('UR-02','Publish a useful Lost or Found report.','FR-REP-01 to 04, 09 to 13; FR-VAL; FR-PHO / UC-02 / AT-02,03'),('UR-03','Save and resume unfinished work.','FR-REP-05 to 08,12 / UC-03 / AT-02'),('UR-04','See plausible item matches with understandable scores.','FR-MAT-01 to 08 / UC-04 / AT-04'),('UR-05','Agree on a meeting and control contact disclosure.','FR-HND-01 to 06,08,09 / UC-05 / AT-05'),('UR-06','Record an item as returned after the meeting time.','FR-HND-07; FR-HIS-05 / UC-06 / AT-05'),('UR-07','Find my reports, statuses and activity.','FR-HIS-01 to 06 / UC-07 / AT-06'),('UR-08','Help a finder start a report using my report QR.','FR-QR-01 to 04,10 / UC-08 / AT-07'),('UR-09','Create and control a printable contact label.','FR-QR-05 to 09,11 / UC-09 / AT-07'),('UR-10','Moderate eligible reports without viewing private answers.','FR-MOD-01 to 05 / UC-10 / AT-06')]
table(['ID','User need','Allocated requirements / use case / scenario'],userneeds,[.12,.38,.50])
para('The following requirements retain the original IDs and priorities. Acceptance statements define the expected observable outcome. The traceability matrix links each family to code locations and planned scenario coverage; the limited observations actually performed are recorded separately.')

overrides={
'FR-ACC-06':('The system shall protect submitted state-changing POST forms against cross-site request forgery.','A POST with a missing or invalid token is rejected without applying the submitted action. GET routes that create or update drafts are a documented limitation in Chapter 5.'),
'FR-HND-05':('The system shall show both saved report contact numbers to match participants after the other participant accepts the handover.','Both participants see the numbers in Handover Scheduled and Returned states.'),
'FR-HND-06':('The system shall withhold both saved report contact numbers while a match is Possible Match or Handover Proposed.','Neither participant sees the numbers before the other participant accepts.'),
'FR-QR-01':('The system shall generate a QR code containing the UUID URL of a report. The standard report interface offers this code for Lost reports.','The UUID URL opens the report-entry flow. The endpoint does not enforce Lost kind; see GAP-04.'),
'FR-REP-06':('The system shall let an owner resume saved draft data. Public fields and ordinary private choices shall be repopulated. Identifier inputs shall stay masked and shall not reprint stored values.','Saved fields persist after navigation; password-style identifier fields display blank and may require re-entry if the Matching step is resubmitted.'),
'FR-MAT-01':('The system shall compare a published report with opposite-kind, same-category Open reports owned by other users, excluding reserved candidates. Scoring shall reject same-owner, wrong-kind, closed or different-category pairs.','Publishing creates no new suggestion against a reserved candidate or a pair violating a scoring condition.'),
'FR-HIS-01':('The dashboard shall show the signed-in user\'s summaries, drafts and active matches. It shall show at most three Open reports and ten returned reports, with full report access through history.','The dashboard shows only owned reports, prioritizes handover actions and hides possible matches whose reports are reserved. Users with no visible reports enter the report/draft flow.'),
'FR-HIS-05':('The system shall persist actor and timestamp for report creation/edit, match state transitions, moderation and return events.','Each action writes an Event row for every affected report. The report activity view displays event text and time; actor identity remains available in the stored record.'),
'FR-QR-02':('A signed-in finder opening an eligible report QR shall create or reuse their newest new-report draft and seed kind Found, category, title, coarse place and today\'s date. The flow shall clear description, detailed location, contact, answers and coordinates before completion.','No report is automatically published. The finder must supply their own remaining fields. This flow can overwrite an existing new-report draft; see Chapter 5.'),
'FR-QR-06':('The QRLabel database row shall store a SHA-256 digest of the personal-label bearer token in token_hash and no separate raw-token field.','The row contains the digest and resolves a presented token. The stored QR image still encodes the token URL and is available only through owner-authorized image access.'),
'FR-QR-09':('An owner shall be able to deactivate or reactivate a personal label. Reactivation shall set expiry to six calendar months from the reactivation time.','Deactivation hides the number. Reactivation preserves the printed token and enables it until the newly calculated expiry; month-end days are clamped to the target month.')}
fr=[]
for line in baseline.splitlines():
    if line.startswith('| FR-'):
        c=[x.strip() for x in line.strip('|').split('|')]
        if len(c)==4:
            i,text,priority,accept=c
            if i in overrides:text,accept=overrides[i]
            if i.split('-')[1] in {'ACC','REP','VAL','PHO','MAT','HND','HIS','QR','MOD'}:
                fr.append((i,text,priority,accept))
families=[('ACC','Accounts and Authorization'),('REP','Reports and Drafts'),('VAL','Input Validation'),('PHO','Photographs'),('MAT','Matching'),('HND','Handover and Return'),('HIS','Dashboard and History'),('QR','Report QR and Personal Labels'),('MOD','Moderation')]
for family,title in families:
    heading('subsection',title)
    for i,text,priority,accept in fr:
        if i.startswith('FR-'+family+'-'):req(i,text,accept,priority)
    if family=='PHO':para('Upload limits: JPEG, PNG or WebP; at most 5 MiB; at most 6,000 pixels per side and 24,000,000 pixels total. Accepted images are decoded, orientation-corrected, resized without cropping, flattened on white when transparent, converted to RGB and stored as JPEG with a maximum 1,800-pixel edge. No visual recognition is performed.')
    if family=='QR':para('The report detail UI presents report QR codes for Open Lost reports. The underlying UUID routes do not enforce kind=Lost and the QR PNG endpoint is public to anyone with the UUID. A public UUID image contains a URL, not report contacts or private answers. The personal-label workflow is separate: an active bearer URL deliberately exposes the chosen phone without authentication.')
    if family=='HND':para('An existing scheduled handover has no cancel, reschedule or timeout action in the baseline. A return is recorded by either participant, with no second return confirmation. These limitations are reflected in the state model rather than implied as missing transitions.')

heading('section','Behaviour Requirements')
heading('subsection','Use Case View')
para('Reporter is the general signed-in actor; a match participant and a report QR finder are roles of that actor. A public label finder can scan without signing in. Staff has the separate moderation permission. The system administrator manages accounts through Django administration and operates the deployment.')
raw(r'''
\begin{figure}[H]\centering

\begin{tikzpicture}[x=1cm,y=1.45cm,uc/.style={ellipse,draw=ink,minimum width=6.5cm,minimum height=1.05cm,inner sep=0pt,text width=5cm,align=center,font=\small},actor/.style={align=center,font=\small\bfseries}]
\draw[rounded corners,draw=ink] (3,-.6) rectangle (10.6,10.05);
\node[anchor=west,font=\small\bfseries,color=ink] at (3.2,9.75) {Where Is My Stuff?};
\foreach \y/\id/\txt in {9/01/Register and sign in,8/02/Publish or edit a report,7/03/Save and resume draft,6/04/Review possible match,5/05/Arrange handover,4/06/Record return,3/07/Browse own history,2/08/Start Found report from QR,1/09/Manage or scan labels,0/10/Moderate report}
{\node[uc] (u\id) at (6.8,\y) {UC-\id\\\txt};}
\node[actor] (reporter) at (1,8.2) {Reporter};
\node[actor] (participant) at (12.2,5.2) {Match\\participant};
\node[actor] (finder) at (1,2.1) {Report QR\\finder};
\node[actor] (public) at (12.2,1.0) {Public label\\finder};
\node[actor] (staff) at (12.2,0) {Moderator};
\foreach \id in {01,02,03,07,09} {\draw[draw=ink] (reporter.east)--(u\id.west);}
\foreach \id in {04,05,06} {\draw[draw=ink] (participant.west)--(u\id.east);}
\draw[draw=ink] (finder.east)--(u08.west);
\draw[draw=ink] (public.west)--(u09.east);
\draw[draw=ink] (staff.west)--(u10.east);
\end{tikzpicture}
\caption{Use case view. Textual actor symbols identify the external roles; UC-09 includes owner management and public scanning.}
\end{figure}
''')
usecases=[
('UC-01','Reporter','Register with unique email or authenticate; create a session and enter the report/dashboard flow. Invalid credentials or password validation failure produces an error.'),('UC-02','Reporter','Complete all report stages, review and publish. Revalidate every field, write the report/event, calculate matches and remove the draft. An owner can edit only Open, unreserved reports.'),('UC-03','Reporter','Submit a valid stage, leave and resume saved data. Explicit confirmation is required when discarding a draft through the normal new-report workflow.'),('UC-04','Match participant','Open a permitted match; compare both public summaries and factor points. Private answers remain hidden; a score is not proof of ownership.'),('UC-05','Match participant','Propose a future meeting; reserve both reports; let the other participant accept. Either may dismiss a possible/proposed match; only the dismisser may restore an eligible pair.'),('UC-06','Match participant','At or after the scheduled time, record return. Update both reports, release reservations, reject competing possible matches and write events.'),('UC-07','Reporter','Browse own report summaries, search title/place, filter kind/status and paginate history. Removed records are absent from ordinary lists.'),('UC-08','Signed-in report QR finder','Open a UUID link, seed/reuse a Found draft with limited public hints, then independently complete the report. Self-use redirects; closed/reserved sources show a notice.'),('UC-09','Owner / public label finder','Owner creates/downloads/deactivates/reactivates a label. A bearer URL shows the chosen phone only while the label is active; an unknown token is not found.'),('UC-10','Moderator','Inspect the staff list and close/remove an Open unreserved report. Reject related possible matches and record the staff action; deny nonstaff access.')]
table(['ID / actor','Brief use case description'],[(i+' / '+a,b) for i,a,b in usecases],[.26,.74])
para('These brief descriptions follow the supplied format; detailed step-by-step test procedures belong in a separate test plan. Administrator account management is a supporting framework function, outside UC-01 to UC-10.')
heading('subsection','Report and Handover State Models')
raw(r'''
\begin{figure}[H]\centering

\begin{tikzpicture}
\node[box,text width=3cm] (open) at (-2,2) {Open\\reserved = false};
\node[box,text width=3cm] (reserved) at (3,2) {Open\\reserved = true};
\node[box,text width=2.8cm] (closed) at (-4,-1) {Closed};
\node[box,text width=2.8cm] (removed) at (0,-1) {Removed};
\node[box,text width=2.8cm] (returned) at (4,-1) {Returned};
\draw[arr] (open) to[bend left=18] node[lab,above]{proposal}(reserved);
\draw[arr] (reserved) to[bend left=18] node[lab,below]{dismiss proposal}(open);
\draw[arr] (open)--node[lab,left,pos=.65]{staff close}(closed);
\draw[arr] (open)--node[lab,right,pos=.75]{staff remove}(removed);
\draw[arr] (reserved)--node[lab,right]{record return}(returned);
\end{tikzpicture}
\caption{Report status and reservation. Reserved is a separate Boolean, not a report status.}
\end{figure}
\begin{figure}[H]\centering
\begin{tikzpicture}[node distance=1.0cm and 1.1cm]
\node[box] (possible) {Possible Match};
\node[box,right=2.4cm of possible] (proposed) {Handover Proposed};
\node[box,below=2.5cm of proposed] (scheduled) {Handover Scheduled};
\node[box,left=2.4cm of scheduled] (rejected) {Rejected};
\node[box,below=1.2cm of scheduled] (returned) {Returned};
\draw[arr] (possible)--node[lab,above]{propose}(proposed);
\draw[arr] (proposed)--node[lab,right]{other participant\\accepts}(scheduled);
\draw[arr] (scheduled)--node[lab,right]{at/after meeting\\record return}(returned);
\draw[arr] (possible.south) -- node[lab,right]{dismiss}(rejected.north);
\draw[arr] (rejected.west) to[bend left=50] node[lab,left]{restore\\if eligible}(possible.west);
\draw[arr] (proposed.south west)--node[lab,above,sloped,pos=.35]{dismiss}(rejected.north east);
\end{tikzpicture}
\caption{Match lifecycle. Staff closure/removal and competing return also reject related Possible Match records.}
\end{figure}
''')
table(['Action','Guards and effects'],[
('Propose','Participant; Possible Match; both reports Open and unreserved; valid future meeting. Sets both reserved, records proposer/place/time and proposed state.'),('Accept','Other participant; Handover Proposed; meeting remains in future; reports Open. Sets scheduled state; reveals contacts.'),('Dismiss','Either participant; Possible Match or Handover Proposed; reports Open. Sets Rejected and rejected_by. A dismissed proposal releases both reservations.'),('Restore','Only rejected_by; reports Open and unreserved; current score still qualifies. Sets Possible Match and refreshes scores; clears rejected_by.'),('Return','Either participant; Handover Scheduled; meeting time reached; reports Open. Sets both Returned, clears reservations and rejects competing Possible Match records.'),('Close / remove','Staff only; report Open and unreserved. Sets Closed/Removed, rejects related possible matches and records an event.')],[.19,.81])
heading('subsection','Publication Interaction Model')
raw(r'''
\begin{figure}[H]\centering
\begin{tikzpicture}[x=1cm,y=1cm]
\foreach \x/\n/\t in {0/u/Reporter,3.4/v/Wizard view,7/s/Publish service,11/d/Database}
{\node[box,text width=2.5cm] (\n) at (\x,0) {\t};\draw[dashed,gray] (\x,-.55)--(\x,-7.1);}
\draw[arr] (0,-1)--node[lab,above]{submit Review}(3.4,-1);
\draw[arr] (3.4,-1.8)--node[lab,above]{publish(draft, user)}(7,-1.8);
\draw[arr] (7,-2.6)--node[lab,above]{lock; fetch owned draft}(11,-2.6);
\node[lab] at (7,-3.25) {revalidate all forms};
\draw[arr] (7,-3.9)--node[lab,above]{save report + event}(11,-3.9);
\draw[arr] (7,-4.7)--node[lab,above]{score candidates; save matches}(11,-4.7);
\draw[arr] (7,-5.5)--node[lab,above]{delete draft; commit}(11,-5.5);
\draw[arr,dashed] (7,-6.25)--node[lab,above]{saved report}(3.4,-6.25);
\draw[arr,dashed] (3.4,-6.95)--node[lab,above]{dashboard + result notice}(0,-6.95);
\end{tikzpicture}
\caption{Successful publication. Validation failure returns an error; transactional database changes do not partially commit.}
\end{figure}
''')
heading('subsection','Business Rules and Matching Calculation')
table(['ID','Rule'],[
('BR-01','A report, match or QR scan is a lead only. Only a valid participant return action sets the matched reports to Returned.'),('BR-02','The five score factors total at most 100. Threshold 70 and at least two meaningful private agreements are both mandatory.'),('BR-03','Scoring accepts only Lost-to-Found, same-category, Open reports from different owners. Candidate retrieval excludes reserved reports.'),('BR-04','A proposed or scheduled handover reserves both reports and blocks editing, moderation and competing proposals.'),('BR-05','The report remains Open while reserved. Closed, Removed and Returned reports cannot receive normal editing or handover actions.'),('BR-06','Report contacts become visible to participants after acceptance and stay visible after return. Active personal labels separately publish their chosen phone.'),('BR-07','Recalculation deletes existing Possible Match rows involving the edited/published report before rebuilding suggestions. Existing rejected/proposed/scheduled pair states are not reset to Possible Match.'),('BR-08','Event entries are created for report creation/update, match transitions and moderation. Match score generation itself is not a separately logged Event.')],[.15,.85])
table(['Factor','Maximum','Calculation'],[
('Category','20','Exact category equality; otherwise the pair is ineligible.'),('Location','20','Haversine distance: below 0.5 km = 20; below 1 km = 15; below 2 km = 10; below 5 km = 5; otherwise 0. Missing coordinates give 0.'),('Date','15','Absolute event-date difference: 0 days = 15; 1 day = 10; 2-3 days = 5; otherwise 0.'),('Description','15','Casefold text; extract [a-z0-9] tokens of length at least 3; remove configured stop words. Round 15 times intersection size / union size. Empty union gives 0.'),('Private','30','Normalize ordinary values by stripping and casefolding. Count agreements over the union of evidence keys plus bank-card pairs. Round 30 times agreements / evidence total. Empty total gives 0.')],[.19,.14,.67])
para('Private evidence excludes contents, bank_count and logo selectors, all bank_* keys from ordinary key comparisons, and values None, empty string, "None", "Other", "Not provided", empty list and "No". Conditional logo_name and other filled descriptive fields can contribute. Bank-card entries are compared as a set of (issuer or custom service, complete number stored in *_suffix) pairs, independent of entry order. Each identical pair contributes one agreement. Ordinary matching fields include generic colour/type as well as more distinctive details; two agreements do not establish ownership.')
para('Description stop words are: the, and, with, from, near, was, for, this, that, have, item, lost, found. Python round is used for fractional description/private scores. At exactly 0.5, 1, 2 or 5 km the lower distance band no longer applies. A hypothetical pair with 20 category + 10 location + 10 date + 10 description + 20 private = 70 qualifies only if at least two private agreements also exist.')

heading('chapter','Other Non-functional Requirements')
heading('section','Performance Requirements')
para('The following five measurable targets are Proposed. They complete the performance specification requested by the course template; they are not measured achievements. Reference workload: 1,000 Open reports, 10 concurrent authenticated users, 2-vCPU/4-GiB server with SSD, PostgreSQL, warm cache and same-region client network. Measure p95 over at least 100 operations after warm-up. Exclude external map-tile latency; include database and server work. Record hardware and test data when approving the targets.')
for row in [
('NFR-PER-01','Ordinary dashboard, history and detail page loads shall complete within 2 seconds at p95.','Measure browser navigation through load completion under the reference workload.'),('NFR-PER-02','Report publication including candidate matching shall complete within 5 seconds at p95.','Measure submit-to-redirect completion for representative reports, including the largest same-category candidate set.'),('NFR-PER-03','Valid wizard-step submissions without a photo shall complete within 1 second at p95.','Measure POST-to-next-step response; confirm data has persisted before the next step is shown.'),('NFR-PER-04','Photo validation and normalization at the allowed 5-MiB/24-megapixel boundary shall finish within 3 seconds at p95 after upload receipt.','Time decode, normalize and private-storage write for valid boundary images; exclude client upload transfer.'),('NFR-PER-05','Personal-label creation including QR generation shall finish within 2 seconds at p95.','Measure successful POST through persisted label and available image with 10 concurrent users.')]:req(row[0],'Proposed: '+row[1],row[2],'Medium')
heading('section','Safety and Security Requirements')
heading('subsection','Safety and Trust')
for row in [
('SAFE-01','Match and QR interfaces shall explain that the application does not establish ownership or guarantee recovery.','Match/report QR screens display the limitation; no automatic ownership claim is made.'),('SAFE-02','The handover form shall guide users to choose a public, safe meeting place.','Meeting-place help contains the guidance. This is advice; the system does not assess the safety of a location.'),('SAFE-03','The system shall prevent return confirmation before the scheduled time and prevent overlapping active handovers for a report.','Early return and competing proposals are refused without changing report state.')]:req(*row)
heading('subsection','Security and Privacy')
secrows=[
('NFR-SEC-01','Restricted application pages shall require a valid authenticated session.','Anonymous requests redirect to login or return no protected content.'),('NFR-SEC-02','Authorization shall be checked against the object owner, match participation or staff role.','Cross-account report/draft/match/media access is denied. Staff permission alone does not grant photo or private-answer access.'),('NFR-SEC-03','State-changing POST forms shall use CSRF protection.','Missing/invalid tokens reject POST submission. GET draft mutations remain a known gap in Chapter 5.'),('NFR-SEC-04','The server shall revalidate current state and reservation at action time.','A stale form cannot edit, moderate or propose against an ineligible report.'),('NFR-SEC-05','Other users and staff management pages shall not receive raw private answers.','Inspect report/match/management responses for absence of the other owner\'s answers. This is application access control, not encryption against database administrators.'),('NFR-SEC-06','Production secrets shall be supplied through protected deployment configuration.','Production configuration rejects missing/weak required settings; a separate release review checks distributable files for secrets.'),('NFR-SEC-07','Proposed deployment gate: approve collection, minimization, retention and deletion rules for private identifiers, photos and contact data.','A documented policy identifies permitted fields, retention periods, access roles and deletion procedures before public use.'),('NFR-SEC-08','Report photos, draft photos and personal-label images shall use authorization-aware responses with private, no-store caching.','Authorized media includes required headers; unrelated users receive no image bytes. Public report QR PNGs are a separate non-photo endpoint.')]
for row in secrows:req(*row)
table(['Security rule','Specification / acceptance reference'],[
('SEC-01','Object scope is defined by NFR-SEC-02 and the disclosure matrix in Chapter 5.'),('SEC-02','Both saved report contacts remain hidden until the other participant accepts; compare responses before and after acceptance (FR-HND-05/06).'),('SEC-03','Report QR hints omit the source phone, private answers, exact coordinates and location description (FR-QR-02/03).'),('SEC-04','Label token_hash is a digest; inactive labels omit the phone. The QR image contains the bearer URL (FR-QR-06/08).'),('SEC-05','Decode and re-encode photos, remove source metadata, enforce size/type/dimensions and restrict access; no photo similarity analysis (FR-PHO).'),('SEC-06','Public deployment shall use HTTPS, secure cookies, explicit hosts, protected secrets and production headers. Verify against config/production.py and actual deployment.'),('SEC-07','Trust notices shall communicate application limits (SAFE-01/02).'),('SEC-08','Apply configured identifier and invisible-character filters to public text (FR-VAL-01/02). These pattern filters are not a complete personal-data detector.')],[.19,.81])
para('Some private forms request complete 13-digit CNIC and 16-digit card numbers despite keys named suffix. These values are stored in JSON without additional field encryption. Password-style inputs mask rendering but do not change storage. This fact must remain explicit in the specification and any decision about public deployment.')
heading('section','Software Quality Attributes')
nfrgroups=[('Reliability and Data Integrity',[
('NFR-REL-01','Publishing, recalculating matches, moderation and handover transitions shall commit database changes atomically.','An induced database failure shall leave no partial workflow state. Filesystem writes are not claimed to share the database transaction.'),('NFR-REL-02','At most one active handover shall reserve a report.','Concurrent proposal scenarios shall produce one reservation winner and rejection of a competing proposal.'),('NFR-REL-03','A Lost/Found pair shall be unique and match score shall not exceed 100.','Database unique_pair and score_maximum constraints reject invalid inserts.'),('NFR-REL-04','Schema changes shall use versioned migrations.','Clean installation and upgrade shall reach migrations 0001-0006 without manual schema edits.')]),('Usability and Accessibility',[
('NFR-USE-01','Proposed: at least 8 of 10 first-time participants shall publish a valid report without assistance, with median completion within 5 minutes.','Observe a defined representative task and report success rate and median elapsed time.'),('NFR-USE-02','Core form fields shall have labels and validation errors that indicate corrective action.','Inspect account, wizard, meeting and label forms for labels and actionable errors.'),('NFR-USE-03','Users shall be able to enter place text and coordinates when external map tiles are unavailable.','Complete Location with manual fields while tile requests fail.'),('NFR-ACC-01','Proposed: core flows shall satisfy WCAG 2.2 AA requirements for keyboard use, focus, labels, contrast and error identification.','A documented manual and automated accessibility audit records conformance and remaining failures.')]),('Compatibility and Localization',[
('NFR-COMP-01','Proposed: core workflows shall work in current and previous major Chrome, Edge, Firefox and Safari, with defined desktop/mobile versions.','Execute an approved browser matrix. The Appendix C observation covers Chrome only.'),('NFR-LOC-01','Dates and meetings shall use Asia/Karachi for interpretation and display; persistent datetime values shall be timezone aware.','Save a meeting and compare its displayed Pakistan time with the stored instant.')]),('Maintainability and Testability',[
('NFR-MNT-01','Matching, transitions and moderation shall remain callable independently of template rendering.','Service functions can be exercised with model fixtures without opening a browser.'),('NFR-MNT-02','All baseline functional requirements shall have mapped acceptance scenarios before release approval.','Appendix B maps every FR family; a release test record shall add individual results and evidence.')]),('Availability and Recoverability',[
('NFR-OPS-01','Proposed: production database and private-media backups shall run daily, retain 14 daily recovery points and be restored in a quarterly exercise with recovery-point loss at most 24 hours.','Restore database and referenced files together and record recovery evidence.'),('NFR-OPS-02','Proposed: public service availability shall be at least 99.5% per calendar month, excluding announced maintenance.','Use timestamped availability monitoring over the complete month.')])]
for title,rows in nfrgroups:
    heading('subsection',title)
    for row in rows:req(*row,priority='Medium' if not row[0].startswith('NFR-REL') else 'High')
para('Correctness, privacy and workflow integrity take priority over convenience and performance. Database schema, matching rules and views are separate modules to support changes. New questionnaire fields require corresponding validation, scoring, privacy and data-dictionary updates rather than a UI-only change.')

heading('chapter','Other Requirements')
heading('section','Database Tables and Relationships')
para('The six application tables are core_user, core_report, core_draft, core_match, core_event and core_qrlabel. Django additionally maintains authentication, permission, session, content-type, administration-log and migration tables. The application field dictionary appears in Appendix A. JSON is used for category-varying answers and draft data; it is not a separate relational table.')
raw(r'''
\begin{figure}[H]\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  entity/.style={draw=ink,rounded corners=4pt,fill=pale,align=center,
    text width=2.7cm,minimum height=1.1cm,inner sep=5pt,font=\small},
  relation/.style={-{Stealth[length=2mm]},draw=ink,line width=.6pt},
  relabel/.style={font=\footnotesize,fill=white,inner sep=2pt,align=center}]
\node[entity] (user) at (0,2) {User\\PK: id; unique email};
\node[entity] (report) at (5,2) {Report\\PK: id; FK: owner};
\node[entity] (match) at (11,2) {Match\\FK: lost, found};
\node[entity] (label) at (0,-2) {QRLabel\\FK: owner; token hash};
\node[entity] (draft) at (5,-2) {Draft\\FK: owner; optional report};
\node[entity] (event) at (11,-2) {Event\\FK: report, actor};
\draw[relation] (user.east)--node[relabel,above]{owns}(report.west);
\draw[relation] (report.east)--node[relabel,above]{one Lost + one Found}(match.west);
\draw[relation] (user.south)--node[relabel,left]{owns}(label.north);
\draw[relation] (report.south)--node[relabel,right]{optional source}(draft.north);
\draw[relation] (report.south east) to[out=-35,in=145] node[relabel,sloped,above,pos=.55]{has events} (event.north west);
\node[font=\footnotesize,align=center,text width=13cm] at (5,-3.55)
  {Each box lists its key links. Draft.owner and Event.actor reference User; Match.proposer and Match.rejected\_by also reference User.};
\end{tikzpicture}
\caption{Application entities and their principal relationships.}
\end{figure}
''')
bullets(['Every report has one protected owner. Match.lost, Match.found, Match.proposer, Match.rejected_by and Event references use PROTECT deletion behavior.','Draft and QRLabel owner links use CASCADE; Draft.report is nullable and cascades if its source report is deleted. Normal moderation sets status rather than physically deleting reports.','Match(lost, found) is unique; score is a positive small integer constrained to at most 100. Report.public_id and QRLabel.token_hash are unique.','Only kind has model choices on Report. Status and state are string fields controlled by service logic; no additional database state-enumeration or one-active-handover constraint is declared.','The service locks an owner row to avoid duplicate creation of a new draft in normal concurrent requests. Historical duplicates can still exist; the newest matching draft is resumed.','Framework tables include core_user_groups, core_user_user_permissions, auth_group, auth_permission, auth_group_permissions, django_session, django_content_type, django_admin_log and django_migrations.'])
heading('section','Data Disclosure and Retention')
table(['Data','Permitted application visibility'],[
('Owned report and draft','Owner. Match views reveal the paired report\'s public summary; the standalone report detail route stays owner-only.'),('Private answers','Owner during authorized draft entry/editing; server for scoring. Absent from the opposite participant\'s output and staff management. Administrators with database access are outside this UI protection.'),('Report contact phone','Owner during Details entry; both match participants after the other party accepts (scheduled/returned states). Not exposed by the report QR seed.'),('Report photo','Owner and owner of the opposite report in any existing match involving it. The current photo query does not exclude Rejected matches.'),('Draft photo','Draft owner only.'),('Report QR PNG','Public to anyone holding the UUID URL; contains only the entry URL. Following it requires authentication before seeding a draft.'),('Personal QR image','Owner only. It encodes a bearer URL; a shared printed image grants scan capability.'),('Personal-label phone','Anyone with the bearer URL while active. Suppressed when expired/revoked; no login is required for public scanning.'),('Activity event','Stored actor, text and time. Owner report UI shows text/time; management actions are attributable in the database.')],[.26,.74])
para('There is no automatic retention schedule, user deletion/export workflow or account recovery workflow in this baseline. Label expiry disables public contact display; it does not delete the label record or image. Removing a report is a status change and is not erasure. These distinctions must be considered when defining production retention policy.')
heading('section','Known Limitations and Open Decisions')
table(['ID','Observed behavior / decision'],[
('OI-01','Private questionnaires store complete CNIC/card values without field encryption. Decide whether these fields are necessary and define minimization, retention and deletion before public deployment.'),('OI-02','Approve reference hardware, quality thresholds and operational targets before treating Proposed requirements as release gates.'),('GAP-01','The private-identifier validation hint incorrectly says the matched party sees private answers; templates actually suppress them. UI wording should be aligned to the privacy model.'),('GAP-02','New-report and report-QR GET routes can create or modify a draft. CSRF guarantees in this document apply to POST forms; moving draft mutations behind confirmed POST requests is a follow-up change.'),('GAP-03','Report QR entry reuses the newest draft, overwrites seeded fields and clears several values without the normal discard confirmation. An existing draft photo is not cleared by this route. Add an explicit choice to avoid accidental reuse.'),('GAP-04','Report UUID endpoints do not restrict source kind to Lost. The normal UI exposes the feature only for Lost reports; server-side kind enforcement is a follow-up.'),('GAP-05','Scheduled handovers have no cancel/reschedule/expiry transition. Decide the desired policy before adding a transition or claiming timeout recovery.'),('GAP-06','Photo access persists for a participant linked by a Rejected match. Decide whether rejected participation should continue to authorize photo viewing.'),('GAP-07','Identifier PasswordInput fields are not repopulated on edit. Saved values remain in the draft, but resubmitting Matching may require re-entry.')],[.15,.85])
para('These observations document the inspected implementation and prevent the SRS from claiming unsupported behavior. They are not application changes made as part of this document task. Proposed future scope may include password reset, profile editing, notifications and in-app guidance; no such feature is included in the functional baseline here.')
heading('section','Acceptance and Change Control')
para('Acceptance begins with approved scope and requirement IDs, followed by the scenario families in Appendix B. A result record should identify build, database engine, browser, fixture, expected outcome, actual outcome and evidence. Performance, usability, accessibility and operational requirements need their own measurements. Localhost screenshots alone cannot establish those qualities.')
para('When behavior changes, update the affected FR/BR entries, use case/state diagrams, dictionary fields and traceability rows together. Changes to collection of identifiers, contact release or media visibility require an explicit privacy review. The project team maintains the revision history and supplies cover details before academic submission.')

raw(r'\appendix\renewcommand{\chaptername}{Appendix}')
heading('chapter','Data Dictionary')
para('Types and limits below describe the current Django models and forms. Form limits can be stricter than database column sizes. PKs are auto-generated big integers. FK names are shown as Python attributes; database columns add _id. Unless explicitly nullable, fields are required at the model level. Empty strings and optional file values are distinct from SQL NULL.')
entities=[
('User / core_user','FR-ACC; FR-HIS; FR-MOD',[
('id','BigAutoField / PK','Account identity referenced by owned data and actions.'),('username','Char(254), unique','Stores normalized email as the login username.'),('email','Email field (254), unique','Registration lowercases and checks duplicates case-insensitively.'),('password','Char(128)','Framework password hash; no plaintext password field.'),('first_name / last_name','Char(150) each','Registration uses first_name for the full name. last_name is inherited and not collected by registration.'),('is_active / is_staff / is_superuser','Boolean','Account usability, management permission and framework administrator permission.'),('last_login','Datetime, nullable','Framework login timestamp.'),('date_joined','Datetime','Framework account creation time.'),('groups / user_permissions','Many-to-many links','Django permission assignments through join tables.')]),
('Report / core_report','FR-REP; FR-VAL; FR-PHO; FR-MAT; FR-HND',[
('id','BigAutoField / PK','Source for display_id: LFD- or FND- plus at least three digits.'),('public_id','UUID, unique/indexed','Generated UUID for report QR routes; independent of display_id.'),('owner','FK User / PROTECT','The reporter who controls standalone report access and editing.'),('kind','Char(5), choices','Lost or Found.'),('title','Char(120)','Required readable item title; public_short screening.'),('category','Char(40)','One of eight CATEGORIES values validated by the form.'),('description','Text; form max 2,000','Required public description; extended identifier screening.'),('location','Char(100)','Required readable place; public_short screening.'),('lat / lng','Decimal(10,8) / Decimal(11,8), nullable','Legacy/model NULL permitted; new publication requires both. Valid ranges -90..90 and -180..180.'),('location_detail','Char(255)','Required location description; public_short screening.'),('event_date','Date','1 January 2000 through current local date.'),('contact','Char(120); form exactly 11','Phone must match 0 followed by 10 ASCII digits.'),('answers','JSON, default empty object','Category-specific private fields described below.'),('photo','Image path, optional','Private normalized JPEG; upload path report_photos/ or carried draft photo path.'),('status','Char(10), default Open','Service states Open, Closed, Removed, Returned.'),('reserved','Boolean, default false','True during proposed/scheduled handover; separate from status.'),('created_at','Datetime, auto on create','Report creation time; editing does not change this field.')]),
('Draft / core_draft','FR-REP-05 to 12; FR-QR-02',[
('id / owner','PK / FK User CASCADE','Owner-authorized draft identity.'),('report','Nullable FK Report CASCADE','Existing report being edited; NULL for a new report.'),('data','JSON, default empty object','Saved report fields; event_date stored as ISO YYYY-MM-DD and coordinates as decimal strings. answers is nested; remove_photo is a Boolean flag when selected.'),('photo','Image path, optional','Normalized upload under draft_photos/; may become a report photo on publication.'),('updated_at','Datetime, auto on save','Used to choose the newest draft and display saved time.')]),
('Match / core_match','FR-MAT; FR-HND; BR-02 to 07',[
('id','BigAutoField / PK','Internal match-route identifier.'),('lost / found','FK Report / PROTECT','Exactly one report per role; unique combined pair.'),('score','Positive small integer','Total similarity; database check at most 100. New qualifying scores are at least 70.'),('breakdown','JSON, default empty object','Integer factors named Category, Location, Date, Description and Private.'),('state','Char(24), default Possible Match','Possible Match, Handover Proposed, Handover Scheduled, Rejected or Returned.'),('proposer','Nullable FK User / PROTECT','Participant who created the current/last proposal.'),('rejected_by','Nullable FK User / PROTECT','Participant who dismissed; required for user restoration authority. Automated rejection may leave this unset.'),('meeting_place','Char(255), blank permitted','Required readable text when proposing; words validator.'),('meeting_at','Nullable timezone-aware datetime','Required future time on proposal/acceptance; return allowed at or after this instant.')]),
('Event / core_event','FR-HIS-05; FR-MOD-04',[
('id','BigAutoField / PK','Event identity.'),('report / actor','FK Report / FK User, both PROTECT','Affected report and account performing the action.'),('text','Char(255)','Report created, Report updated, a match state, or Closed/Removed by management.'),('created_at','Datetime, auto on create','Attributable action time. Events are ordered by descending time in report detail.')]),
('QRLabel / core_qrlabel','FR-QR-05 to 09,11; SEC-04',[
('id / owner','PK / FK User CASCADE','Owner-managed personal label.'),('item_name','Char(80)','Readable item name, public_short screening.'),('contact_phone','Char(11)','Exactly 11 digits starting with 0; deliberately public while active.'),('token_hash','Char(64), unique','SHA-256 hex digest of a token_urlsafe(32) token.'),('qr_image','File path','PNG under private_qr_labels/ encoding the bearer URL.'),('expires_at','Datetime','Creation/reactivation time plus six calendar months, with day clamped if necessary.'),('revoked','Boolean, default false','Manual deactivation switch.'),('created_at','Datetime, auto on create','Creation time; default ordering newest first.'),('is_active','Derived Boolean, not a column','True exactly when revoked is false and expires_at is later than now.')])]
for title,related,rows in entities:
    heading('section',title);para('Related requirements: '+related+'.')
    table(['Field','Type / constraint','Meaning'],rows,[.24,.28,.48])
heading('section','Private Answer Schemas')
para('All categories ask colour. All applicable ChoiceFields are required except contents, which can be empty. Private free text is limited to 80 characters and must contain letters and no configured invisible/control characters. Conditional fields are generated from selections. Password-style numeric fields are strings of exact length, not numeric database columns.')
table(['Category','Answer keys and dependencies'],[
('Wallet / Purse','colour, material, logo, contents, mark. If logo=Yes: logo_name. If contents includes CNIC: cnic_suffix (13 digits). If Bank cards: bank_count 1-5 and bank_i_issuer, bank_i_suffix (16 digits), plus bank_i_other when issuer=Other. If Cash: cash_range and cash_notes. If Driving licence: licence_issuer. If Other items: other_contents.'),('Cards / IDs','colour, card_type, issuer, suffix, mark; issuer_other if issuer=Other. card_type is CNIC, NED Student Card or Bank Card. suffix is respectively 13, 4 or 16 digits.'),('Keys','colour, count, kind, fob, mark. count: 1,2,3,4,5+; kind: Home,Car,Bike,Locker,Other; fob: None,Plastic,Fabric,Metal.'),('Electronics','colour, kind, case, brand, mark. kind: Phone,Laptop,Tablet,Earbuds,Charger,Other; case: None,Hard,Soft,Sleeve; brand: free text.'),('Bag','colour, kind, material, pockets, mark. kind: Backpack,Handbag,Laptop bag,Tote,Other; material: Fabric,Leather,Canvas,Synthetic; pockets: 1,2,3,4+.'),('Documents','colour, kind, holder, issuer, mark. kind: Notebook,Assignment,Certificate,Folder,Other; holder: None,Folder,Envelope; issuer: free text.'),('Cash / Money','colour, amount, notes, mark. amount and notes use the cash ranges and denomination choices below.'),('Other','colour and mark using generic choices.')],[.23,.77])
table(['Shared choice set','Values'],[
('COLOURS','Black; Brown; Blue; Red; Green; Grey; White; Silver; Other.'),('CONTENTS','CNIC; Bank cards; Cash; Driving licence; Other items. Multiple selections allowed.'),('BANK_SERVICES','HBL; MCB; UBL; Meezan Bank; National Bank of Pakistan; Bank Alfalah; Allied Bank; NayaPay; SadaPay; JazzCash; Easypaisa; Other.'),('DEPARTMENTS','Computer and Information Systems Engineering (CIS); Computer Science & Information Technology (CSIT); Civil Engineering; Mathematics; Physics; Chemistry; Metallurgical Engineering; Other.'),('Wallet choices','material: Leather,Fabric,Synthetic,Other. logo: Yes,No. mark: None,Scratch,Sticker,Tear,Initials.'),('Card choices','CNIC issuer: NADRA,Other. NED Student Card issuer: DEPARTMENTS. Bank Card issuer: BANK_SERVICES. mark: None,Scratch,Sticker,Crack.'),('Generic mark','None; Scratch; Sticker; Tear; Other.'),('Cash range / amount','Below Rs. 500; Rs. 500 to 1,999; Rs. 2,000 to 4,999; Rs. 5,000+.'),('Cash notes','Rs. 100; Rs. 500; Rs. 1,000; Mixed notes.')],[.27,.73])
heading('section','Constants, State Variables, Inputs and Outputs')
table(['Name / variable','Allowed value or role','Requirement / operation'],[
('CATEGORIES','Wallet / Purse; Cards / IDs; Keys; Electronics; Bag; Documents; Cash / Money; Other.','FR-REP-04 / Type and Matching'),('step','Integer clamped 1-5; invalid input falls back to 1. Missing preceding data redirects earlier.','UI-02 / wizard'),('kind / status / state / reserved','Enumerations and Boolean listed in Report/Match tables above.','BR-04/05 / transitions'),('action','Wizard: refresh or new (with confirmation); match: propose, accept, reject, restore, returned; moderation: close, remove.','FR-REP; FR-HND; FR-MOD'),('confirm_discard / discard_draft_id','yes and the current draft ID are required for normal discard-and-new.','FR-REP-07'),('q / kind / status / page','History query, filters and pagination input. Unsupported filters are ignored; paginator normalizes missing/invalid pages.','FR-HIS-02/03/06'),('Page size / dashboard limits','History 10 per page; dashboard at most 3 Open and 10 Returned reports.','FR-HIS-01/03'),('Score weights / gates','20,20,15,15,30; minimum total 70; minimum agreements 2; distance radius 6,371 km for haversine.','FR-MAT-02 to 04'),('Distance/date bands','Distance below 0.5,1,2,5 km; date difference 0,1,2-3,more than 3 days.','BR-02 / score'),('Photo boundaries','5*1024*1024 bytes; 6,000 pixels/edge; 24,000,000 total pixels; output MAX_EDGE=1,800; JPEG quality=86.','FR-PHO-01 to 03'),('ACTIVE_MONTHS','6 calendar months from create/reactivate, not a fixed 180-day duration.','FR-QR-05/09'),('BAD_CHARS','C0 controls except tab/newline/CR; U+007F-009F; U+200B-200F; U+202A-202E; U+2060-206F; U+FEFF.','FR-VAL-02 / public text'),('Public identifier rules','Short fields reject @ and configured digit patterns; description adds email, obfuscated email, roll number and named identifier patterns.','FR-VAL-01 / forms.py'),('Phone / event-date input','0[0-9]{10}; date DD-MM-YYYY between 2000-01-01 and today.','FR-REP-02; FR-VAL-04'),('Meeting input','Place at most 255; exact DD-MM-YY hh:mm AM/PM in Pakistan time, future on proposal.','FR-HND-01'),('public_id / token / download','UUID report lookup; bearer token label lookup via digest; download=1 requests attachment.','FR-QR'),('contacts / can_restore','Derived by match state and rejected_by respectively; not stored columns.','FR-HND-04 to 06'),('display_id / visible_report_count','Derived report code; user count excluding Removed reports.','FR-REP-13; FR-HIS'),('Outputs','HTML pages/errors/redirects; protected JPEG photos; PNG QR images; database records; activity entries; match score breakdowns.','UI-01 to 07; FR-PHO; FR-QR; FR-HIS')],[.27,.40,.33])
para('Raw personal-label tokens are generated from 32 random bytes. The report/draft JSON can contain identifiers regardless of the name suffix. The functional validation rules, not just database column widths, define acceptable user input.')

heading('chapter','Traceability and Acceptance')
heading('section','Functional Coverage Matrix')
para('Each FR range below is inclusive and covers every functional requirement in this document. AT entries are acceptance scenario families, not claims of executed tests. Individual cases should split compound criteria into positive, negative and boundary examples.')
coverage=[
('FR-ACC-01 to 06','UR-01 / UC-01 / AT-01','forms.Registration, EmailLogin; views.register, AccountLoginView; settings middleware; auth.html.'),('FR-REP-01 to 13','UR-02/03 / UC-02/03 / AT-02','forms.TypeForm, DetailsForm, LocationForm, MatchingForm; views.wizard, edit_report; services.publish, get_or_create_draft; wizard.html.'),('FR-VAL-01 to 06','UR-02 / UC-02 / AT-02','forms.words/public_short/public_text and date/coordinate validators; escaped Django templates.'),('FR-PHO-01 to 04','UR-02 / UC-02 / AT-03','forms.DetailsForm.clean_photo; images.normalize_photo; views.report_photo/draft_photo.'),('FR-MAT-01 to 08','UR-04 / UC-04 / AT-04','services.score, location_score, recalculate; models.Match; templates/match.html.'),('FR-HND-01 to 09','UR-05/06 / UC-05/06 / AT-05','forms.MeetingForm; services.transition; views.match_detail; templates/match.html.'),('FR-HIS-01 to 06','UR-07 / UC-07 / AT-06','views.dashboard, report_history, report_detail; models.Event; dashboard/reports/report templates.'),('FR-QR-01 to 11','UR-08/09 / UC-08/09 / AT-07','views.report_found/report_qr_image and label views; qr.py; qr_labels.py; models.QRLabel.'),('FR-MOD-01 to 05','UR-10 / UC-10 / AT-06','views.management; services.moderate; management.html; admin.py restrictions.')]
table(['Requirement family','User / use case / acceptance','Implementation source (core/ unless noted)'],coverage,[.24,.27,.49])
heading('section','Acceptance Scenario Families')
atrows=[
('AT-01','Accounts and boundaries','Register valid/duplicate/case-variant email; invalid password; login/logout; remember-me; anonymous routes; wrong owner; nonstaff management; missing/invalid CSRF POST.'),('AT-02','Report lifecycle and validation','Save/resume all five stages; explicit discard; category change; masked identifier behavior; required field omission; date and coordinate boundaries; identifier/control-character samples; escaped markup; publish/re-edit locks; display ID and UUID separation.'),('AT-03','Image processing and access','Valid JPEG/PNG/WebP; exact and exceeding byte/pixel limits; corrupted file; decoded output/metadata/orientation; owner/participant/unrelated access; Rejected match visibility; draft isolation; response cache headers.'),('AT-04','Scoring and candidate selection','Same owner/wrong kind/category/closed/reserved candidates; 69/70 threshold; one/two private agreements; distance/date boundaries; empty descriptions; bank entry order; score factors; unique pair; absent raw private answers; trust notice.'),('AT-05','Handover state transitions','Propose valid/past/malformed meeting; self-accept blocked; other accepts; phone release; dismiss/restore authority; changed eligibility; concurrent proposals; reserved edit/moderation; early and valid return; competing suggestion rejection.'),('AT-06','History and moderation','Owner isolation; search title/location; kind/status combinations; eleven-record pagination; bad query; activity record actor/time; staff close/remove; reserved and closed refusal; Removed list exclusion.'),('AT-07','QR workflows','Signed-out/signed-in report entry; self/closed/reserved source; seeded-field exclusions; existing-draft overwrite; Lost/Found source behavior; label digest and owner image; active/expired/revoked scan; six-month/month-end reactivation.'),('AT-08','Proposed quality targets','After approval, run five performance measurements, first-time user study, responsive/keyboard/accessibility audit, browser matrix, monthly availability review and database/media restore exercise.'),('AT-09','Engineering and operations','Database rollback/concurrency/constraints; migration clean install/upgrade; deployment secrets/HTTPS/headers; timezone round trip; traceability completeness; approved sensitive-data policy and configured storage visibility.')]
table(['ID','Area','Required scenarios'],atrows,[.11,.22,.67])
heading('section','Nonfunctional and Model Coverage')
table(['Requirements / model','Scenario or review'],[
('UI-01 to 07; UI-08 Proposed','AT-01/02/05/06/07 for screens; AT-08 for responsive target.'),('BR-01 to 08','AT-02/04/05/06; inspect state and sequence models against service methods.'),('NFR-PER-01 to 05','AT-08: measured workload and p95 evidence after approval.'),('SAFE-01 to 03; SEC-01 to 08','AT-01/03/04/05/07/09: trust notices, protected data, workflow guards and deployment inspection.'),('NFR-SEC-01 to 08','AT-01/02/03/05/07/09: sessions, ownership, CSRF, state validation, privacy and policy.'),('NFR-REL-01 to 04','AT-04/05/09: rollback, concurrent proposals, pair/score constraints, migrations.'),('NFR-USE-01 to 03; NFR-ACC-01','AT-02/08: first-time study, labeled forms, tile outage, accessibility audit.'),('NFR-COMP-01; NFR-LOC-01','AT-08 browser matrix; AT-05/09 timezone round trip.'),('NFR-MNT-01 to 02','AT-09: services independent of views; no missing functional coverage.'),('NFR-OPS-01 to 02','AT-08/09: actual restore evidence and availability monitoring.'),('Data dictionary and entity model','Inspect models/forms/migrations; compare field sizes, nullability, keys, JSON schemas and deletion rules.'),('CPA-1 / CPA-2 / CPA-3','Chapters 1-2 identify resources/viewpoints; Chapter 3 resolves interacting privacy/workflow needs and maps user-to-system behavior; Chapter 5 and Appendix A specify data; LaTeX source provides the final communication artifact.')],[.37,.63])
para('Acceptance scenarios define planned checks; no test results or quality measurements are claimed here.')

heading('chapter','Localhost Interface Evidence')
para('The localhost screens were captured on 10 October 2026 in Chrome 154 using an isolated SQLite database and synthetic accounts/items.')
table(['Observation','Recorded outcome'],[
('Account and dashboard','Synthetic reporter signed in and reached the populated dashboard.'),('Report flow','Type, Details and Location saved successfully; the Matching stage loaded.'),('Match view','A synthetic pair showed its score and factors; contacts remained locked before acceptance.'),('QR labels','The authenticated label-management page loaded.')],[.27,.73])
para('Figures C.1-C.4 show current implementation screens with synthetic records.')
for filename,caption,note in [
('dashboard.png','Owner dashboard with active match and report summary.',''),
('location.png','Location stage of the report wizard.',''),
('matching.png','Category-specific private questions for a Keys report.',''),
('match.png','Possible Match review before handover acceptance.','')]:
    raw(r'\begin{figure}[H]\centering\includegraphics[width=.92\textwidth,height=.65\textheight,keepaspectratio]{'+filename+'}'+r'\caption{'+esc(caption)+r'}\end{figure}')

heading('chapter','Live Deployment Evidence')
para('The owner identified the site as their project and supplied its public URL. Registration, login and selected anonymous routes were inspected on 10 October 2026 using Chrome 154 over HTTPS.')
raw(r'\textbf{Registration:} \url{https://lost-and-found.54.252.227.103.sslip.io/register/}\par')
raw(r'\textbf{Login:} \url{https://lost-and-found.54.252.227.103.sslip.io/login/}\par')
heading('section','Observed Public Behavior')
table(['Live observation','Result / related requirement'],[
('Registration page','HTTP 200. Required Full name, Email, Password and Password confirmation inputs were present. Password guidance specifies at least eight characters, no commonly used password and no entirely numeric password. FR-ACC-01 / UI-01.'),('Login page','HTTP 200. Email, Password and optional Remember me controls were present. FR-ACC-02 / UI-01.'),('Protected entry points','Anonymous requests to /, /reports/, /labels/ and /management/ redirected to login with a next destination. FR-ACC-04 / NFR-SEC-01. This observes anonymous access protection, not all role-based permissions.'),('Trust and workflow copy','The page describes report, possible-match and handover workflows and states recovery is not guaranteed. SAFE-01 / SEC-07.'),('Application correspondence','Branding, forms and route behavior match the inspected project. This does not identify the deployed backend build.'),('Observation boundary','Only public GET requests were made. No live account or report was created; authenticated behavior and performance were not measured.')],[.27,.73])
heading('section','Observed Transport and Response Configuration')
table(['Property','Observed value'],[
('DNS address','54.252.227.103'),('TLS connection','TLS 1.3; certificate subject matched lost-and-found.54.252.227.103.sslip.io.'),('Reported server','nginx/1.28.3 (Ubuntu)'),('Strict-Transport-Security','max-age=3600; includeSubDomains'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Referrer-Policy','same-origin'),('CSRF cookie','Secure=true; SameSite=Lax. This was the anonymous csrf token cookie; authenticated session-cookie behavior was not inspected.')],[.37,.63])
para('Public observation confirms the account pages and HTTPS configuration shown here; authenticated workflows were not inspected live.')
for filename,caption,note in [
('live-register.png','Live public registration page, captured from the owner-supplied HTTPS deployment.','The published registration interface collects the four account fields specified by FR-ACC-01. No registration was submitted during this observation.'),
('live-login.png','Live public login page, captured from the owner-supplied HTTPS deployment.','The published login interface exposes email/password authentication and Remember me. The screenshot contains no account credentials.')]:
    raw(r'\begin{figure}[H]\centering\includegraphics[width=.92\textwidth,height=.65\textheight,keepaspectratio]{'+filename+'}'+r'\caption{'+esc(caption)+r'}\end{figure}')
raw(r'\clearpage\end{document}')

target=OUT/'SRS-Where-Is-My-Stuff.tex'
target.write_text('\n'.join(parts),encoding='utf-8')
print(f'Wrote {target} ({len(fr)} functional requirements).')
