"""Build the Kasaragod final coverage report (HTML + PDF) from both sources."""
import html
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from compare import PENDING_ALREADY_VISITED, build, is_mobile
from data import AREAS, PENDING

OUT = Path(__file__).resolve().parent
HTML_OUT = OUT / "Kasaragod_Final_Report.html"
PDF_OUT = OUT / "Kasaragod_Final_Report.pdf"
e = html.escape

r = build()
cov, pen = r["covered"], r["pending"]
covered, not_covered = len(cov), len(pen)
total = covered + not_covered
with_mobile = sum(is_mobile(x["phone"]) for x in cov + pen)
without_mobile = total - with_mobile
execs = Counter(c["exec"] for c in cov)
new_names = {p["name"] for p in r["new_from_sametham"]}

cards = [
    ("Areas visited", len(AREAS), "by Emmanuel & Shibili"),
    ("Total schools in executive areas", total, "covered + not yet covered"),
    ("Schools covered", covered, "first visit done"),
    ("Schools not yet covered", not_covered, f"{len(new_names)} found only through Sametham"),
    ("Second visits due", covered, f"Emmanuel {execs['Emmanuel']} · Shibili {execs['Shibili']}"),
    ("Schools with mobile number", with_mobile, f"{with_mobile * 100 // total}% of all schools"),
    ("Schools without mobile number", without_mobile, "landline only or no number"),
    ("Free passes issued", "—", "not recorded in either file"),
]

by_area = defaultdict(lambda: [0, 0, 0, 0])
for x in cov:
    d = by_area[x["area"]]; d[0] += 1; d[2 if is_mobile(x["phone"]) else 3] += 1
for x in pen:
    d = by_area[x["area"]]; d[1] += 1; d[2 if is_mobile(x["phone"]) else 3] += 1

months = Counter(c["month"].split(",")[0].replace(" end", "") for c in cov)
month_order = ["August", "September", "October", "November", "December"]
type_counts = Counter(("Govt" if x["type"] == "Government" else x["type"]) for x in cov + pen)


def rows(items):
    return "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in item) + "</tr>" for item in items)


def phone(p):
    if is_mobile(p):
        return p
    return f'{e(p)} <span class="tag warn">{"no number" if p == "—" else "landline"}</span>'


area_rows = [(e(a), *by_area[a][:2], sum(by_area[a][:2]), by_area[a][2], by_area[a][3] or "–")
             for a in AREAS]
area_rows.append(tuple(f"<b>{v}</b>" for v in
                       ("Total", covered, not_covered, total, with_mobile, without_mobile)))

cov_rows = [(i, e(c["area"]), e(c["name"]), e(c["type"]), phone(c["phone"]), e(c["exec"]),
             e(c["month"]), c["sametham"] or '<span class="mute">not listed</span>')
            for i, c in enumerate(sorted(cov, key=lambda c: c["area"]), 1)]
pen_rows = [(i, e(p["area"]),
             e(p["name"]) + (' <span class="tag new">new</span>' if p["name"] in new_names else ""),
             e(p["type"]), phone(p["phone"]),
             p["code"] or '<span class="mute">CBSE list</span>')
            for i, p in enumerate(sorted(pen, key=lambda p: (p["area"], p["name"])), 1)]

visited_not_in_sam = covered - r["visited_rows_matched"]
old_unique = len({(p[1], p[4]) for p in PENDING})
findings = [
    f"<b>Sametham register:</b> {r['sametham_total']} schools. "
    f"<b>{r['sametham_in_area']}</b> of them are in the 56 executive areas "
    f"({len(r['visited_matched'])} already visited, {r['sametham_pending']} not yet). "
    f"The other {r['sametham_total'] - r['sametham_in_area']} are in areas the team has not visited, so they are left out.",
    f"<b>Visited schools:</b> {r['visited_rows_matched']} of the {covered} visited entries match "
    f"{len(r['visited_matched'])} Sametham schools (the High School and Higher Secondary sections of "
    f"Kumbala and Neerchal are logged separately). The other {visited_not_in_sam} are not in this Sametham "
    "extract: mostly Hosdurg/Kanhangad-side schools, private schools and LP/UP schools it does not cover.",
    f"<b>New pending schools:</b> comparing both files found <b>{len(new_names)}</b> schools in the executive "
    "areas that the earlier visit-log report did not list as pending (marked <span class='tag new'>new</span>).",
    f"<b>Corrections:</b> {len(PENDING_ALREADY_VISITED)} schools the visit-log report listed as pending were "
    "actually visited already: " + "; ".join(f"{e(k)} ({e(v)})" for k, v in PENDING_ALREADY_VISITED.items())
    + f". The report also listed {len(PENDING) - old_unique} schools twice under different areas; each is counted once here.",
    "<b>Free passes:</b> neither file has any free-pass figure, so this count cannot be given. "
    "Share the free-pass log and it can be added.",
    "<b>Mobile numbers:</b> a number counts as mobile when it is 10 digits starting with 6–9. "
    "Most Sametham numbers are school landlines (04994 / 04998).",
]

card_html = "\n".join(
    f'<div class="card{" muted" if v == "—" else ""}"><div class="num">{v}</div>'
    f'<div class="lbl">{e(l)}</div><div class="sub">{e(s)}</div></div>' for l, v, s in cards)
month_html = "".join(
    f'<div class="bar"><span>{m}</span><div class="track"><div class="fill" '
    f'style="width:{months[m] * 100 / max(months.values()):.0f}%"></div></div><b>{months[m]}</b></div>'
    for m in month_order if months[m])

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kasaragod Coverage Report</title>
<style>
:root {{ --bg:#fff; --fg:#1d2433; --mute:#5b6475; --line:#e3e7ee; --card:#f5f7fb; --accent:#1f5fbf; --warn:#b4541a; --ok:#1d7a4a; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#12161f; --fg:#e6e9ef; --mute:#9aa3b5; --line:#2a3242; --card:#1a2030; --accent:#6ea2f5; --warn:#f0a36b; --ok:#5fcf94; }} }}
:root[data-theme="dark"] {{ --bg:#12161f; --fg:#e6e9ef; --mute:#9aa3b5; --line:#2a3242; --card:#1a2030; --accent:#6ea2f5; --warn:#f0a36b; --ok:#5fcf94; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:1000px; margin:0 auto; padding:28px 16px 48px; }}
h1 {{ font-size:24px; margin:0 0 4px; }}
h2 {{ font-size:17px; margin:30px 0 10px; padding-bottom:6px; border-bottom:2px solid var(--line); }}
.meta {{ color:var(--mute); margin:0 0 20px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }}
.card .num {{ font-size:30px; font-weight:700; color:var(--accent); line-height:1.1; }}
.card.muted .num {{ color:var(--mute); }}
.card .lbl {{ font-weight:600; margin-top:4px; }}
.card .sub {{ color:var(--mute); font-size:12px; }}
ul.find {{ padding-left:18px; margin:0; }} ul.find li {{ margin:6px 0; }}
.wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
th, td {{ text-align:left; padding:5px 7px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ background:var(--card); font-weight:600; white-space:nowrap; }}
td:first-child {{ color:var(--mute); }}
.num-cols td:not(:first-child), .num-cols th:not(:first-child) {{ text-align:right; }}
.num-cols td:first-child {{ color:var(--fg); }}
.mute {{ color:var(--mute); }}
.tag {{ font-size:10.5px; padding:1px 6px; border-radius:8px; background:var(--line); white-space:nowrap; }}
.tag.warn {{ color:var(--warn); }} .tag.new {{ color:var(--ok); font-weight:600; }}
.bar {{ display:grid; grid-template-columns:90px 1fr 32px; align-items:center; gap:8px; margin:4px 0; }}
.track {{ background:var(--card); border:1px solid var(--line); height:14px; border-radius:7px; overflow:hidden; }}
.fill {{ background:var(--accent); height:100%; }}
.bar b {{ text-align:right; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}
@media (max-width:700px) {{ .two {{ grid-template-columns:1fr; }} }}
@media print {{
  :root {{ --bg:#fff; --fg:#1d2433; --mute:#5b6475; --line:#dfe3ea; --card:#f3f5f9; --accent:#1f5fbf; --warn:#b4541a; --ok:#1d7a4a; }}
  main {{ padding:0; max-width:none; }}
  .cards {{ grid-template-columns:repeat(4,1fr); }}
  h2 {{ break-after:avoid; }} tr, .card, li {{ break-inside:avoid; }}
}}
@page {{ size:A4; margin:14mm 12mm; }}
</style></head>
<body><main>
<h1>Kasaragod District – Final School Coverage Report</h1>
<p class="meta">Executives: Emmanuel &amp; Shibili · Visits 13 Jul – 21 Aug 2026 · Visit log compared with the
Sametham school register (KITE, updated 27 Jun 2026)</p>

<h2>Summary</h2>
<div class="cards">{card_html}</div>

<h2>What the comparison found</h2>
<ul class="find">{"".join(f"<li>{f}</li>" for f in findings)}</ul>

<div class="two">
<div><h2>Second visits by month</h2>{month_html}
<p class="meta" style="font-size:12px">Where two months were given, the first is used.</p></div>
<div><h2>Schools by type</h2><div class="wrap"><table class="num-cols">
<tr><th>Type</th><th>Schools</th></tr>
{rows((e(t), n) for t, n in type_counts.most_common())}
</table></div></div>
</div>

<h2>Area-wise summary</h2>
<div class="wrap"><table class="num-cols">
<tr><th>Area</th><th>Covered</th><th>Not covered</th><th>Total</th><th>Mobile</th><th>No mobile</th></tr>
{rows(area_rows)}
</table></div>
<p class="meta" style="font-size:12px">A school listed under two areas in the source is counted once, under the first area.</p>

<h2>Covered schools – second visit due ({covered})</h2>
<div class="wrap"><table>
<tr><th>#</th><th>Area</th><th>School</th><th>Type</th><th>Contact</th><th>Executive</th><th>2nd visit</th><th>Sametham</th></tr>
{rows(cov_rows)}
</table></div>

<h2>Schools not yet covered – first visit pending ({not_covered})</h2>
<div class="wrap"><table>
<tr><th>#</th><th>Area</th><th>School</th><th>Type</th><th>Contact</th><th>Source</th></tr>
{rows(pen_rows)}
</table></div>
</main></body></html>
"""

HTML_OUT.write_text(page, encoding="utf-8")
subprocess.run(["/opt/pw-browsers/chromium", "--headless", "--no-sandbox", "--disable-gpu",
                "--no-pdf-header-footer", f"--print-to-pdf={PDF_OUT}", HTML_OUT.as_uri()],
               check=True, capture_output=True)
print(f"total={total} covered={covered} not_covered={not_covered} mobile={with_mobile} "
      f"no_mobile={without_mobile} new={len(new_names)} sam_in_area={r['sametham_in_area']} "
      f"sam_pending={r['sametham_pending']}")
