#!/usr/bin/env python3
"""
style_suggester.py

Scans a Django project (built for "Where Is My Stuff?", a campus lost-and-found
app) for its templates and CSS, then writes out 5 distinct HTML/CSS styling
directions as standalone preview files you can open in a browser.

Usage:
    python3 style_suggester.py [path-to-project]

If no path is given, the current directory is scanned. If no Django
templates/CSS are found there, the script still generates the 5 previews
using the app's known screens (landing hero, recent matches, report list)
so you always get something to compare.

Output:
    style_suggestions/<theme-id>.html   -- 5 standalone previews
    style_suggestions/REPORT.md         -- scan summary + rationale per theme
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Project scan
# ---------------------------------------------------------------------------

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,6}\b")
FONT_RE = re.compile(r"font-family\s*:\s*([^;]+);", re.IGNORECASE)
CLASS_RE = re.compile(r'class="([^"]+)"')
UPPERCASE_RE = re.compile(r"text-transform\s*:\s*uppercase", re.IGNORECASE)


def scan_project(root: Path) -> dict:
    templates = sorted(root.glob("**/templates/**/*.html"))
    css_files = sorted(root.glob("**/static/**/*.css"))
    is_django = (root / "manage.py").exists()

    html_text = "\n".join(p.read_text(errors="ignore") for p in templates)
    css_text = "\n".join(p.read_text(errors="ignore") for p in css_files)
    all_text = html_text + "\n" + css_text

    return {
        "root": root,
        "is_django": is_django,
        "templates": templates,
        "css_files": css_files,
        "uses_bootstrap": "bootstrap" in all_text.lower(),
        "uses_tailwind": "tailwind" in all_text.lower(),
        "hex_colors": Counter(HEX_RE.findall(css_text)).most_common(6),
        "font_families": sorted(set(m.strip() for m in FONT_RE.findall(css_text))),
        "class_names": Counter(
            c for cls in CLASS_RE.findall(html_text) for c in cls.split()
        ).most_common(10),
        "has_uppercase_label": bool(UPPERCASE_RE.search(css_text)),
    }


def print_scan_summary(scan: dict) -> None:
    root = scan["root"]
    print(f"Scanned: {root.resolve()}")
    if not scan["templates"] and not scan["css_files"]:
        print("  No templates/ or static/*.css found at this path.")
        print("  Generating the 5 previews from the app's known screens instead.\n")
        return

    print(f"  Django project detected: {'yes' if scan['is_django'] else 'no (no manage.py found)'}")
    print(f"  Templates found: {len(scan['templates'])}")
    print(f"  CSS files found: {len(scan['css_files'])}")
    print(f"  Bootstrap referenced: {scan['uses_bootstrap']}")
    print(f"  Tailwind referenced: {scan['uses_tailwind']}")
    if scan["font_families"]:
        print(f"  Font families in use: {', '.join(scan['font_families'][:5])}")
    if scan["hex_colors"]:
        top_colors = ", ".join(c for c, _ in scan["hex_colors"])
        print(f"  Most common hex colors: {top_colors}")
    if scan["class_names"]:
        top_classes = ", ".join(c for c, _ in scan["class_names"][:8])
        print(f"  Most reused classes: {top_classes}")
    if scan["has_uppercase_label"]:
        print("  Note: found text-transform: uppercase still in the CSS"
              " (the wireframe feedback flagged an all-caps badge --"
              " none of the 5 directions below use it).")
    print()


# ---------------------------------------------------------------------------
# 2. Shared page content
# ---------------------------------------------------------------------------

COPY = {
    "site_name": "Where Is My Stuff?",
    "nav": ["My reports", "Report an item", "Log out"],
    "headline": "Left something behind on campus?",
    "subtext": (
        "Report it and we'll check it against everything already turned in "
        "\u2014 no long forms, no waiting on a bulletin board."
    ),
    "cta": "Report an item",
    "matches_heading": "Recent matches",
    "match": {
        "title": "Blue Hydro Flask",
        "detail": "Found near the Civil Engineering block",
        "confidence": "92% match",
    },
    "reports_heading": "Your reports (3)",
    "reports": [
        {"title": "Grey backpack", "status": "Matched", "status_class": "matched", "date": "Sep 21"},
        {"title": "Student ID card", "status": "Pending review", "status_class": "pending", "date": "Sep 18"},
        {"title": "Black umbrella", "status": "Open", "status_class": "open", "date": "Sep 12"},
    ],
    "footer": "NED University of Engineering & Technology \u2014 Lost & Found",
}


def page_shell(title: str, fonts_href: str, css: str, body_html: str) -> str:
    head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts_href}" rel="stylesheet">
<style>
"""
    tail = f"""
</style>
</head>
<body>
{body_html}
</body>
</html>
"""
    return head + css + tail


# ---------------------------------------------------------------------------
# 3. Theme 1 -- Full-Bleed Field Report
# ---------------------------------------------------------------------------

CSS_FIELD_REPORT = """
:root{--ink:#14181F;--navy:#1B2A4A;--brass:#B9863B;--paper:#F2F3F0;--success:#2F6F4E;--line:#D8D6CE;}
*{box-sizing:border-box;}
body{margin:0;background:var(--paper);color:var(--ink);font-family:'Public Sans',sans-serif;line-height:1.55;}
.topbar{position:absolute;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;padding:1.5rem 2rem;color:#fff;z-index:2;}
.topbar .logo{font-family:'Fraunces',serif;font-weight:600;font-size:1.1rem;}
.topbar nav a{color:#fff;text-decoration:none;margin-left:1.5rem;font-size:0.9rem;opacity:0.85;}
.hero{position:relative;min-height:420px;display:flex;align-items:flex-end;padding:5rem 2rem 3rem;background:linear-gradient(120deg,#16223d 0%,#28406b 45%,#5c6c56 100%);color:#fff;overflow:hidden;}
.hero::after{content:"";position:absolute;inset:0;background:linear-gradient(0deg,rgba(0,0,0,.5),transparent 60%);}
.hero-content{position:relative;max-width:640px;}
.hero h1{font-family:'Fraunces',serif;font-weight:600;font-size:clamp(2rem,4vw,2.75rem);line-height:1.12;margin:0 0 0.75rem;}
.hero p{margin:0 0 1.5rem;font-size:1.05rem;max-width:38ch;color:rgba(255,255,255,.88);}
.btn{display:inline-block;background:var(--brass);color:#1c1406;font-weight:600;padding:0.7rem 1.4rem;border-radius:3px;text-decoration:none;font-size:0.95rem;}
.section{padding:3rem 2rem;max-width:960px;margin:0 auto;}
.section h2{font-family:'Fraunces',serif;font-weight:600;font-size:1.4rem;margin:0 0 1.25rem;}
.match-card{display:grid;grid-template-columns:4px 1fr auto;gap:1.25rem;align-items:center;background:#fff;border:1px solid var(--line);padding:1.25rem 1.5rem;border-radius:4px;}
.match-card .bar{align-self:stretch;background:var(--success);border-radius:2px;}
.match-card h3{margin:0 0 0.2rem;font-size:1.05rem;}
.match-card p{margin:0;color:#5b5c56;font-size:0.9rem;}
.pill{background:#e7f0ea;color:var(--success);font-size:0.85rem;font-weight:600;padding:0.3rem 0.75rem;border-radius:999px;white-space:nowrap;}
details{border-top:1px solid var(--line);padding:1rem 0;}
summary{font-weight:600;cursor:pointer;}
.report-row{display:flex;justify-content:space-between;padding:0.6rem 0;border-bottom:1px solid var(--line);font-size:0.95rem;}
.status{color:#5b5c56;font-size:0.85rem;}
footer{padding:2rem;color:#8a8b84;font-size:0.85rem;max-width:960px;margin:0 auto;}
"""


def body_field_report(c: dict) -> str:
    rows = "\n".join(
        f'<div class="report-row"><span>{r["title"]}</span><span class="status">{r["status"]} \u00b7 {r["date"]}</span></div>'
        for r in c["reports"]
    )
    return f"""
<div class="topbar"><div class="logo">{c['site_name']}</div>
<nav>{''.join(f'<a href="#">{n}</a>' for n in c['nav'])}</nav></div>
<section class="hero"><div class="hero-content">
<h1>{c['headline']}</h1><p>{c['subtext']}</p>
<a class="btn" href="#">{c['cta']}</a>
</div></section>
<section class="section"><h2>{c['matches_heading']}</h2>
<div class="match-card"><div class="bar"></div>
<div><h3>{c['match']['title']}</h3><p>{c['match']['detail']}</p></div>
<div class="pill">{c['match']['confidence']}</div></div></section>
<section class="section"><details open><summary>{c['reports_heading']}</summary>{rows}</details></section>
<footer>{c['footer']}</footer>
"""


# ---------------------------------------------------------------------------
# 4. Theme 2 -- Ledger
# ---------------------------------------------------------------------------

CSS_LEDGER = """
:root{--ink:#23241F;--teal:#3E6B64;--paper:#EFEDE6;--amber:#B8792C;--line:#CBC6B8;}
*{box-sizing:border-box;}
body{margin:0;background:var(--paper);color:var(--ink);font-family:'Work Sans',sans-serif;line-height:1.55;}
.masthead{border-bottom:3px double var(--ink);padding:1.5rem 2rem;}
.masthead .row{display:flex;justify-content:space-between;align-items:baseline;max-width:960px;margin:0 auto;}
.masthead .logo{font-family:'Lora',serif;font-weight:600;font-size:1.3rem;}
.masthead nav a{color:var(--ink);text-decoration:none;margin-left:1.25rem;font-size:0.85rem;border-bottom:1px solid transparent;}
.hero{max-width:960px;margin:0 auto;padding:3rem 2rem;display:grid;grid-template-columns:1.3fr 1fr;gap:2rem;align-items:end;}
.hero .meta{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:var(--teal);margin-bottom:0.5rem;}
.hero h1{font-family:'Lora',serif;font-weight:600;font-size:clamp(1.8rem,3.2vw,2.3rem);margin:0 0 0.75rem;}
.hero p{margin:0 0 1.25rem;color:#4b4c44;}
.btn{display:inline-block;border:1px solid var(--ink);color:var(--ink);padding:0.6rem 1.25rem;text-decoration:none;font-size:0.9rem;}
.section{max-width:960px;margin:0 auto;padding:1.5rem 2rem 3rem;}
.section h2{font-family:'Lora',serif;font-size:1.15rem;font-weight:600;border-bottom:1px solid var(--ink);padding-bottom:0.4rem;margin:0 0 1rem;}
.ledger-row{display:grid;grid-template-columns:6rem 1fr auto;gap:1rem;padding:0.6rem 0;border-bottom:1px solid var(--line);align-items:baseline;}
.ledger-row .id{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;color:#7a7a70;}
.status{font-size:0.85rem;}
.status.matched{color:var(--teal);}
.status.pending{color:var(--amber);}
.status.open{color:#7a7a70;}
details summary{font-family:'Lora',serif;font-weight:600;cursor:pointer;}
footer{max-width:960px;margin:0 auto;padding:1.5rem 2rem;color:#7a7a70;font-size:0.8rem;font-family:'IBM Plex Mono',monospace;}
"""


def body_ledger(c: dict) -> str:
    rows = "\n".join(
        f'<div class="ledger-row"><span class="id">{r["date"]}</span><span>{r["title"]}</span><span class="status {r["status_class"]}">{r["status"]}</span></div>'
        for r in c["reports"]
    )
    return f"""
<div class="masthead"><div class="row"><div class="logo">{c['site_name']}</div>
<nav>{''.join(f'<a href="#">{n}</a>' for n in c['nav'])}</nav></div></div>
<section class="hero"><div>
<div class="meta">Lost &amp; Found Register</div>
<h1>{c['headline']}</h1>
<a class="btn" href="#">{c['cta']}</a>
</div><p>{c['subtext']}</p></section>
<section class="section"><h2>{c['matches_heading']}</h2>
<div class="ledger-row"><span class="id">today</span><span>{c['match']['title']} \u2014 {c['match']['detail']}</span><span class="status matched">{c['match']['confidence']}</span></div>
</section>
<section class="section"><details open><summary>{c['reports_heading']}</summary>{rows}</details></section>
<footer>{c['footer']}</footer>
"""


# ---------------------------------------------------------------------------
# 5. Theme 3 -- Signal Board
# ---------------------------------------------------------------------------

CSS_SIGNAL_BOARD = """
:root{--cork:#6B5B4E;--notice:#F5F1E4;--pin:#B1443A;--ink:#201C18;--line:rgba(0,0,0,.12);}
*{box-sizing:border-box;}
body{margin:0;color:var(--ink);font-family:'Source Sans 3',sans-serif;min-height:100vh;
background-color:var(--cork);
background-image:repeating-linear-gradient(135deg,rgba(0,0,0,.06) 0 2px,transparent 2px 5px);}
header{padding:1.5rem 2rem;display:flex;justify-content:space-between;color:#f2ece0;}
header .logo{font-family:'Zilla Slab',serif;font-weight:700;font-size:1.2rem;}
header nav a{color:#f2ece0;opacity:.85;text-decoration:none;margin-left:1.25rem;font-size:.9rem;}
.board{max-width:960px;margin:0 auto;padding:1rem 2rem 3rem;display:flex;flex-direction:column;gap:2rem;}
.notice{background:var(--notice);padding:2rem;position:relative;box-shadow:0 10px 20px rgba(0,0,0,.25);}
.notice.hero-notice{transform:rotate(-1deg);}
.notice .pin{position:absolute;top:-9px;left:2.5rem;width:18px;height:18px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#e07a70,var(--pin));box-shadow:0 2px 4px rgba(0,0,0,.4);}
.notice h1{font-family:'Zilla Slab',serif;font-weight:700;font-size:clamp(1.8rem,3.4vw,2.4rem);margin:0.5rem 0 0.75rem;}
.notice p{margin:0 0 1.25rem;max-width:42ch;}
.btn{display:inline-block;background:var(--ink);color:#f5f1e4;padding:0.65rem 1.3rem;text-decoration:none;font-size:.9rem;}
.small-notices{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;}
.notice.small{transform:rotate(.7deg);padding:1.25rem 1.5rem;}
.notice.small:nth-of-type(2){transform:rotate(-.6deg);}
.notice h2{font-family:'Zilla Slab',serif;font-size:1.1rem;margin:0.4rem 0 .75rem;}
.match-row{display:flex;justify-content:space-between;align-items:center;}
.tag{font-size:.8rem;background:#ece3cf;padding:.25rem .6rem;border-radius:3px;color:#5b4a2e;}
details summary{font-family:'Zilla Slab',serif;font-weight:700;cursor:pointer;}
.report-row{display:flex;justify-content:space-between;padding:.5rem 0;border-bottom:1px dashed var(--line);}
footer{text-align:center;color:#f2ece0cc;padding:1.5rem;font-size:.8rem;}
"""


def body_signal_board(c: dict) -> str:
    rows = "\n".join(
        f'<div class="report-row"><span>{r["title"]}</span><span>{r["status"]} \u00b7 {r["date"]}</span></div>'
        for r in c["reports"]
    )
    return f"""
<header><div class="logo">{c['site_name']}</div>
<nav>{''.join(f'<a href="#">{n}</a>' for n in c['nav'])}</nav></header>
<div class="board">
<div class="notice hero-notice"><div class="pin"></div>
<h1>{c['headline']}</h1><p>{c['subtext']}</p>
<a class="btn" href="#">{c['cta']}</a></div>
<div class="small-notices">
<div class="notice small"><h2>{c['matches_heading']}</h2>
<div class="match-row"><span>{c['match']['title']}<br><small>{c['match']['detail']}</small></span><span class="tag">{c['match']['confidence']}</span></div></div>
<div class="notice small"><details open><summary>{c['reports_heading']}</summary>{rows}</details></div>
</div>
</div>
<footer>{c['footer']}</footer>
"""


# ---------------------------------------------------------------------------
# 6. Theme 4 -- Quiet Directory
# ---------------------------------------------------------------------------

CSS_QUIET_DIRECTORY = """
:root{--ink:#16181D;--steel:#2E5C8A;--bg:#FAFAF9;--muted:#6B6F76;--line:#E4E4E1;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);font-family:'Archivo',sans-serif;line-height:1.6;}
.wrap{max-width:720px;margin:0 auto;padding:2.5rem 1.5rem 4rem;}
header{display:flex;justify-content:space-between;align-items:center;padding-bottom:2rem;border-bottom:1px solid var(--line);margin-bottom:2.5rem;}
header .logo{font-weight:700;font-size:1.05rem;}
header nav a{color:var(--muted);text-decoration:none;margin-left:1.25rem;font-size:.9rem;}
.label{font-variant:small-caps;letter-spacing:.02em;color:var(--muted);font-size:.9rem;font-weight:600;margin:0 0 .5rem;}
h1{font-weight:700;font-size:clamp(1.6rem,3vw,2rem);margin:0 0 .75rem;max-width:22ch;}
.hero p{color:var(--muted);max-width:52ch;margin:0 0 1.25rem;}
.btn{display:inline-block;background:var(--steel);color:#fff;padding:.6rem 1.2rem;text-decoration:none;font-size:.9rem;font-weight:500;}
section{margin-top:2.5rem;}
.row{display:flex;justify-content:space-between;align-items:baseline;padding:.85rem 0;border-bottom:1px solid var(--line);}
.row .title{font-weight:500;}
.row .meta{color:var(--muted);font-size:.85rem;}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:.4rem;position:relative;top:-1px;}
.dot.matched{background:var(--steel);}
.dot.pending{background:#c98a2e;}
.dot.open{background:#9a9d9f;}
details summary{font-weight:600;cursor:pointer;}
footer{margin-top:3rem;color:var(--muted);font-size:.8rem;}
"""


def body_quiet_directory(c: dict) -> str:
    rows = "\n".join(
        f'<div class="row"><span class="title">{r["title"]}</span>'
        f'<span class="meta"><span class="dot {r["status_class"]}"></span>{r["status"]} \u00b7 {r["date"]}</span></div>'
        for r in c["reports"]
    )
    return f"""
<div class="wrap">
<header><div class="logo">{c['site_name']}</div>
<nav>{''.join(f'<a href="#">{n}</a>' for n in c['nav'])}</nav></header>
<div class="hero">
<p class="label">Lost &amp; found</p>
<h1>{c['headline']}</h1>
<p>{c['subtext']}</p>
<a class="btn" href="#">{c['cta']}</a>
</div>
<section><p class="label">{c['matches_heading']}</p>
<div class="row"><span class="title">{c['match']['title']}</span><span class="meta">{c['match']['detail']} \u00b7 {c['match']['confidence']}</span></div>
</section>
<section><details open><summary>{c['reports_heading']}</summary>{rows}</details></section>
<footer>{c['footer']}</footer>
</div>
"""


# ---------------------------------------------------------------------------
# 7. Theme 5 -- Match Signal (claim ticket)
# ---------------------------------------------------------------------------

CSS_MATCH_SIGNAL = """
:root{--indigo:#21254A;--paper:#EFEEEA;--amber:#E2A93B;--green:#3C8465;--ink:#1C1E29;--page:#E4E2DA;}
*{box-sizing:border-box;}
body{margin:0;background:var(--page);color:var(--ink);font-family:'Work Sans',sans-serif;padding:2rem 1rem;}
header{max-width:760px;margin:0 auto 1.5rem;display:flex;justify-content:space-between;align-items:center;}
header .logo{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:1.3rem;letter-spacing:.02em;}
header nav a{color:var(--ink);opacity:.7;text-decoration:none;margin-left:1.25rem;font-size:.85rem;}
.ticket{max-width:760px;margin:0 auto 1.5rem;background:var(--paper);border-radius:6px;display:grid;grid-template-columns:1fr 220px;position:relative;box-shadow:0 6px 18px rgba(0,0,0,.12);}
.ticket .stub-main{padding:2rem;border-left:6px solid var(--green);border-radius:6px 0 0 6px;}
.ticket .stub-side{padding:2rem 1.5rem;position:relative;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:.75rem;border-left:2px dashed #c9c5ba;}
.ticket .stub-side::before,.ticket .stub-side::after{content:"";position:absolute;left:-9px;width:18px;height:18px;border-radius:50%;background:var(--page);}
.ticket .stub-side::before{top:-9px;}
.ticket .stub-side::after{bottom:-9px;}
.ticket h1{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:clamp(1.6rem,3vw,2.1rem);margin:0 0 .5rem;line-height:1.1;}
.ticket p{margin:0 0 1.25rem;color:#4c4e5c;max-width:36ch;}
.btn{display:inline-block;background:var(--indigo);color:#fff;padding:.65rem 1.3rem;border-radius:4px;text-decoration:none;font-size:.9rem;}
.qr{width:72px;height:72px;background:repeating-conic-gradient(#1c1e29 0 25%,transparent 0 50%) 0 0/14px 14px;border-radius:4px;}
.code{font-family:'JetBrains Mono',monospace;font-size:.8rem;color:#4c4e5c;}
.section{max-width:760px;margin:0 auto;padding:1.5rem 0;}
.section h2{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:1.2rem;margin:0 0 .9rem;}
.mini-ticket{display:grid;grid-template-columns:6px 1fr auto;align-items:center;background:var(--paper);border-radius:4px;margin-bottom:.6rem;overflow:hidden;}
.mini-ticket .stripe{align-self:stretch;}
.mini-ticket .stripe.matched{background:var(--green);}
.mini-ticket .stripe.pending{background:var(--amber);}
.mini-ticket .stripe.open{background:#a9a79d;}
.mini-ticket .body{padding:.75rem 1rem;}
.mini-ticket .body .title{font-weight:600;}
.mini-ticket .body .meta{font-family:'JetBrains Mono',monospace;font-size:.75rem;color:#6b6d78;}
.mini-ticket .status{padding:0 1rem;font-size:.8rem;color:#4c4e5c;}
details summary{font-family:'Barlow Condensed',sans-serif;font-weight:700;cursor:pointer;font-size:1.05rem;}
footer{max-width:760px;margin:1.5rem auto 0;color:#6b6d78;font-size:.8rem;}
"""


def body_match_signal(c: dict) -> str:
    rows = "\n".join(
        f'<div class="mini-ticket"><div class="stripe {r["status_class"]}"></div>'
        f'<div class="body"><div class="title">{r["title"]}</div><div class="meta">{r["date"]}</div></div>'
        f'<div class="status">{r["status"]}</div></div>'
        for r in c["reports"]
    )
    return f"""
<header><div class="logo">{c['site_name']}</div>
<nav>{''.join(f'<a href="#">{n}</a>' for n in c['nav'])}</nav></header>
<div class="ticket">
<div class="stub-main">
<h1>{c['headline']}</h1><p>{c['subtext']}</p>
<a class="btn" href="#">{c['cta']}</a>
</div>
<div class="stub-side">
<div class="qr" title="QR placeholder"></div>
<div class="code">CLAIM-04821</div>
</div>
</div>
<section class="section"><h2>{c['matches_heading']}</h2>
<div class="mini-ticket"><div class="stripe matched"></div>
<div class="body"><div class="title">{c['match']['title']}</div><div class="meta">{c['match']['detail']}</div></div>
<div class="status">{c['match']['confidence']}</div></div>
</section>
<section class="section"><details open><summary>{c['reports_heading']}</summary>{rows}</details></section>
<footer>{c['footer']}</footer>
"""


# ---------------------------------------------------------------------------
# 8. Theme registry
# ---------------------------------------------------------------------------

THEMES = [
    {
        "id": "full-bleed-field-report",
        "name": "Full-Bleed Field Report",
        "fonts_href": "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Public+Sans:wght@400;500;600&display=swap",
        "css": CSS_FIELD_REPORT,
        "body": body_field_report,
        "rationale": (
            "Answers the full-bleed hero idea directly: a photographic gradient "
            "hero with the headline anchored bottom-left instead of centered, "
            "which also fixes the dead-space complaint since the copy now "
            "occupies an edge instead of floating in the middle. Fraunces "
            "gives the headline weight without needing a bigger size."
        ),
    },
    {
        "id": "ledger",
        "name": "Ledger",
        "fonts_href": "https://fonts.googleapis.com/css2?family=Lora:wght@500;600&family=IBM+Plex+Mono:wght@400;500&family=Work+Sans:wght@400;500&display=swap",
        "css": CSS_LEDGER,
        "body": body_ledger,
        "rationale": (
            "Leans into what the app actually is: a register of claims. Reports "
            "read as ledger rows (date, item, status) instead of cards, so a "
            "long report history stays scannable rather than turning into a "
            "stack of boxes. No badges at all, so the all-caps badge problem "
            "cannot recur."
        ),
    },
    {
        "id": "signal-board",
        "name": "Signal Board",
        "fonts_href": "https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;700&family=Source+Sans+3:wght@400;600&display=swap",
        "css": CSS_SIGNAL_BOARD,
        "body": body_signal_board,
        "rationale": (
            "Literal campus corkboard, since that's the real-world thing this "
            "app replaces. The hero is one slightly rotated pinned notice "
            "instead of a centered banner, and the matches/reports panels are "
            "smaller notices with their own tilt so nothing lines up into a "
            "uniform card grid."
        ),
    },
    {
        "id": "quiet-directory",
        "name": "Quiet Directory",
        "fonts_href": "https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;700&display=swap",
        "css": CSS_QUIET_DIRECTORY,
        "body": body_quiet_directory,
        "rationale": (
            "The most restrained option: one typeface, one accent color, left "
            "aligned throughout, dividers instead of shadows. Section labels "
            "use small-caps rather than uppercase text, so they stay quiet "
            "instead of shouting like the old badge did. Best fit if the goal "
            "is to look like campus IT infrastructure, not a startup landing page."
        ),
    },
    {
        "id": "match-signal",
        "name": "Match Signal",
        "fonts_href": "https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;700&family=Work+Sans:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap",
        "css": CSS_MATCH_SIGNAL,
        "body": body_match_signal,
        "rationale": (
            "Ties directly into the QR scan-to-claim flow already planned: the "
            "hero and every report render as a claim-ticket stub, with a "
            "colored edge stripe carrying the status instead of a badge. Once "
            "real QR codes exist this is the direction that will feel least "
            "like it was bolted on afterward."
        ),
    },
]


# ---------------------------------------------------------------------------
# 9. Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", help="Path to the Django project root")
    parser.add_argument("-o", "--out", default="style_suggestions", help="Output directory")
    args = parser.parse_args()

    root = Path(args.project)
    scan = scan_project(root)
    print_scan_summary(scan)

    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)

    report_lines = ["# 5 UI styling directions for Where Is My Stuff?\n"]
    if scan["templates"] or scan["css_files"]:
        report_lines.append(
            f"Scanned `{root.resolve()}` \u2014 "
            f"{len(scan['templates'])} template(s), {len(scan['css_files'])} CSS file(s).\n"
        )
    else:
        report_lines.append(
            f"No templates/static found under `{root.resolve()}`; previews below use the "
            "app's known screens (landing hero, recent matches, report list).\n"
        )

    for theme in THEMES:
        body_html = theme["body"](COPY)
        html = page_shell(theme["name"], theme["fonts_href"], theme["css"], body_html)
        out_path = out_dir / f"{theme['id']}.html"
        out_path.write_text(html, encoding="utf-8")
        report_lines.append(f"## {theme['name']}\n\n{theme['rationale']}\n\nPreview: `{out_path}`\n")
        print(f"  wrote {out_path}")

    (out_dir / "REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nDone. Open any file in {out_dir}/ in a browser to compare "
          "(needs internet the first time, for the Google Fonts).")


if __name__ == "__main__":
    main()
