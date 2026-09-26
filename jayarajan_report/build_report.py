"""Build the Jayarajan area summary report (HTML + PDF).

Figures are extracted from Jayarajan_Data.pdf (Kozhikode, visits 13.08.2026 - 24.09.2026).
"""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

OUT = Path(__file__).parent

# area, schools in Deepika list, visited by Jayarajan, visited & not in Deepika list,
# covered by free pass (other exec), pending 1st visit, pending with mobile,
# 2nd visit month fixed, visited with mobile, free passes issued in area
AREAS = [
    ("Koduvally",              97, 22, 3,  3, 76, 24, 14, 21, 5),
    ("Kunnamangalam",         113,  4, 0,  3, 106, 49, 2,  3, 3),
    ("Balussery",             106, 30, 2, 10, 71, 32, 13, 28, 10),
    ("Perambra",               81, 38, 6,  1, 50, 18, 21, 37, 2),
    ("Melady",                 47, 11, 2,  0, 39, 20, 2, 11, 0),
    ("Panthalayani",           48,  4, 0,  0, 44, 14, 2,  4, 0),
    ("Koyilandy Municipality", 47,  3, 0,  0, 44, 15, 0,  3, 0),
    ("Kunnummal",              75, 25, 2,  0, 53, 30, 14, 25, 0),
    ("Thodannur",              86,  5, 0,  1, 80, 52, 3,  5, 1),
    ("Tuneri",                100, 10, 3,  0, 93, 58, 3, 10, 0),
]

rows = []
for a, total, vis, notlist, fp, pend, pend_mob, second, vis_mob, passes in AREAS:
    with_mob = vis_mob + fp + pend_mob          # every free-pass school has a mobile
    without_mob = (vis - vis_mob) + (pend - pend_mob)
    rows.append([a, total, vis, fp, pend, second, with_mob, without_mob, passes, vis - notlist])

tot = [sum(r[i] for r in rows) for i in range(1, 10)]
T = dict(zip(["total", "visited", "fp", "pending", "second", "with_mob", "without_mob",
              "passes", "matched"], tot))
assert T == dict(total=800, visited=152, fp=18, pending=656, second=74, with_mob=477,
                 without_mob=349, passes=21, matched=134), T

KPIS = [
    ("Total schools in Jayarajan's areas", "800", "As per Deepika's school list (10 main areas). 18 more schools were visited that are not in her list."),
    ("Total schools covered", "152", "Visited by Jayarajan / Amal (13.08 - 24.09.2026). Another 18 schools were covered by other executives through the free stay pass."),
    ("Total schools not yet covered", "656", "Pending first visit. 82% of Deepika's list is still to be covered."),
    ("Total second visits", "74", "Schools with the 2nd visit / tour month fixed. 78 more visited schools have no month fixed yet (call again). 1 school was already revisited."),
    ("Schools with contact mobile number", "477", "147 visited + 18 free-pass + 312 pending schools."),
    ("Schools without contact mobile number", "349", "5 visited (get a number on next visit) + 344 pending (landline only / no number)."),
    ("Total free passes issued", "21", "Free stay passes used by schools in these areas (out of 83 overall). Only 1 is a Jayarajan school (Kannatty LPS)."),
    ("Schools matched with Deepika's data", "134", "Of the 152 visited schools (126 unique Deepika entries, incl. 2 probable matches). 18 are not in her list."),
]

MONTHS = [("September", 1), ("October", 5), ("November", 23), ("December", 19),
          ("January", 25), ("February", 1)]

HEAD = ["Main area", "Schools", "Covered (visited)", "Covered by free pass", "Not covered",
        "2nd visit fixed", "With mobile", "No mobile", "Free passes", "Matched with Deepika"]


def build_html():
    kpi = "\n".join(
        f'<div class="kpi"><div class="num">{v}</div><div class="lbl">{k}</div><div class="note">{n}</div></div>'
        for k, v, n in KPIS)
    body = "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    foot = "<tr><td>TOTAL</td>" + "".join(f"<td>{c}</td>" for c in tot) + "</tr>"
    months = "".join(f"<tr><td>{m}</td><td>{n}</td></tr>" for m, n in MONTHS)
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jayarajan Area Report</title>
<style>
:root {{ --bg:#f6f7f9; --card:#fff; --ink:#1d2433; --muted:#5b6475; --line:#dde1e8; --accent:#1f6feb; --head:#eef2f8; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#11151c; --card:#1a2029; --ink:#e6e9ef; --muted:#9aa4b5; --line:#2c3440; --accent:#6ea8ff; --head:#222a35; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:24px 16px 48px; }}
h1 {{ margin:0 0 4px; font-size:26px; }}
h2 {{ margin:32px 0 12px; font-size:18px; }}
.sub {{ color:var(--muted); margin:0 0 20px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:12px; }}
.kpi {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
.num {{ font-size:32px; font-weight:700; color:var(--accent); font-variant-numeric:tabular-nums; }}
.lbl {{ font-weight:600; margin:2px 0 6px; }}
.note {{ color:var(--muted); font-size:13px; }}
.wrap {{ overflow-x:auto; background:var(--card); border:1px solid var(--line); border-radius:10px; }}
table {{ border-collapse:collapse; width:100%; font-variant-numeric:tabular-nums; }}
th,td {{ padding:8px 10px; border-bottom:1px solid var(--line); text-align:right; white-space:nowrap; }}
th:first-child,td:first-child {{ text-align:left; }}
th {{ background:var(--head); font-size:13px; white-space:normal; }}
tr:last-child td {{ font-weight:700; border-bottom:0; }}
.small {{ max-width:320px; }}
footer {{ color:var(--muted); font-size:13px; margin-top:28px; }}
</style></head><body><main>
<h1>Jayarajan's Area Report - Summary</h1>
<p class="sub">Kozhikode &middot; Visits 13.08.2026 - 24.09.2026 &middot; Compared with Deepika's school list</p>
<div class="grid">{kpi}</div>
<h2>Area-wise breakdown</h2>
<div class="wrap"><table><thead><tr>{''.join(f'<th>{h}</th>' for h in HEAD)}</tr></thead>
<tbody>{body}{foot}</tbody></table></div>
<h2>Second visits by month</h2>
<div class="wrap small"><table><thead><tr><th>Month</th><th>Schools</th></tr></thead>
<tbody>{months}<tr><td>Total fixed</td><td>74</td></tr></tbody></table></div>
<footer>Source: Jayarajan_Data.pdf (Jayarajan's Area Report, 25.09.2026). "Covered by free pass" = schools covered by other executives, not counted as Jayarajan visits.
"Matched with Deepika" counts visited schools found in Deepika's list.</footer>
</main></body></html>"""
    (OUT / "Jayarajan_Summary_Report.html").write_text(html, encoding="utf-8")


def build_pdf():
    ss = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#5b6475"))
    doc = SimpleDocTemplate(str(OUT / "Jayarajan_Summary_Report.pdf"), pagesize=landscape(A4),
                            leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title="Jayarajan Area Report - Summary")
    blue = colors.HexColor("#1f6feb")
    head = colors.HexColor("#eef2f8")
    story = [Paragraph("Jayarajan's Area Report - Summary", ss["Title"]),
             Paragraph("Kozhikode | Visits 13.08.2026 - 24.09.2026 | Compared with Deepika's school list", ss["Normal"]),
             Spacer(1, 8)]

    cell = ParagraphStyle("cell", parent=ss["Normal"], fontSize=9, leading=11)
    kdata = [["Key figure", "Count", "Details"]] + [[Paragraph(f"<b>{k}</b>", cell),
                                                     Paragraph(f'<font size=13 color="#1f6feb"><b>{v}</b></font>', cell),
                                                     Paragraph(n, cell)] for k, v, n in KPIS]
    kt = Table(kdata, colWidths=[75 * mm, 22 * mm, 170 * mm])
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), blue), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e8")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f7f9")])]))
    story += [kt, Spacer(1, 6)]

    hdr = [Paragraph(f"<b>{h}</b>", ParagraphStyle("h", parent=ss["Normal"], fontSize=8, leading=10)) for h in HEAD]
    at = Table([hdr] + rows + [["TOTAL"] + tot], colWidths=[45 * mm] + [24.5 * mm] * 9, repeatRows=1)
    at.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), head), ("FONTSIZE", (0, 1), (-1, -1), 9),
                            ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e8")),
                            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("BACKGROUND", (0, -1), (-1, -1), head)]))
    story += [KeepTogether([Paragraph("Area-wise breakdown", ss["Heading2"]), at]), Spacer(1, 10)]

    mt = Table([["Month", "Schools"]] + [[m, n] for m, n in MONTHS] + [["Total fixed", 74]], colWidths=[40 * mm, 25 * mm], hAlign="LEFT")
    mt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), head), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e8")),
                            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    story += [KeepTogether([Paragraph("Second visits by month", ss["Heading2"]), mt]), Spacer(1, 10),
              Paragraph('Source: Jayarajan_Data.pdf (Jayarajan\'s Area Report, 25.09.2026). "Covered by free pass" = schools covered '
                        'by other executives, not counted as Jayarajan visits. "Matched with Deepika" counts visited schools found in Deepika\'s list.', small)]
    doc.build(story)


if __name__ == "__main__":
    build_html()
    build_pdf()
    print("done")
