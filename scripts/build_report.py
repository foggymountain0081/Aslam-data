"""Build the executive area-wise PDF from data.json (see parse_sources.py)."""
import json, re, sys
from collections import Counter, defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak,
                                KeepTogether, CondPageBreak)
from match import load, deepika_match, phones, norm, fp_text
from areas import MAIN_AREAS, ASSUMED, area_map

REPORT_DATE = "24 September 2026"
# Visit-month check, relative to the report date (Sept 2026).
MONTH_CHECK = {
    "September": ("Sep 2026", "Due now", "due"),
    "October": ("Oct 2026", "Upcoming", "ok"),
    "November": ("Nov 2026", "Upcoming", "ok"),
    "December": ("Dec 2026", "Upcoming", "ok"),
    "January": ("Jan 2027", "Next year", "ok"),
    "May": ("May 2027?", "Verify month", "check"),
}
MONTH_ORDER = ["September", "October", "November", "December", "January", "May"]
# Visited entries whose short name in Aslam's log is the same school as a directory entry.
SAME_SCHOOL = {
    ("Tanur", "ICHS"): "ICH School Tanur",
    ("Tanur", "K P N M P U P School"): "K. P. N. M. U. P. S. Tanur",
    ("Tirur", "NSS English Medium School Thekkumuri"): "N. S. S. E. M. H. S. Tirur",
    ("Kodinhi", "IEC Secondary English Medium School"): "I E C Secondary School Engilsh Medium, Kodinhi",
    ("Kodinhi", "MA Higher Secondary School"): "Madrasathul Anwar Higher Secondary School Kodinhi",
    ("Nariparamba", "Al Bashir English Medium School"): "Al Basheer E. M. School Nariparamba",
    ("Chennara", "VVUO School"): "V. V. U. P. S. Chennara",
}
# Visited entries logged under the wrong locality.
MOVE = {("Tirur", "G.H.S Meenadathur"): "Meenadathur"}
FP_STATUS_ORDER = {"Interested": 0, "Neutral": 1, "Not interested": 2, "": 3}

ACCENT = colors.HexColor("#1F4E79")
GREEN = colors.HexColor("#E2F0D9")
AMBER = colors.HexColor("#FFF2CC")
RED = colors.HexColor("#F8CBAD")
BLUE = colors.HexColor("#DDEBF7")
GREY = colors.HexColor("#F2F2F2")
GRID = colors.HexColor("#BFBFBF")

ss = dict(
    title=ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=ACCENT),
    sub=ParagraphStyle("s", fontName="Helvetica", fontSize=11, leading=15, textColor=colors.HexColor("#404040")),
    h1=ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=colors.white),
    h2=ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=ACCENT, spaceBefore=6,
                      spaceAfter=2),
    body=ParagraphStyle("b", fontName="Helvetica", fontSize=9, leading=12),
    cell=ParagraphStyle("c", fontName="Helvetica", fontSize=7.6, leading=9.2),
    cellb=ParagraphStyle("cb", fontName="Helvetica-Bold", fontSize=7.6, leading=9.2),
    head=ParagraphStyle("hd", fontName="Helvetica-Bold", fontSize=7.6, leading=9.2, textColor=colors.white),
    small=ParagraphStyle("sm", fontName="Helvetica", fontSize=8, leading=10.5, textColor=colors.HexColor("#404040")),
)


def P(text, style="cell"):
    return Paragraph(str(text).replace("&", "&amp;"), ss[style]) if "<" not in str(text) else Paragraph(text, ss[style])


def fmt_phone(p):
    """Unique numbers; an STD code (e.g. 0494) is joined to the landline that follows it."""
    toks = [x for x in re.split(r"[ ,/]+", p or "") if x.isdigit()]
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t.startswith("0") and len(t) <= 4 and i + 1 < len(toks) and len(toks[i + 1]) >= 6:
            t, i = t + "-" + toks[i + 1], i + 1
        if len(t) >= 6 and t not in out:
            out.append(t)
        i += 1
    return ", ".join(out) if out else "—"


def build_rows(d, deep_phone, deep_name):
    amap = area_map()
    areas = {a["area"]: {"sv": list(a["sv"]), "pf": list(a["pf"])} for a in d["aslam"]}
    for (src, name), dst in MOVE.items():
        row = next(r for r in areas[src]["sv"] if r["name"] == name)
        areas[src]["sv"].remove(row)
        row["note"] = f"Logged under {src}; school is in {dst}"
        areas[dst]["sv"].append(row)

    # index every pending (directory) school so visited ones can absorb their duplicate
    pending_by_phone = defaultdict(list)
    for loc, a in areas.items():
        for r in a["pf"]:
            for p in phones(r["phone"]):
                pending_by_phone[p].append((loc, r))

    out = defaultdict(list)   # locality -> rows
    used = set()              # id() of pending rows absorbed into a visited row
    seen_visit_phone = {}
    for loc, a in areas.items():
        for r in a["sv"]:
            ph = phones(r["phone"])
            dup = next((x for p in ph for x in [seen_visit_phone.get(p)] if x), None)
            if dup and dup["locality"] == loc:
                dup["alias"].append(r["name"])
                dup["contact"] += " / " + r["contact"]
                dup["notes"].append("Entered twice in Aslam's log (same phone)")
                continue
            match = None
            for p in ph:
                for (ploc, pr) in pending_by_phone.get(p, []):
                    if not match and ploc != loc:
                        r.setdefault("note", f"Was also listed as pending under {ploc}; merged")
                    match = match or pr
            target = SAME_SCHOOL.get((loc, r["name"]))
            key = norm(r["name"]) + norm(loc)
            for pr in areas[loc]["pf"]:
                if (target and pr["name"] == target) or (not match and norm(pr["name"]) == key):
                    match = pr
            row = dict(locality=loc, name=r["name"], alias=[], board=r["board"], phone=r["phone"],
                       contact=r["contact"], month=r["month"], visited=True, notes=[], fp=None)
            if r.get("note"):
                row["notes"].append(r["note"])
            if match:
                used.add(id(match))
                if norm(match["name"]) != norm(r["name"]):
                    row["alias"].append(r["name"])
                    row["name"] = match["name"]
                if match["board"] != row["board"]:
                    row["notes"].append(f"Board corrected to {match['board']} (was {row['board']} in visit log)")
                    row["board"] = match["board"]
                extra = phones(match["phone"]) - ph
                if extra:
                    row["phone"] = r["phone"] + ", " + match["phone"]
            for p in ph:
                seen_visit_phone[p] = row
            out[loc].append(row)
        for r in a["pf"]:
            if id(r) in used:
                continue
            out[loc].append(dict(locality=loc, name=r["name"], alias=[], board=r["board"], phone=r["phone"],
                                 contact="", month=None, visited=False, notes=[], fp=None))

    # Deepika match
    for loc, rows in out.items():
        for row in rows:
            m = None
            for nm in [row["name"]] + row["alias"]:
                m = m or deepika_match(nm, row["phone"], loc, deep_phone, deep_name)
            row["deepika"] = m

    # Free-pass match: phone first, then locality name inside the free-pass school name
    unplaced = []
    for fp in d["freepass"]:
        if "phone" not in fp:
            continue
        hit = None
        for loc, rows in out.items():
            for row in rows:
                if fp["phone"] in phones(row["phone"]):
                    hit = row
        if not hit:
            txt = fp_text(fp)
            for loc, rows in out.items():
                if re.search(r"\b" + re.escape(loc.lower()) + r"\b", txt):
                    key = norm(re.sub(r"\b" + re.escape(loc.lower()) + r"\b", "", txt))
                    same = [r for r in rows if norm(r["name"]).replace(norm(loc), "").startswith(key[:5])
                            and key[:5]]
                    if same and len(same) == 1:
                        hit = same[0]
                        hit["notes"].append(f"Free-pass entry: '{fp['school']}' ({fp['phone']})")
                    else:
                        hit = dict(locality=loc, name=fp["school"], alias=[], board="Govt", phone=fp["phone"],
                                   contact=fp["person"], month=None, visited=False, deepika=None, fp=None,
                                   notes=["New school - found only in the free-pass log"])
                        hit["deepika"] = deepika_match(hit["name"], hit["phone"], loc, deep_phone, deep_name)
                        rows.append(hit)
                    break
        exec_ = fp["tail"].split()[0] if fp["tail"] else ""
        if hit:
            hit["fp"] = fp
            if exec_.lower() in ("aslam", "azlam") and not hit["visited"]:
                hit["visited"] = True
                hit["notes"].append("Visited by Aslam (free-pass log), no 2nd-visit month yet")
        elif re.search(r"\b(aslam|azlam)\b", fp["tail"], re.I):
            unplaced.append(fp)
    return out, unplaced, amap


def status_cells(row):
    # Visited
    if row["visited"]:
        visited = P("<b>Yes</b>")
    else:
        visited = P("No")
    # Confirmed 2nd visit
    if row["month"]:
        when, tag, _ = MONTH_CHECK[row["month"]]
        confirmed = P(f"<b>{when}</b><br/>{tag}")
    elif row["visited"]:
        confirmed = P("Not fixed")
    else:
        confirmed = P("Pending 1st visit")
    dp = row["deepika"]
    deep = P(f"<b>Yes</b><br/>{dp['block']}" if dp and dp["block"] else ("<b>Yes</b>" if dp else "No"))
    fp = row["fp"]
    if fp:
        fpv = P(f"<b>Yes</b><br/>{fp['visit_date'] or fp['date']}")
        st = fp["status"] or "Not recorded"
        tour = f"<br/>Tour: {fp['tour']}" if fp["tour"] else ""
        fps = P(f"<b>{st}</b>{tour}")
    else:
        fpv, fps = P("No"), P("—")
    return visited, confirmed, deep, fpv, fps


def row_colour(row):
    if row["fp"] and row["fp"]["status"] == "Not interested":
        return RED
    if row["month"]:
        return AMBER if MONTH_CHECK[row["month"]][2] != "ok" else GREEN
    if row["visited"]:
        return BLUE
    return None


COLS = [("#", 7), ("School name", 70), ("Board", 13), ("Phone", 30), ("Visited\n(Aslam)", 16),
        ("Confirmed\n2nd visit", 24), ("In Deepika\ndata", 20), ("Free pass\nvisited", 19),
        ("Free pass status", 30), ("Contact / notes", 48)]


def locality_table(rows):
    data = [[P(c.replace("\n", "<br/>"), "head") for c, _ in COLS]]
    styles = [("BACKGROUND", (0, 0), (-1, 0), ACCENT), ("GRID", (0, 0), (-1, -1), 0.4, GRID),
              ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 3),
              ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for i, row in enumerate(rows, 1):
        name = row["name"] + (f" <font color='#595959'>(logged as: {', '.join(row['alias'])})</font>"
                              if row["alias"] else "")
        notes = "; ".join(([row["contact"]] if row["contact"] else []) + row["notes"])
        data.append([P(i), P(name, "cellb" if row["visited"] else "cell"), P(row["board"]),
                     P(fmt_phone(row["phone"])), *status_cells(row), P(notes)])
        c = row_colour(row)
        if c:
            styles.append(("BACKGROUND", (0, i), (-1, i), c))
    t = Table(data, colWidths=[w * mm for _, w in COLS], repeatRows=1)
    t.setStyle(TableStyle(styles))
    return t


def sort_rows(rows):
    return sorted(rows, key=lambda r: (not r["visited"] and not r["fp"], not r["visited"],
                                       MONTH_ORDER.index(r["month"]) if r["month"] else 9,
                                       r["board"] != "CBSE", r["name"].lower()))


def area_stats(rows):
    return dict(total=len(rows), visited=sum(r["visited"] for r in rows),
                confirmed=sum(bool(r["month"]) for r in rows),
                pending=sum(not r["visited"] for r in rows),
                deepika=sum(bool(r["deepika"]) for r in rows),
                fp=sum(bool(r["fp"]) for r in rows),
                cbse=sum(r["board"] == "CBSE" for r in rows))


def summary_table(header, body_rows, widths, total=None, pad=2.5):
    data = [[P(h, "head") for h in header]] + [[P(c) for c in r] for r in body_rows]
    if total:
        data.append([P(f"<b>{c}</b>") for c in total])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), ACCENT), ("GRID", (0, 0), (-1, -1), 0.4, GRID),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), pad),
          ("BOTTOMPADDING", (0, 0), (-1, -1), pad)]
    for i in range(1, len(data)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), GREY))
    if total:
        st.append(("BACKGROUND", (0, len(data) - 1), (-1, len(data) - 1), BLUE))
    t.setStyle(TableStyle(st))
    return t


def banner(text):
    t = Table([[Paragraph(text, ss["h1"])]], colWidths=[277 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT), ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    return t


def legend():
    items = [(GREEN, "2nd visit confirmed (Oct 2026 - Jan 2027)"), (AMBER, "2nd visit month due now / needs checking"),
             (BLUE, "Visited, 2nd visit month not fixed"), (RED, "Free pass: not interested"),
             (colors.white, "Pending first visit")]
    cells = []
    for c, label in items:
        cells += ["", P(label, "small")]
    t = Table([cells], colWidths=[5 * mm, 50 * mm] * len(items))
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, (c, _) in enumerate(items):
        st += [("BACKGROUND", (2 * i, 0), (2 * i, 0), c), ("BOX", (2 * i, 0), (2 * i, 0), 0.4, GRID)]
    t.setStyle(TableStyle(st))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#595959"))
    canvas.drawString(10 * mm, 7 * mm, "Aslam - Area-wise School Coverage (vs Deepika's data & Free-pass log)  |  "
                                       f"Prepared {REPORT_DATE}  |  For marketing executives")
    canvas.drawRightString(287 * mm, 7 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build(data_path, out_path):
    d, deep_phone, deep_name = load(data_path)
    rows_by_loc, unplaced, amap = build_rows(d, deep_phone, deep_name)
    all_rows = [r for rows in rows_by_loc.values() for r in rows]
    tot = area_stats(all_rows)

    story = []
    story += [Paragraph("Aslam - Area-wise School Coverage Report", ss["title"]), Spacer(1, 3),
              Paragraph("Aslam's school visits compared with <b>Deepika's Malappuram data</b> and the "
                        "<b>Free-pass feedback log</b>. Only the 133 localities Aslam covers are included, "
                        f"grouped into {len(MAIN_AREAS)} main areas. Prepared {REPORT_DATE}.", ss["sub"]),
              Spacer(1, 8)]
    kpis = [(tot["total"], "Schools in Aslam's areas"), (tot["visited"], "Visited by Aslam"),
            (tot["confirmed"], "2nd visit month confirmed"), (tot["pending"], "Pending 1st visit"),
            (tot["deepika"], "Also in Deepika's data"), (tot["total"] - tot["deepika"], "Not in Deepika's data"),
            (tot["fp"], "Used a free pass")]
    k = Table([[Paragraph(f"<b>{v}</b>", ParagraphStyle("k", fontName="Helvetica-Bold", fontSize=18, leading=22)) for v, _ in kpis],
               [P(l, "small") for _, l in kpis]], colWidths=[39.5 * mm] * len(kpis))
    k.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BLUE), ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                           ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white), ("TOPPADDING", (0, 0), (-1, 0), 8),
                           ("BOTTOMPADDING", (0, 1), (-1, 1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
    story += [k, Spacer(1, 10)]

    # Main-area summary
    story.append(Paragraph("1. Main-area summary", ss["h2"]))
    body = []
    for main, locs in MAIN_AREAS.items():
        s = area_stats([r for l in locs for r in rows_by_loc[l]])
        body.append([f"<b>{main}</b>", len(locs), s["total"], s["visited"], s["confirmed"], s["pending"],
                     s["deepika"], s["total"] - s["deepika"], s["fp"], s["cbse"]])
    story.append(summary_table(["Main area", "Localities", "Schools", "Visited", "2nd visit confirmed",
                                "Pending 1st visit", "In Deepika", "Not in Deepika", "Free pass used", "CBSE"],
                               body, [62, 22, 22, 22, 30, 28, 24, 26, 26, 17],
                               ["Total", len(amap), tot["total"], tot["visited"], tot["confirmed"], tot["pending"],
                                tot["deepika"], tot["total"] - tot["deepika"], tot["fp"], tot["cbse"]]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<b>How to read this report:</b> each main area lists its localities; each locality has one table. "
        "<b>Visited</b> = Aslam has met the school. <b>Confirmed 2nd visit</b> = the follow-up month agreed with the "
        "school, checked against today's date. <b>In Deepika data</b> = the school also appears in Deepika's Malappuram "
        "sheet (block shown). <b>Free pass</b> columns come from the free-pass feedback log (date the pass was used "
        "and the final status). Visited schools are listed first and in bold.", ss["body"]))
    story.append(Spacer(1, 5))
    story.append(legend())

    # Month-wise 2nd visit plan
    story.append(PageBreak())
    story.append(Paragraph("2. Second-visit plan by month (with month check)", ss["h2"]))
    by_month = defaultdict(list)
    for r in all_rows:
        if r["month"]:
            by_month[r["month"]].append(r)
    mbody = []
    for m in MONTH_ORDER:
        for r in sorted(by_month[m], key=lambda r: (amap[r["locality"]], r["locality"])):
            when, tag, _ = MONTH_CHECK[m]
            mbody.append([f"<b>{when}</b>", tag, amap[r["locality"]], r["locality"], r["name"], r["board"],
                          fmt_phone(r["phone"]), r["contact"],
                          "Yes" if r["deepika"] else "No", (r["fp"]["status"] or "Visited") if r["fp"] else "—"])
    story.append(summary_table(["Month", "Check", "Main area", "Locality", "School", "Board", "Phone",
                                "Contact", "In Deepika", "Free pass"], mbody,
                               [18, 20, 34, 28, 58, 12, 32, 38, 17, 20], pad=1.2))
    cnt = Counter(r["month"] for r in all_rows if r["month"])
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Month check (as of %s): %s. <b>September</b> visits are due now - complete them before 30 Sep or "
        "re-schedule. <b>January</b> is taken as Jan 2027. <b>May</b> (Anganwadi, Edayathuparamba) is 8 months away "
        "and outside the usual tour season - please re-confirm with the contact." % (
            REPORT_DATE, ", ".join(f"{MONTH_CHECK[m][0]}: {cnt[m]}" for m in MONTH_ORDER if cnt[m])), ss["small"]))

    # Area-wise detail
    for main, locs in MAIN_AREAS.items():
        story.append(PageBreak())
        s = area_stats([r for l in locs for r in rows_by_loc[l]])
        story.append(banner(f"{main}  -  {len(locs)} localities, {s['total']} schools  |  visited {s['visited']}  |  "
                            f"2nd visit confirmed {s['confirmed']}  |  pending {s['pending']}"))
        story.append(Spacer(1, 4))
        for loc in sorted(locs):
            rows = sort_rows(rows_by_loc[loc])
            ls = area_stats(rows)
            head = Paragraph(f"{loc}{' *' if loc in ASSUMED else ''}  <font size=8 color='#595959'>"
                             f"- {ls['total']} school{'s' if ls['total'] != 1 else ''}: {ls['visited']} visited, {ls['confirmed']} 2nd visit "
                             f"confirmed, {ls['pending']} pending 1st visit, {ls['deepika']} in Deepika data"
                             f"{', ' + str(ls['fp']) + ' free pass' if ls['fp'] else ''}</font>", ss["h2"])
            story.append(CondPageBreak(30 * mm))
            if len(rows) <= 10:
                story.append(KeepTogether([head, locality_table(rows)]))
            else:
                story += [head, locality_table(rows)]

    # Notes / data checks
    story.append(PageBreak())
    story.append(Paragraph("3. Data checks and corrections made while comparing", ss["h2"]))
    notes = []
    for r in all_rows:
        for n in r["notes"]:
            if not n.startswith("Free-pass entry"):
                notes.append([r["locality"], r["name"], n])
    story.append(summary_table(["Locality", "School", "Check / correction"], notes, [40, 90, 147]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Free-pass visits that fall inside Aslam's localities", ss["h2"]))
    fprows = sorted((r for r in all_rows if r["fp"]), key=lambda r: FP_STATUS_ORDER[r["fp"]["status"]])
    story.append(summary_table(
        ["Locality", "School (as in this report)", "Free-pass entry", "Pass used on", "Persons", "Executive",
         "Status", "Tour period"],
        [[r["locality"], r["name"], r["fp"]["school"], r["fp"]["visit_date"], r["fp"]["persons"],
          (r["fp"]["tail"].split() or ["—"])[0], r["fp"]["status"] or "Not recorded", r["fp"]["tour"] or "—"]
         for r in fprows], [30, 55, 55, 24, 16, 26, 30, 41]))
    story.append(Spacer(1, 6))
    if unplaced:
        story.append(Paragraph("Free-pass visits by Aslam whose school is not in any of his listed localities",
                               ss["h2"]))
        story.append(summary_table(["Pass used on", "School", "Contact", "Phone", "Persons", "Status"],
                                   [[f["visit_date"], f["school"], f["person"], f["phone"], f["persons"],
                                     f["status"] or "—"] for f in unplaced], [30, 90, 50, 40, 25, 42]))
        story.append(Spacer(1, 6))
    story.append(Paragraph((
        "<b>Matching method:</b> a school is marked <i>In Deepika data</i> when its phone number, or its name "
        "(ignoring dots and spaces), matches a row in Deepika's Malappuram sheet (1,579 schools). Free-pass entries "
        "are matched by phone number, or by the locality name inside the school name. Only %d of the %d free-pass "
        "entries relate to Aslam's localities - most free-pass guests are from Kozhikode, Palakkad, Kasaragod and "
        "other districts. CBSE schools are not part of Deepika's (State-syllabus) sheet, so they show <i>No</i>.<br/>"
        "<b>* Localities marked with an asterisk</b> have no block in Deepika's data; their main area was assigned "
        "by location - please confirm: " + ", ".join(sorted(ASSUMED)) + ".") % (
            tot["fp"] + len(unplaced), sum("phone" in f for f in d["freepass"])), ss["small"]))

    doc = SimpleDocTemplate(out_path, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=10 * mm, bottomMargin=12 * mm,
                            title="Aslam - Area-wise School Coverage Report", author="Marketing")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return tot


if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2]))
