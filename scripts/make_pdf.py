"""Render the consolidated (sheet-wise) and area-wise PDF reports."""
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DV", f"{FONT_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", f"{FONT_DIR}/DejaVuSans-Bold.ttf"))

INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#616e7c")
ACCENT = colors.HexColor("#0b6e6e")
HEAD_BG = colors.HexColor("#0b6e6e")
ZEBRA = colors.HexColor("#f2f6f6")
RULE = colors.HexColor("#c9d6d6")
PROB_COL = {"Very High": "#0a6b2e", "High": "#2f8f46", "Medium": "#a86b00", "Low": "#5f6b76",
            "Very Low": "#b3261e", "-": "#8a949e"}

ST = {
    "title": ParagraphStyle("title", fontName="DVB", fontSize=20, leading=24, textColor=INK),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=10, leading=14, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=14, leading=18, textColor=ACCENT, spaceAfter=4),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=10.5, leading=14, textColor=INK, spaceBefore=6,
                         spaceAfter=3),
    "body": ParagraphStyle("body", fontName="DV", fontSize=8.5, leading=11.5, textColor=INK),
    "note": ParagraphStyle("note", fontName="DV", fontSize=7.5, leading=10, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=6.6, leading=8.2, textColor=INK, alignment=TA_LEFT),
    "hcell": ParagraphStyle("hcell", fontName="DVB", fontSize=6.8, leading=8.2, textColor=colors.white),
    "kpi_n": ParagraphStyle("kpi_n", fontName="DVB", fontSize=15, leading=18, textColor=ACCENT),
    "kpi_l": ParagraphStyle("kpi_l", fontName="DV", fontSize=7.2, leading=9, textColor=MUTED),
}

PAGE_W = landscape(A4)[0] - 2 * 12 * mm


def cell(v, key=""):
    txt = escape(str(v if v is not None else ""))
    if key == "Probability" and v in PROB_COL:
        txt = f'<font name="DVB" color="{PROB_COL[v]}">{txt}</font>'
    if key == "Verification" and "DUE NOW" in str(v):
        txt = f'<font color="#b3261e">{txt}</font>'
    if key in ("Mobile no.", "Mobile (Deepika)", "Contact no.") and v:
        txt = f'<font name="DVB">{txt}</font>'
    return Paragraph(txt, ST["cell"])


def table(rows, cols, empty="No schools in this list."):
    """cols: list of (key, relative width)."""
    if not rows:
        return Paragraph(escape(empty), ST["note"])
    tot = sum(w for _, w in cols)
    widths = [PAGE_W * w / tot for _, w in cols]
    data = [[Paragraph(escape(k), ST["hcell"]) for k, _ in cols]]
    for r in rows:
        data.append([cell(r.get(k, ""), k) for k, _ in cols])
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(style))
    return t


def kpis(items):
    cells = [[Paragraph(str(n), ST["kpi_n"]) for n, _ in items],
             [Paragraph(escape(l), ST["kpi_l"]) for _, l in items]]
    t = Table(cells, colWidths=[PAGE_W / len(items)] * len(items))
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fafa")),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


# column layouts ------------------------------------------------------------------------
C_SUMMARY = [("Area", 8), ("State-syllabus schools", 7), ("CBSE / ICSE schools", 6),
             ("Found only in Aslam's log", 7), ("Total schools", 6), ("Visited (unique)", 6),
             ("Pending 1st visit", 6), ("- with mobile", 6), ("- no mobile", 6), ("2nd visit done", 6),
             ("2nd visit planned", 6), ("Deepika mobiles", 6), ("Deepika visited", 6), ("High / Very High", 6)]
C_SECOND = [("Second visit month", 9), ("Area", 7), ("School", 22), ("Contact person", 13), ("Contact no.", 11),
            ("First visit", 8), ("Tour period (remarks)", 11), ("Verification", 20), ("In Deepika data", 6),
            ("Probability", 7.5)]
C_VISITED = [("Area", 6), ("First visit", 7), ("School", 17), ("Type", 7), ("Contact person", 10.5),
             ("Contact no.", 9), ("Strength", 6), ("Visits", 7), ("Call remarks", 24), ("In Deepika data", 11),
             ("Official list", 6), ("Free-pass feedback", 9), ("Probability", 7.5)]
C_PEND_MOB = [("Area", 7), ("School", 26), ("Type", 10), ("Classes", 6), ("Mobile no.", 14), ("Other no.", 10),
              ("In Deepika data", 6), ("Source", 12), ("Free-pass feedback", 15), ("Probability", 7.5)]
C_PEND_NOMOB = [("Area", 8), ("School", 34), ("Type", 12), ("Classes", 7), ("Landline", 14),
                ("In Deepika data", 8), ("Source", 14)]
C_DEEPIKA = [("Area", 7), ("Deepika Sl", 5), ("School", 20), ("Deepika block", 8), ("Type", 8),
             ("Mobile (Deepika)", 10), ("Visited by executive", 14), ("Executive's remark", 22),
             ("Free-pass feedback", 12), ("Probability", 7.5)]
C_FP = [("Area", 6), ("Park visit", 7), ("Person", 8), ("Contact", 8), ("School (feedback form)", 13),
        ("Matched school", 13), ("Visited by Aslam", 10), ("Persons", 4), ("Executive (form)", 7),
        ("Glamping stay", 5), ("Feedback", 10), ("Tour period", 6), ("Final status", 6), ("Probability", 6)]


EXTRA = "Found only in Aslam's log"


def no_area(cols):
    return [c for c in cols if c[0] != "Area"]


def footer(title):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("DV", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(12 * mm, 7 * mm, title)
        canvas.drawRightString(landscape(A4)[0] - 12 * mm, 7 * mm, f"Page {doc.page}")
        canvas.restoreState()
    return draw


def cover(T, subtitle):
    s = T["stats"]
    p = s["prob"]
    story = [
        Paragraph("Aslam – School Visit Verification Report", ST["title"]),
        Paragraph(f"{subtitle} · Malappuram district · Visits {s['first_date']} to {s['last_date']} · "
                  f"Prepared {s['today']}", ST["sub"]),
        Spacer(1, 8),
        kpis([(s["unique_visited"], f"schools visited by Aslam ({s['visit_entries']} visit entries)"),
              (s["pending"], "schools pending first visit"),
              (s["pend_mob"], "pending schools with a mobile no."),
              (s["second_planned"], "second visits planned"),
              (s["due_now"], "second visits due now (Sept)"),
              (p["Very High"] + p["High"], "High / Very High probability")]),
        Spacer(1, 8),
        Paragraph("Area-wise summary (areas Aslam covered)", ST["h2"]),
        table(T["summary"], C_SUMMARY),
        Spacer(1, 6),
        Paragraph("How this was checked", ST["h2"]),
        Paragraph(
            f"Aslam's visit log ({s['counts']['visits']} entries) was compared with Deepika's Malappuram list "
            f"({s['counts']['deepika']} schools), the State-syllabus census ({s['counts']['state']} schools), "
            f"the CBSE/ICSE directory ({s['counts']['cbse']} Malappuram schools) and the free stay-pass feedback "
            f"register ({s['counts']['freepass']} entries). Schools were matched by phone number first, then by "
            "school type (AMLPS, GMUPS, HSS…) plus place name, allowing for spelling variants "
            "(Tirurangadi/Thirurangadi, Kodinhi/Kodinji). Repeat visits to the same school are counted once. "
            "Areas are the assembly constituencies used in the State census; places were mapped using the "
            "census school names, and a few unclear places were taken from that day's route.", ST["body"]),
        Spacer(1, 3),
        Paragraph(
            "<b>Second visit month</b>: taken from the 'Second Visit' column of Aslam's sheet and checked against "
            "the tour period in the call remarks (the rule used in the sheet is one month before the tour). "
            f"Where the column was empty but a tour month was given, the month was derived the same way "
            f"({s['derived']} schools, marked 'Derived'). "
            "<b>Confirmation probability</b>: Very High = used the free pass with positive feedback or pass booked; "
            "High = tour month given plus a positive response; Medium = positive response or tour month only; "
            "Low = not reachable / busy / no remark yet; Very Low = wrong number, declined or not interested. "
            "<b>Mobile numbers</b> are 10-digit numbers starting 6–9; other numbers are landlines "
            "(shown with a leading 0).", ST["body"]),
        Spacer(1, 3),
        Paragraph(
            f"Only {s['freepass']} of the {s['counts']['freepass']} free-pass feedback entries belong to schools in "
            "Aslam's areas; the rest are from other districts or other executives' areas. "
            f"{s['unique_visited'] - s['listed']} schools Aslam visited (mostly private, pre-schools and "
            "anganwadis) are not in any official list; they are added to the area totals as "
            "'Found only in Aslam's log'.", ST["note"]),
    ]
    return story


def build_consolidated(T, path):
    doc = SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=11 * mm, bottomMargin=12 * mm,
                            title="Aslam School Visit Verification – Consolidated", author="Sales team")
    s = T["stats"]
    story = cover(T, "Consolidated (sheet-wise)")
    sheets = [
        ("Sheet 1 – Second visit schedule (month-wise, verified)",
         f"{s['second_planned']} schools need a second visit; {s['second_done']} schools have already been "
         "revisited. Rows in red are due now (September / after Onam).", T["second"], C_SECOND),
        ("Sheet 2 – Schools visited by Aslam (first visit) with Deepika-data check",
         "'In Deepika data' shows Deepika's serial no., block and phone when the school is on her list.",
         T["visited"], C_VISITED),
        ("Sheet 3 – Pending first visit: schools WITH a mobile number",
         "Schools from the official lists in Aslam's areas that he has not visited yet.",
         T["pend_mob"], C_PEND_MOB),
        ("Sheet 4 – Pending first visit: schools WITHOUT a mobile number",
         "Only a landline or no number is available – plan a direct visit.", T["pend_nomob"], C_PEND_NOMOB),
        ("Sheet 5 – Deepika's data: mobile numbers (Aslam's areas) with visit status",
         f"{s['deepika_mob']} Deepika schools in Aslam's areas have a mobile number; "
         f"{s['deepika_visited']} of them have been visited by the executive.", T["deepika"], C_DEEPIKA),
        ("Sheet 6 – Free stay-pass feedback (Aslam's areas)",
         "Feedback entries matched to schools in Aslam's areas by phone number or school name.",
         T["freepass"], C_FP),
    ]
    for title, note, rows, cols in sheets:
        story += [PageBreak(), Paragraph(title, ST["h1"]), Paragraph(escape(note), ST["note"]), Spacer(1, 4),
                  table(rows, cols)]
    doc.build(story, onFirstPage=footer("Aslam – consolidated report"),
              onLaterPages=footer("Aslam – consolidated report"))


def build_areawise(T, path):
    doc = SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=11 * mm, bottomMargin=12 * mm,
                            title="Aslam School Visit Verification – Area-wise", author="Sales team")
    story = cover(T, "Area-wise")
    for srow in T["summary"]:
        a = srow["Area"]
        if a == "TOTAL":
            continue
        pick = lambda rows: [r for r in rows if r["Area"] == a]
        story += [PageBreak(), Paragraph(f"Area: {a}", ST["h1"]),
                  kpis([(srow["Total schools"], "total schools"),
                        (srow["Visited (unique)"], "visited by Aslam"),
                        (srow["Pending 1st visit"], "pending first visit"),
                        (srow["- with mobile"], "pending, with mobile"),
                        (srow["2nd visit planned"], "second visit planned"),
                        (srow["High / Very High"], "High / Very High")]),
                  Spacer(1, 4),
                  Paragraph(f"Total = {srow['State-syllabus schools']} State-syllabus + "
                            f"{srow['CBSE / ICSE schools']} CBSE/ICSE + {srow[EXTRA]} "
                            "found only in Aslam's log.", ST["note"])]
        parts = [
            ("Second visit schedule", pick(T["second"]), no_area(C_SECOND)),
            ("Schools visited (first visit) – with Deepika-data check", pick(T["visited"]), no_area(C_VISITED)),
            ("Pending first visit – with mobile number", pick(T["pend_mob"]), no_area(C_PEND_MOB)),
            ("Pending first visit – without mobile number", pick(T["pend_nomob"]), no_area(C_PEND_NOMOB)),
            ("Deepika's data – mobile numbers and visit status", pick(T["deepika"]), no_area(C_DEEPIKA)),
            ("Free stay-pass feedback", pick(T["freepass"]), no_area(C_FP)),
        ]
        for title, rows, cols in parts:
            story += [CondPageBreak(40 * mm), Paragraph(f"{title} ({len(rows)})", ST["h2"]), table(rows, cols)]
    doc.build(story, onFirstPage=footer("Aslam – area-wise report"),
              onLaterPages=footer("Aslam – area-wise report"))


if __name__ == "__main__":
    from report_tables import make_tables
    T = make_tables()
    build_consolidated(T, os.path.join(OUT, "Aslam_Consolidated_Report.pdf"))
    build_areawise(T, os.path.join(OUT, "Aslam_Areawise_Report.pdf"))
    print("done")
