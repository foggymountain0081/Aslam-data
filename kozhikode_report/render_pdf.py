"""Render the PDF report.  Usage: python3 render_pdf.py model.json out.pdf"""
import json, sys
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
                                KeepTogether, CondPageBreak)
import tables
from mapping import AREAS

pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

T = tables.build(json.load(open(sys.argv[1])))
OUT = sys.argv[2]

INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#5f6b7a")
ACCENT = colors.HexColor("#1d4e89")
LINE = colors.HexColor("#d5dbe3")
HEAD_BG = colors.HexColor("#e8eef6")
ZEBRA = colors.HexColor("#f6f8fb")
PROB_COL = {"Very high": "#0b6e4f", "High": "#2a8a4a", "Medium": "#9a6a00", "Low": "#8a4b2a",
            "Awaiting follow-up": "#5f6b7a", "Invalid number": "#b3261e", "Not interested": "#b3261e"}

st = dict(
    h1=ParagraphStyle("h1", fontName="DVB", fontSize=20, leading=24, textColor=ACCENT, spaceAfter=4),
    sub=ParagraphStyle("sub", fontName="DV", fontSize=10, leading=13, textColor=MUTED),
    h2=ParagraphStyle("h2", fontName="DVB", fontSize=14, leading=18, textColor=ACCENT, spaceBefore=6, spaceAfter=4),
    h3=ParagraphStyle("h3", fontName="DVB", fontSize=10.5, leading=14, textColor=INK, spaceBefore=8, spaceAfter=3),
    body=ParagraphStyle("body", fontName="DV", fontSize=8.6, leading=11.5, textColor=INK, spaceAfter=4),
    note=ParagraphStyle("note", fontName="DV", fontSize=7.6, leading=10, textColor=MUTED, spaceAfter=3),
    cell=ParagraphStyle("cell", fontName="DV", fontSize=6.7, leading=8.2, textColor=INK),
    cellb=ParagraphStyle("cellb", fontName="DVB", fontSize=6.7, leading=8.2, textColor=INK),
    head=ParagraphStyle("head", fontName="DVB", fontSize=6.8, leading=8.2, textColor=INK),
    big=ParagraphStyle("big", fontName="DVB", fontSize=17, leading=20, textColor=ACCENT, alignment=1),
    bigl=ParagraphStyle("bigl", fontName="DV", fontSize=7.4, leading=9, textColor=MUTED, alignment=1),
)


def P(txt, style="cell"):
    return Paragraph(txt if isinstance(txt, str) and txt.startswith("<") else escape(str(txt or "")), st[style])


def prob(p):
    if not p:
        return P("")
    return Paragraph(f'<font color="{PROB_COL.get(p, "#1f2933")}"><b>{escape(p)}</b></font>', st["cell"])


def table(head, rows, widths, repeat=1):
    data = [[P(h, "head") for h in head]] + rows
    t = Table(data, colWidths=widths, repeatRows=repeat)
    style = [("GRID", (0, 0), (-1, -1), 0.3, LINE), ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
             ("RIGHTPADDING", (0, 0), (-1, -1), 2.5), ("TOPPADDING", (0, 0), (-1, -1), 1.6),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6)]
    for i in range(2, len(data), 2):
        style.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(style))
    return t


def lines(xs):
    return P("<br/>".join(escape(x) for x in xs) if xs else "-") if True else None


def P_lines(xs):
    return Paragraph("<br/>".join(escape(x) for x in xs) if xs else "-", st["cell"])


def name_cell(r):
    loc = r.get("locality") or ""
    extra = f'<br/><font color="#5f6b7a">{escape(loc)}</font>' if loc and loc.lower()[:5] not in r["name"].lower() else ""
    return Paragraph(f"<b>{escape(r['name'])}</b>{extra}", st["cell"])


# ---------------------------------------------------------------- sheets
def visited_table(rows, with_area=False):
    head = ["#"] + (["Area"] if with_area else []) + ["School / locality", "Type", "1st visit", "Contact person - number",
                                                      "Str.", "Latest follow-up (call -> 2nd remark)", "Tour time",
                                                      "2nd visit month", "In Deepika list", "Confirmation probability"]
    w = [16] + ([52] if with_area else []) + [140, 38, 44, 138, 26, 158, 42, 56, 38, 58]
    if with_area:
        w[7] = 110
    data = []
    for i, r in enumerate(rows, 1):
        data.append([P(i)] + ([P(r["area"])] if with_area else []) + [
            name_cell(r), P(r["type"]), P(r["date"] + ("" if r["executive"] == "Arshad" else f' ({r["executive"]})')),
            P_lines(r["contacts"]), P(r["strength"]), P(r["remark"] + (f' | Free-pass: {r["feedback"]}' if r["feedback"] else "")),
            P(r["tour"]), P(r["second"] or "Not fixed"), P(r["in_deepika"]), prob(r["prob"])])
    return table(head, data, w)


def pending_table(rows, with_area=False, no_mobile=False):
    if no_mobile:
        head = ["#"] + (["Area"] if with_area else []) + ["School", "Type", "Classes", "Landline / other number",
                                                          "Source list", "In Deepika list"]
        w = [16] + ([66] if with_area else []) + [300, 60, 50, 170, 100, 50]
    else:
        head = ["#"] + (["Area"] if with_area else []) + ["School", "Type", "Classes", "Mobile number(s)",
                                                          "Other numbers", "Source list", "In Deepika list", "Note"]
        w = [16] + ([66] if with_area else []) + [220, 52, 40, 120, 110, 80, 44, 96]
        if with_area:
            w[-1] = 30
    data = []
    for i, r in enumerate(rows, 1):
        row = [P(i)] + ([P(r["area"])] if with_area else []) + [P(f"<b>{escape(r['name'])}</b>"), P(r["type"]), P(r["level"])]
        if no_mobile:
            row += [P_lines(r["landlines"] or ["No number in any list"]), P(r["source"]), P(r["in_deepika"])]
        else:
            row += [P_lines(r["mobiles"]), P_lines(r["landlines"] or ["-"]), P(r["source"]), P(r["in_deepika"]),
                    P(("Free-pass: " + r["feedback"]) if r["feedback"] else "")]
        data.append(row)
    return table(head, data, w)


def plan_table(rows):
    head = ["#", "Area", "School / locality", "Contact person - number", "Tour time", "2nd visit (as logged)",
            "Probability", "Latest follow-up"]
    w = [16, 66, 150, 150, 46, 76, 58, 194]
    data = [[P(i), P(r["area"]), name_cell(r), P_lines(r["contacts"]), P(r["tour"]), P(r["second"] or "Not fixed"),
             prob(r["prob"]), P(r["remark"])] for i, r in enumerate(rows, 1)]
    return table(head, data, w)


def summary_table():
    head = ["Area", "Schools in area", "1st visit done", "1st visit pending", "Pending - with mobile",
            "Pending - no mobile", "2nd visit month fixed", "Visited & in Deepika list", "Very high", "High",
            "Medium", "Low", "Awaiting follow-up", "Not int. / wrong no."]
    w = [74, 44, 44, 46, 50, 48, 50, 54, 38, 36, 40, 36, 52, 52]
    data = []
    for r in T["summary"]:
        data.append([P(f"<b>{r['area']}</b>")] + [P(x) for x in (
            r["total"], r["visited"], r["pending"], r["pending_mobile"], r["pending_no_mobile"], r["second_planned"],
            f'{r["visited_in_deepika"]} of {r["visited"]}', r["p_Very high"], r["p_High"], r["p_Medium"], r["p_Low"],
            r["p_Awaiting follow-up"], r["p_Not interested"] + r["p_Invalid number"])])
    tt = T["totals"]
    pc = tt["prob"]
    data.append([P("<b>Total</b>")] + [P(f"<b>{x}</b>") for x in (
        tt["schools"], tt["visited"], tt["pending"], tt["pending_mobile"], tt["pending_no_mobile"], tt["second_planned"],
        f'{tt["visited_in_deepika"]} of {tt["visited"]}', pc["Very high"], pc["High"], pc["Medium"], pc["Low"],
        pc["Awaiting follow-up"], pc["Not interested"] + pc["Invalid number"])])
    t = table(head, data, w)
    t.setStyle(TableStyle([("BACKGROUND", (0, len(data)), (-1, len(data)), HEAD_BG)]))
    return t


def kpis():
    tt = T["totals"]
    items = [(tt["schools"], "schools in Arshad's areas"), (tt["visited"], "first visit done"),
             (tt["pending"], "first visit pending"), (tt["second_planned"], "2nd visit month fixed"),
             (tt["prob"]["Very high"] + tt["prob"]["High"], "very high / high probability"),
             (tt["deepika_mobiles"], "Deepika mobile numbers in area")]
    cells = [[Paragraph(str(v), st["big"]) for v, _ in items], [Paragraph(l, st["bigl"]) for _, l in items]]
    t = Table(cells, colWidths=[128] * 6)
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.4, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f6fa")),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def deepika_mobile_table(rows):
    head = ["#", "Area", "Deepika no.", "School (as in Deepika's list)", "Block", "Type", "Deepika mobile",
            "Visited?", "Visit", "Executive's contact(s)", "Number check", "Probability"]
    w = [16, 66, 40, 146, 62, 50, 54, 44, 66, 130, 50, 56]
    data = [[P(i), P(r["area"]), P(r["sno"]), P(f"<b>{escape(r['name'])}</b>"), P(r["block"]), P(r["finance"]),
             P(f"<b>{r['mobile']}</b>"), P(r["visited"]), P(r["visit"]), P_lines(r["exec_contacts"]), P(r["same"]),
             prob(r["prob"]) if r["prob"] != "-" else P("-")] for i, r in enumerate(rows, 1)]
    return table(head, data, w)


def deepika_check_table(rows):
    head = ["#", "Area", "School visited (directory name)", "Visit place", "1st visit", "Present in Deepika's list?",
            "Deepika's phone", "Executive's contact(s)", "Probability"]
    w = [16, 66, 190, 72, 44, 58, 60, 206, 66]
    data = [[P(i), P(r["area"]), P(f"<b>{escape(r['name'])}</b>"), P(r["locality"]), P(r["date"]),
             Paragraph(f'<b>{r["in_deepika"]}</b>', st["cell"]), P(r["deepika_phone"] or "-"),
             P_lines(r["contacts"]), prob(r["prob"])] for i, r in enumerate(rows, 1)]
    return table(head, data, w)


def feedback_table(rows):
    head = ["#", "Area", "School (matched)", "Person - phone", "Free-pass date / persons", "Executive",
            "Park opinion", "Used glamping stay? / stay opinion", "Feedback", "Tour period", "Final status",
            "Arshad visited?", "Confirmation probability"]
    w = [16, 52, 110, 80, 60, 42, 70, 70, 60, 40, 44, 60, 60]
    data = [[P(i), P(r["area"]), P(f"<b>{escape(r['school'])}</b><br/>({escape(r['fb_school'])})"),
             P(f'{r["person"]} - {r["phone"]}'), P(f'{r["park"]} / {r["persons"]}'), P(r["executive"]),
             P(r["park_opinion"]), P(f'{r["glamping"]} / {r["stay"]}'), P(r["feedback"]), P(r["period"]),
             P(r["status"]), P(r["visited"]), prob(r["prob"]) if r["prob"] in PROB_COL else P(r["prob"])]
            for i, r in enumerate(rows, 1)]
    return table(head, data, w)


# ---------------------------------------------------------------- story
story = []
story += [Paragraph("School Visit &amp; Coverage Report - Kozhikode", st["h1"]),
          Paragraph("Executive: <b>Arshad</b> &nbsp;|&nbsp; Visits logged 13 Aug - 24 Sep 2026 &nbsp;|&nbsp; "
                    f"Report date {tables.TODAY}", st["sub"]), Spacer(1, 8), kpis(), Spacer(1, 8)]
story.append(Paragraph(
    "This report compares Arshad's visit log with every other list supplied - Deepika's Kozhikode school list, the "
    "Kozhikode School Data (state-syllabus master list), the CBSE and ICSE school lists and the free-pass feedback "
    "sheet. It covers <b>only the areas Arshad works in</b>: Kozhikode South, Kozhikode North and Beypore constituencies "
    "in full, and the parts of Elathur and Kunnamangalam constituencies on his route. For each area it shows the "
    "total schools with contact numbers, first visits done and still pending, second visits by month, whether each "
    "school is in Deepika's list, the confirmation probability and the free-pass feedback.", st["body"]))
story += [Paragraph("Area summary", st["h3"]), summary_table(), Spacer(1, 4),
          Paragraph("'Schools in area' = schools found in any of the lists (state-syllabus, Deepika, CBSE, ICSE) plus "
                    "schools, anganwadis, colleges and tuition centres that appear only in Arshad's log. A school with several "
                    "sections (LP / UP / HS / HSS) listed as one institution in the directories is counted once; Arshad's "
                    f"{T['totals']['units']} visited units ({T['totals']['visit_rows']} contact rows) collapse to "
                    f"{T['totals']['visited']} schools. Elathur and Kunnamangalam constituencies have "
                    f"{T['outside_route'].get('Elathur', 0)} and {T['outside_route'].get('Kunnamangalam', 0)} more "
                    "state-syllabus schools outside Arshad's route (Kakkodi, Chelannur, Nanminda, Mavoor, Kunnamangalam town, "
                    "etc. - Basheer's rural beat); they are not counted as pending here.", st["note"])]

story.append(Paragraph("How confirmation probability is decided", st["h3"]))
story.append(table(["Level", "Rule (from the call remarks, 2nd remarks and free-pass feedback)"], [
    [prob("Very high"), P("School said 'almost confirmed', a visit/date is booked, or 'trip almost confirmed'.")],
    [prob("High"), P("Tour month given AND details shared on WhatsApp, or the school's free-pass feedback says Interested.")],
    [prob("Medium"), P("Tour month given, or 'will confirm after visit / meeting', 'discussing', details shared without a month.")],
    [prob("Low"), P("Only 'call not answered / busy / waiting / not confirmed / not decided' so far.")],
    [prob("Awaiting follow-up"), P("Visited (mostly on 24.09) but no follow-up call recorded yet.")],
    [prob("Invalid number"), P("Wrong / invalid number recorded - use the directory number shown in the pending/ Deepika sheets.")],
    [prob("Not interested"), P("School said not interested (or staff trip already done). The latest remark wins.")]],
    [90, 690]))

story.append(PageBreak())
story.append(Paragraph("1. Second visits by month (all areas)", st["h2"]))
story.append(Paragraph("Month as written in Arshad's 'Second Visit' column (earliest month used where a school has two). "
                       f"September items are due now - today is {tables.TODAY}.", st["note"]))
for m, rows in T["plan"].items():
    story += [CondPageBreak(60), Paragraph(f"{m} - {len(rows)} schools", st["h3"]), plan_table(rows)]
story += [CondPageBreak(60), Paragraph(f"Visited, still interested, but no 2nd-visit month fixed yet - {len(T['unplanned'])} schools", st["h3"]),
          Paragraph("Visits from 17.09 onward have no 2nd-visit month in the log yet; the tour time the school gave is shown so the month can be fixed.", st["note"]),
          plan_table(T["unplanned"])]

story.append(PageBreak())
story.append(Paragraph("2. Pending first visits (not yet covered) - with mobile numbers", st["h2"]))
story.append(Paragraph("Schools in Arshad's areas that are in the directories but not yet in his visit log, with at least one "
                       "mobile number from the state-syllabus list, Deepika's list or the CBSE/ICSE list.", st["note"]))
rows = [r for a in AREAS for r in T["pending_mobile"][a]]
story.append(pending_table(rows, with_area=True))

story.append(PageBreak())
story.append(Paragraph("3. Pending first visits - NO mobile number available (separate list)", st["h2"]))
story.append(Paragraph("These schools have only a landline (or no number at all) in every list, so they need a direct "
                       "visit or a landline call to collect a coordinator's mobile.", st["note"]))
rows = [r for a in AREAS for r in T["pending_nomobile"][a]]
story.append(pending_table(rows, with_area=True, no_mobile=True))

story.append(PageBreak())
story.append(Paragraph("4. Deepika's data - mobile numbers sheet (Arshad's areas only)", st["h2"]))
tt = T["totals"]
story.append(Paragraph(
    f"Deepika's list has {tt['deepika_in_area']} schools inside Arshad's areas; {tt['deepika_mobiles']} of them carry a "
    f"mobile number (the rest are landlines or blank). {tt['deepika_mobiles_visited']} of these have been visited by an "
    "executive; the rest are listed first in each area. 'Number check' compares Deepika's mobile with the number the "
    "executive collected.", st["note"]))
story.append(deepika_mobile_table(T["deepika_mobile"]))

story.append(PageBreak())
story.append(Paragraph("5. Is each visited school in Deepika's list?", st["h2"]))
story.append(Paragraph(
    f"{tt['visited_in_deepika']} of {tt['visited']} visited schools are in Deepika's list. Those marked <b>No</b> are listed "
    "first in each area - mostly unaided English-medium, CBSE/ICSE schools, anganwadis, colleges and tuition centres, "
    "which Deepika's (state-syllabus) list does not cover.", st["note"]))
story.append(deepika_check_table(T["deepika_check"]))

story.append(PageBreak())
story.append(Paragraph("6. Free-pass / stay feedback - Arshad's areas only", st["h2"]))
story.append(Paragraph(
    f"Of {tt['feedback_total']} feedback entries, {tt['feedback_in_area']} belong to schools in Arshad's areas (matched by "
    "phone number and school name). The others are Malappuram, Palakkad, Kasaragod, Wayanad and rural Kozhikode schools.", st["note"]))
story.append(feedback_table(T["feedback"]))

# ---------------------------------------------------------------- area-wise
for ai, a in enumerate(AREAS):
    story.append(PageBreak())
    r = next(x for x in T["summary"] if x["area"] == a)
    story.append(Paragraph(f"Area {ai + 1}: {a}", st["h2"]))
    extra = (f" Another {r['outside_route']} state-syllabus schools in this constituency are outside Arshad's route and not counted."
             if r["outside_route"] else "")
    story.append(Paragraph(
        f"<b>{r['total']}</b> schools &nbsp;|&nbsp; first visit done <b>{r['visited']}</b> &nbsp;|&nbsp; pending <b>{r['pending']}</b> "
        f"({r['pending_mobile']} with mobile, {r['pending_no_mobile']} without) &nbsp;|&nbsp; 2nd visit month fixed "
        f"<b>{r['second_planned']}</b> &nbsp;|&nbsp; in Deepika's list: {r['deepika_in_area']} ({r['deepika_mobiles']} with mobile) "
        f"&nbsp;|&nbsp; probability - very high {r['p_Very high']}, high {r['p_High']}, medium {r['p_Medium']}, low {r['p_Low']}, "
        f"awaiting follow-up {r['p_Awaiting follow-up']}, not interested / wrong no. {r['p_Not interested'] + r['p_Invalid number']}.{extra}",
        st["body"]))
    story += [Paragraph(f"{a} - first visit done ({r['visited']})", st["h3"]), visited_table(T["visited"][a])]
    sec = [x for m, rows in T["plan"].items() for x in rows if x["area"] == a]
    if sec:
        story += [CondPageBreak(60), Paragraph(f"{a} - second visits by month ({len(sec)})", st["h3"]), plan_table(sec)]
    if T["pending_mobile"][a]:
        story += [CondPageBreak(60), Paragraph(f"{a} - pending first visit, with mobile ({len(T['pending_mobile'][a])})", st["h3"]),
                  pending_table(T["pending_mobile"][a])]
    if T["pending_nomobile"][a]:
        story += [CondPageBreak(60), Paragraph(f"{a} - pending first visit, NO mobile ({len(T['pending_nomobile'][a])})", st["h3"]),
                  pending_table(T["pending_nomobile"][a], no_mobile=True)]
    dm = [x for x in T["deepika_mobile"] if x["area"] == a]
    if dm:
        story += [CondPageBreak(60), Paragraph(f"{a} - Deepika's mobile numbers ({len(dm)})", st["h3"]), deepika_mobile_table(dm)]
    fb = [x for x in T["feedback"] if x["area"] == a]
    if fb:
        story += [CondPageBreak(60), Paragraph(f"{a} - free-pass feedback ({len(fb)})", st["h3"]), feedback_table(fb)]

# ---------------------------------------------------------------- notes
story.append(PageBreak())
story.append(Paragraph("Method and data notes", st["h2"]))
for n in tables.NOTES:
    story.append(Paragraph(n, st["body"]))


def on_page(c, doc):
    c.saveState()
    c.setFont("DV", 7)
    c.setFillColor(MUTED)
    c.drawString(28, 16, "Kozhikode School Visit & Coverage Report - Arshad")
    c.drawRightString(landscape(A4)[0] - 28, 16, f"Page {doc.page}")
    c.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=26, bottomMargin=28,
                        title="Kozhikode School Visit & Coverage Report - Arshad", author="Compiled from executive visit logs")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
