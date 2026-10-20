from __future__ import annotations

import re
from pathlib import Path

import fitz

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "SRS-Where-Is-My-Stuff.pdf"
LATEX = DOCS / "SRS-Where-Is-My-Stuff.tex"
SOURCE = DOCS / "SRS-STAKEHOLDER-REVIEW.md"
NAVY = colors.HexColor("#12314B")
TEAL = colors.HexColor("#087E83")
PALE = colors.HexColor("#EAF3F4")
INK = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#596B78")
LINE = colors.HexColor("#CAD5DC")


def source_rows() -> list[str]:
    rows = SOURCE.read_text(encoding="utf-8").splitlines()
    appendix_at = next((i for i, row in enumerate(rows) if row.startswith("## Appendix A.")), len(rows))
    revision_at = next((i for i, row in enumerate(rows) if row.startswith("## 12. Source basis")), len(rows))
    if appendix_at < revision_at < len(rows):
        rows = rows[:appendix_at] + rows[revision_at:] + rows[appendix_at:revision_at]
    return rows


def tex_escape(s: str) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "<": r"\textless{}",
        ">": r"\textgreater{}",
        "–": "--",
        "—": "---",
        "“": "``",
        "”": "''",
        "→": r"$\rightarrow$",
        "×": r"$\times$",
    }
    return "".join(repl.get(c, c) for c in s)


def parse_inline(s: str, latex: bool = False) -> str:
    if latex:
        s = tex_escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
        s = re.sub(r"`(.+?)`", r"\\texttt{\1}", s)
        s = re.sub(r"\*(.+?)\*", r"\\emph{\1}", s)
        return s
    # Paragraph text is escaped before the small set of inline styles is added.
    s = escape(s).replace("\\", "&#92;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<font name='DejaVuMono'>\1</font>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    return s


def markdown_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
            continue
        rows.append(cells)
    return rows


def build_latex(rows: list[str]) -> None:
    appendix_at = next((i for i, row in enumerate(rows) if row.startswith("## Appendix A.")), len(rows))
    revision_at = next((i for i, row in enumerate(rows) if row.startswith("## 12. Source basis")), len(rows))
    if appendix_at < revision_at < len(rows):
        rows = rows[:appendix_at] + rows[revision_at:] + rows[appendix_at:revision_at]
    pieces = [
        r"\documentclass[12pt,a4paper]{report}",
        r"\usepackage[margin=25mm,headheight=15pt]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{lmodern}",
        r"\usepackage{microtype}",
        r"\usepackage{graphicx}",
        r"\usepackage{booktabs,longtable,array,tabularx}",
        r"\usepackage{xcolor}",
        r"\usepackage{fancyhdr}",
        r"\usepackage{hyperref}",
        r"\hypersetup{colorlinks=true,linkcolor=teal,urlcolor=teal}",
        r"\definecolor{navy}{HTML}{12314B}",
        r"\definecolor{teal}{HTML}{087E83}",
        r"\pagestyle{fancy}\fancyhf{}\lhead{Where Is My Stuff? | SRS v3.2}\rhead{CS-326}\cfoot{\thepage}",
        r"\setlength{\parskip}{5pt}\setlength{\parindent}{0pt}",
        r"\begin{document}",
        r"\begin{titlepage}\centering\vspace*{16mm}",
        r"{\color{teal}\Large NED UNIVERSITY OF ENGINEERING AND TECHNOLOGY\par}",
        r"\vspace{3mm}{\large Department of Computer and Information Systems Engineering\par}",
        r"\vspace{24mm}{\color{navy}\bfseries\LARGE SOFTWARE REQUIREMENTS SPECIFICATION\par}",
        r"\vspace{9mm}{\bfseries\huge Where Is My Stuff?\par}",
        r"\vspace{3mm}{\Large Karachi Lost-and-Found Web Application\par}",
        r"\vspace{12mm}{\large Final formatted submission copy\par}",
        r"\vspace{2mm}{\large Version 3.2\par}",
        r"\vfill\begin{tabular}{rl}Course:& CS-326 Software Engineering\\Course instructor:& Dr. Fakhra Aftab\\Prepared by:& Project team\\Document status:& Final formatted copy; approvals pending\\Submission date:& October 2026\end{tabular}",
        r"\vfill{\small Release 1.0 implementation baseline; proposed future scope is informative only.\par}\end{titlepage}",
        r"\pagenumbering{roman}\chapter*{Revision history}",
        r"\begin{longtable}{p{18mm}p{95mm}p{35mm}}\toprule Version & Summary & Approval \\\midrule 1.1 & Initial project SRS baseline and roadmap. & Not recorded \\ 3.0 & Added normative requirements, acceptance criteria, and traceability. & Review pending \\ 3.1 & Aligned detailed behavior and release scope with the implementation. & Review pending \\ 3.2 & Clarified mandatory location inputs, review visibility, sensitive photos, and non-normative roadmap and quality targets. & Review pending \\\bottomrule\end{longtable}",
        r"\chapter*{Approval record}\begin{tabularx}{\textwidth}{lXXX}\toprule Role & Name & Decision & Date \\\midrule Project owner & & Pending & \\ User/stakeholder representative & & Pending & \\ Course reviewer & & Pending & \\\bottomrule\end{tabularx}",
        r"\tableofcontents\clearpage\pagenumbering{arabic}",
    ]
    i = 0
    chapter_map = {"1. Introduction": "Introduction", "2. Overall description": "Overall Description", "3. External interface requirements": "External Interface Requirements", "4. System features and functional requirements": "System Features and Functional Requirements", "5. Business rules": "Business Rules", "6. Data requirements": "Data Requirements", "7. Non-functional requirements": "Non-Functional Requirements", "8. Security, privacy, and trust requirements": "Security, Privacy, and Trust Requirements", "9. Use cases": "Use Cases", "10. Open decisions and exclusions": "Open Decisions and Exclusions", "11. Acceptance and requirement traceability": "Acceptance and Requirement Traceability"}
    while i < len(rows):
        line = rows[i]
        if line == "# Software Requirements Specification" or line.startswith("## Where Is My Stuff?"):
            i += 1
            while i < len(rows) and (not rows[i].strip() or rows[i].startswith("|")):
                i += 1
            continue
        if line.startswith("## Appendix A."):
            pieces.append(r"\appendix\chapter{Informative Future Roadmap (Non-normative)}")
            i += 1
            continue
        if line.startswith("## 12. Source basis"):
            pieces.append(r"\chapter{Source Basis and Revision}")
            i += 1
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            pieces.append(r"\chapter{" + tex_escape(chapter_map.get(title, title)) + "}")
            i += 1
            continue
        if line.startswith("### "):
            title = line[4:].strip()
            pieces.append(r"\section{" + tex_escape(title) + "}")
            i += 1
            continue
        if line.startswith("|"):
            block = []
            while i < len(rows) and rows[i].startswith("|"):
                block.append(rows[i]); i += 1
            table = markdown_table(block)
            if table:
                proportions = {2: [0.23, 0.77], 3: [0.17, 0.42, 0.41], 4: [0.18, 0.12, 0.35, 0.35]}.get(len(table[0]), [1 / len(table[0])] * len(table[0]))
                widths = "".join(r"p{%.3f\textwidth}" % (part * 0.94) for part in proportions)
                pieces.append(r"\begingroup\small\renewcommand{\arraystretch}{1.15}\begin{longtable}{@{}" + widths + "@{}}\\toprule")
                for ri, cells in enumerate(table):
                    cells = cells + [""] * (len(table[0]) - len(cells))
                    pieces.append(" & ".join(parse_inline(cell, True) for cell in cells) + r"\\")
                    if ri == 0: pieces.append(r"\midrule\endhead")
                pieces.append(r"\bottomrule\end{longtable}\endgroup")
            continue
        if line.startswith("- "):
            pieces.append(r"\begin{itemize}")
            while i < len(rows) and rows[i].startswith("- "):
                pieces.append(r"\item " + parse_inline(rows[i][2:], True)); i += 1
            pieces.append(r"\end{itemize}")
            continue
        if line.strip():
            pieces.append(parse_inline(line, True) + "\\par")
        i += 1
    pieces.append(r"\appendix\chapter{Selected User Interface References}")
    pieces.append(r"The following project wireframes illustrate the report and matching flows. They support, but do not override, normative requirements in this specification.")
    for image_name, caption in [("ui-wireframe-report-flow.png", "Five-stage report wizard and location flow."), ("ui-wireframe-matching-categories-final.png", "Private matching questions by category.")]:
        pieces.append(r"\begin{figure}[p]\centering\includegraphics[width=0.96\linewidth,height=0.72\textheight,keepaspectratio]{docs/" + image_name + "}\\caption{" + tex_escape(caption) + r"}\end{figure}\clearpage")
    pieces.append(r"\end{document}")
    LATEX.write_text("\n".join(pieces), encoding="utf-8")


def register_fonts() -> None:
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("DejaVu", str(font_dir / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuBold", str(font_dir / "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuItalic", str(font_dir / "ariali.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuMono", str(font_dir / "consola.ttf")))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVuBold", italic="DejaVuItalic", boldItalic="DejaVuBold")


class NumberedCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.saveState()
                self.setFont("DejaVu", 8)
                self.setFillColor(MUTED)
                number = ("i", "ii")[self._pageNumber - 2] if self._pageNumber <= 3 else str(self._pageNumber - 3)
                self.drawCentredString(A4[0] / 2, 12 * mm, number)
                self.restoreState()
            Canvas.showPage(self)
        Canvas.save(self)


def make_styles():
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="DejaVu", fontSize=9.1, leading=12.4, textColor=INK, spaceAfter=5, alignment=TA_LEFT),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="DejaVu", fontSize=8.1, leading=10.2, textColor=INK, spaceAfter=2),
        "h1": ParagraphStyle("H1", fontName="DejaVuBold", fontSize=17, leading=21, textColor=NAVY, spaceBefore=14, spaceAfter=10, keepWithNext=True),
        "h2": ParagraphStyle("H2", fontName="DejaVuBold", fontSize=12.5, leading=16, textColor=TEAL, spaceBefore=10, spaceAfter=6, keepWithNext=True),
        "h3": ParagraphStyle("H3", fontName="DejaVuBold", fontSize=10.5, leading=13, textColor=NAVY, spaceBefore=7, spaceAfter=4, keepWithNext=True),
        "cover": ParagraphStyle("Cover", fontName="DejaVuBold", fontSize=24, leading=30, textColor=NAVY, alignment=TA_CENTER),
        "cover2": ParagraphStyle("Cover2", fontName="DejaVu", fontSize=13, leading=18, textColor=MUTED, alignment=TA_CENTER),
        "toc": ParagraphStyle("TOC", fontName="DejaVu", fontSize=9.2, leading=14, textColor=INK),
        "callout": ParagraphStyle("Callout", fontName="DejaVuBold", fontSize=9.2, leading=13, textColor=NAVY, spaceAfter=0),
    }


def p(text: str, style) -> Paragraph:
    return Paragraph(parse_inline(text), style)


def table_flow(rows: list[list[str]], width: float, styles, repeat=True):
    if not rows:
        return Spacer(1, 1)
    n = len(rows[0])
    # Prioritize identifiers for requirement tables, distribute remaining width by text columns.
    if n == 2:
        widths = [width * 0.23, width * 0.77]
    elif n == 3:
        widths = [width * 0.17, width * 0.42, width * 0.41]
    elif n == 4:
        widths = [width * 0.18, width * 0.12, width * 0.35, width * 0.35]
    else:
        widths = [width / n] * n
    data = []
    for ri, row in enumerate(rows):
        row = row + [""] * (n - len(row))
        data.append([Paragraph(parse_inline(cell), styles["small"]) for cell in row[:n]])
    t = Table(data, colWidths=widths, repeatRows=1 if repeat else 0, hAlign="LEFT", splitByRow=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVuBold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def draw_header(canvas, doc):
    if doc.page <= 1:
        return
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.45)
    canvas.line(25 * mm, h - 17 * mm, w - 25 * mm, h - 17 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("DejaVu", 7.5)
    canvas.drawString(25 * mm, h - 13 * mm, "WHERE IS MY STUFF?  |  SOFTWARE REQUIREMENTS SPECIFICATION")
    canvas.drawRightString(w - 25 * mm, h - 13 * mm, "CS-326  |  VERSION 3.2")
    canvas.restoreState()


class SrsDocTemplate(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph) or not flowable.style.name.startswith("anchor-h"):
            return
        level = 0 if flowable.style.name.startswith("anchor-h1-") else 1
        title = flowable.getPlainText()
        key = "bookmark-" + flowable.style.name
        self.canv.bookmarkPage(key)
        try:
            self.canv.addOutlineEntry(title, key, level=level, closed=False)
        except ValueError:
            pass
        self.notify("TOCEntry", (level, title, self.page, key))


def collect_toc_entries(rows: list[str]) -> list[tuple[int, str]]:
    section_map = {"1. Introduction": "1 Introduction", "2. Overall description": "2 Overall Description", "3. External interface requirements": "3 External Interface Requirements", "4. System features and functional requirements": "4 System Features and Functional Requirements", "5. Business rules": "5 Business Rules", "6. Data requirements": "6 Data Requirements", "7. Non-functional requirements": "7 Non-Functional Requirements", "8. Security, privacy, and trust requirements": "8 Security, Privacy, and Trust Requirements", "9. Use cases": "9 Use Cases", "10. Open decisions and exclusions": "10 Open Decisions and Exclusions", "11. Acceptance and requirement traceability": "11 Acceptance and Requirement Traceability", "12. Source basis and revision": "12 Source Basis and Revision"}
    entries = []
    for line in rows:
        if line.startswith("## ") and not line.startswith("## Where Is My Stuff?"):
            title = line[3:].strip()
            if title.startswith("Appendix A."):
                title = "Appendix A. Informative Future Roadmap"
            entries.append((0, section_map.get(title, title)))
        elif line.startswith("### "):
            entries.append((1, line[4:].strip()))
    entries.append((0, "Appendix B. Selected User Interface References"))
    return entries


def page_number_map(entries: list[tuple[int, str]]) -> dict[str, str]:
    pdf = fitz.open(OUT)
    page_texts = [page.get_text() for page in pdf]
    intro_index = next((i for i, text in enumerate(page_texts) if i > 1 and "1 Introduction" in text), 3)
    result = {}
    for _, title in entries:
        needle = re.sub(r"\s+", " ", title).strip().casefold()
        for i in range(intro_index, len(page_texts)):
            haystack = re.sub(r"\s+", " ", page_texts[i]).casefold()
            if needle in haystack:
                result[title] = str(i - intro_index + 1)
                break
    pdf.close()
    return result


def build_pdf(rows: list[str], page_numbers: dict[str, str] | None = None) -> None:
    register_fonts()
    styles = make_styles()
    doc = SrsDocTemplate(str(OUT), pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm, topMargin=24 * mm, bottomMargin=22 * mm, title="Where Is My Stuff? - Software Requirements Specification", author="Project Team")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=draw_header)])
    story: list[Flowable] = []
    # Cover page.
    story += [Spacer(1, 21 * mm), p("NED UNIVERSITY OF ENGINEERING AND TECHNOLOGY", styles["cover2"]), Spacer(1, 3 * mm), p("Department of Computer and Information Systems Engineering", styles["cover2"]), Spacer(1, 27 * mm), p("SOFTWARE REQUIREMENTS", styles["cover"]), p("SPECIFICATION", styles["cover"]), Spacer(1, 13 * mm), p("Where Is My Stuff?", ParagraphStyle("Project", parent=styles["cover"], fontSize=28, leading=34, textColor=TEAL)), Spacer(1, 4 * mm), p("Karachi Lost-and-Found Web Application", styles["cover2"]), Spacer(1, 9 * mm), p("Final formatted submission copy  |  Version 3.2", styles["cover2"]), Spacer(1, 12 * mm)]
    details = [
        [Paragraph("COURSE", styles["small"]), Paragraph("CS-326 Software Engineering", styles["small"])],
        [Paragraph("COURSE INSTRUCTOR", styles["small"]), Paragraph("Dr. Fakhra Aftab", styles["small"])],
        [Paragraph("PREPARED BY", styles["small"]), Paragraph("Project team", styles["small"])],
        [Paragraph("STATUS", styles["small"]), Paragraph("Final copy; stakeholder/course approvals pending", styles["small"])],
        [Paragraph("SUBMISSION", styles["small"]), Paragraph("October 2026", styles["small"])],
    ]
    cover_table = Table(details, colWidths=[39 * mm, 83 * mm], hAlign="CENTER")
    cover_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), PALE), ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0,0),(-1,-1),"MIDDLE"), ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8), ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story += [cover_table, Spacer(1, 18 * mm), p("Release 1.0 implementation baseline. Proposed future scope and unapproved quality targets are informative only.", styles["cover2"]), PageBreak()]
    # Revision and approvals.
    story += [p("Revisions", styles["h1"]), table_flow([["Version", "Primary author(s)", "Description of version", "Date / approval"], ["1.1", "Project team", "Initial project SRS baseline and roadmap.", "Not recorded"], ["3.0", "Project team", "Added normative requirements, acceptance criteria, and traceability.", "Review pending"], ["3.1", "Project team", "Aligned detailed behavior and release scope with implementation.", "Review pending"], ["3.2", "Project team", "Clarified required location inputs, review visibility, sensitive photos, future roadmap, and proposed quality targets.", "October 2026 / review pending"]], doc.width, styles), Spacer(1, 7 * mm), p("Approval record", styles["h2"]), table_flow([["Role", "Name", "Decision", "Date"], ["Project owner", "", "Pending", ""], ["User/stakeholder representative", "", "Pending", ""], ["Course reviewer", "", "Pending", ""]], doc.width, styles), PageBreak()]
    # Contents lists the sections and their final page numbers.
    toc_entries=collect_toc_entries(rows)
    section_map={"1. Introduction": "1 Introduction", "2. Overall description":"2 Overall Description", "3. External interface requirements":"3 External Interface Requirements", "4. System features and functional requirements":"4 System Features and Functional Requirements", "5. Business rules":"5 Business Rules", "6. Data requirements":"6 Data Requirements", "7. Non-functional requirements":"7 Non-Functional Requirements", "8. Security, privacy, and trust requirements":"8 Security, Privacy, and Trust Requirements", "9. Use cases":"9 Use Cases", "10. Open decisions and exclusions":"10 Open Decisions and Exclusions", "11. Acceptance and requirement traceability":"11 Acceptance and Requirement Traceability", "12. Source basis and revision":"12 Source Basis and Revision"}
    story.append(p("Contents", styles["h1"]))
    page_numbers = page_numbers or {}
    toc_style = ParagraphStyle("TOCCompact", fontName="DejaVu", fontSize=7.6, leading=9.2, textColor=INK)
    toc_bold_style = ParagraphStyle("TOCCompactBold", fontName="DejaVuBold", fontSize=7.8, leading=9.4, textColor=NAVY)
    toc_page_style = ParagraphStyle("TOCPage", fontName="DejaVu", fontSize=7.6, leading=9.2, textColor=MUTED, alignment=2)
    split = (len(toc_entries) + 1) // 2
    def toc_column(items):
        data=[]
        for level,title in items:
            label = title.upper() if level == 0 else "    " + title
            style = toc_bold_style if level == 0 else toc_style
            data.append([Paragraph(escape(label), style), Paragraph(escape(page_numbers.get(title, "")), toc_page_style)])
        table=Table(data,colWidths=[doc.width/2-17*mm,17*mm],hAlign="LEFT")
        table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-1),0.15,colors.HexColor("#E3E9ED")),("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2),("TOPPADDING",(0,0),(-1,-1),1.2),("BOTTOMPADDING",(0,0),(-1,-1),1.2)]))
        return table
    story.append(Table([[toc_column(toc_entries[:split]), toc_column(toc_entries[split:])]],colWidths=[doc.width/2,doc.width/2],hAlign="LEFT",style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),6)])))
    story.append(PageBreak())
    # Body from the vetted SRS markdown. Revision/approval block is rendered up front.
    i=0
    toc_counter=0
    while i < len(rows):
        line=rows[i]
        if line == "# Software Requirements Specification" or line.startswith("## Where Is My Stuff?"):
            i += 1
            while i < len(rows) and (not rows[i].strip() or rows[i].startswith("|")):
                i += 1
            continue
        if line.startswith("## Appendix A."):
            story.append(PageBreak()); toc_counter+=1; story.append(Paragraph("<a name='toc-%d'/>Appendix A. Informative Future Roadmap (Non-normative)" % toc_counter, styles["h1"])); i+=1; continue
        if line.startswith("## 12. Source basis"):
            story.append(PageBreak()); toc_counter+=1; story.append(Paragraph("<a name='toc-%d'/>12. Source Basis and Revision" % toc_counter, styles["h1"])); i+=1; continue
        if line.startswith("## ") and not line.startswith("## Where Is My Stuff?"):
            title=line[3:].strip()
            title=section_map.get(title,title)
            if title not in ("1 Introduction", "1. Introduction"):
                story.append(PageBreak())
            toc_counter+=1
            story.append(Paragraph(f"<a name='toc-{toc_counter}'/>{parse_inline(title)}", ParagraphStyle(f"anchor-h1-{toc_counter}", parent=styles["h1"])))
            i+=1; continue
        if line.startswith("### "):
            toc_counter+=1
            story.append(Paragraph(f"<a name='toc-{toc_counter}'/>{parse_inline(line[4:].strip())}", ParagraphStyle(f"anchor-h2-{toc_counter}", parent=styles["h2"])))
            i+=1; continue
        if line.startswith("|"):
            block=[]
            while i<len(rows) and rows[i].startswith("|"):
                block.append(rows[i]); i+=1
            parsed=markdown_table(block)
            if parsed: story.append(table_flow(parsed,doc.width,styles))
            story.append(Spacer(1,2*mm)); continue
        if line.startswith("- "):
            items=[]
            while i<len(rows) and rows[i].startswith("- "):
                items.append(Paragraph("&#8226; " + parse_inline(rows[i][2:]),styles["body"])); i+=1
            story.extend(items); continue
        if line.startswith("### UC-"):
            story.append(p(line[4:],styles["h3"])); i+=1; continue
        if line.startswith("**Exceptions:**") or line.startswith("**Alternative flows:**"):
            story.append(p(line,styles["body"])); i+=1; continue
        if line.strip() and not line.startswith("#"):
            story.append(p(line,styles["body"]))
        i+=1
    # Place selected supplied wireframes at the end as supporting figures, preserving their names.
    # The bibliography-style interface appendix is deliberately outside normative section numbering.
    story += [PageBreak(), p("Appendix B. Selected User Interface References", styles["h1"]), p("The following project wireframes illustrate the principal report and matching flows. They are supporting design references and do not override normative requirements in this specification.", styles["body"])]
    for fn,caption in [("ui-wireframe-report-flow.png","Figure B-1. Five-stage report wizard and location flow."),("ui-wireframe-matching-categories-final.png","Figure B-2. Matching categories and report presentation.")]:
        fp=DOCS/fn
        if fp.exists():
            img=Image(str(fp))
            maxw=doc.width; maxh=215*mm
            scale=min(maxw/img.imageWidth,maxh/img.imageHeight)
            img.drawWidth=img.imageWidth*scale; img.drawHeight=img.imageHeight*scale
            story += [Spacer(1,3*mm),img,p(caption,styles["small"]),Spacer(1,8*mm)]
    doc.build(story, canvasmaker=NumberedCanvas)


def main():
    rows=source_rows()
    build_latex(rows)
    entries = collect_toc_entries(rows)
    build_pdf(rows)
    build_pdf(rows, page_number_map(entries))
    print(f"LaTeX source: {LATEX}")
    print(f"PDF: {OUT}")


if __name__ == "__main__":
    main()
