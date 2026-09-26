"""Build the Kasaragod school coverage summary as HTML and PDF."""
import html
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from data import AREAS, PENDING, SECOND

OUT = Path(__file__).resolve().parent
HTML_OUT = OUT / "Kasaragod_Final_Report.html"
PDF_OUT = OUT / "Kasaragod_Final_Report.pdf"


def is_mobile(num):
    return bool(re.fullmatch(r"[6-9]\d{9}", num))


e = html.escape

# Pending schools listed under more than one area are counted once in totals.
pending_unique = {}
for area, school, typ, addr, phone in PENDING:
    pending_unique.setdefault((school, phone), area)

covered = len(SECOND)
not_covered = len(pending_unique)
total = covered + not_covered
contacts = [r[3] for r in SECOND] + [phone for _, phone in pending_unique]
with_mobile = sum(is_mobile(n) for n in contacts)
without_mobile = total - with_mobile
execs = Counter(r[4] for r in SECOND)
duplicates = {k: [a for a, s, _, _, p in PENDING if (s, p) == k]
              for k in pending_unique
              if sum((s, p) == k for _, s, _, _, p in PENDING) > 1}

cards = [
    ("Areas visited", len(AREAS), "by Emmanuel & Shibili"),
    ("Total schools in executive areas", total, "covered + not yet covered"),
    ("Schools covered", covered, "1st visit done"),
    ("Schools not yet covered", not_covered, f"{len(PENDING)} rows in source; {len(PENDING) - not_covered} repeat across areas"),
    ("Second visits due", covered, f"Emmanuel {execs['Emmanuel']} · Shibili {execs['Shibili']}"),
    ("Schools with mobile number", with_mobile, f"{with_mobile * 100 // total}% of all schools"),
    ("Schools without mobile number", without_mobile, "landline only (04xxx)"),
    ("Free passes issued", "—", "not recorded in the source data"),
]

by_area = defaultdict(lambda: {"cov": 0, "pend": 0, "mob": 0, "nomob": 0})
for area, _, _, phone, _, _ in SECOND:
    d = by_area[area]; d["cov"] += 1; d["mob" if is_mobile(phone) else "nomob"] += 1
for (school, phone), area in pending_unique.items():
    d = by_area[area]; d["pend"] += 1; d["mob" if is_mobile(phone) else "nomob"] += 1

months = Counter()
for r in SECOND:
    months[r[5].split(",")[0].replace(" end", "")] += 1
month_order = ["August", "September", "October", "November", "December"]

type_counts = Counter(r[2] for r in SECOND) + Counter(
    t for a, s, t, _, p in PENDING if pending_unique[(s, p)] == a)


def rows(items):
    return "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in item) + "</tr>" for item in items)


area_rows = []
for a in AREAS:
    d = by_area[a]
    area_rows.append((e(a), d["cov"], d["pend"], d["cov"] + d["pend"], d["mob"], d["nomob"] or "–"))
area_rows.append(("<b>Total</b>", f"<b>{covered}</b>", f"<b>{not_covered}</b>", f"<b>{total}</b>",
                  f"<b>{with_mobile}</b>", f"<b>{without_mobile}</b>"))

second_rows = [(i, e(a), e(s), e(t), p, e(x), e(m))
               for i, (a, s, t, p, x, m) in enumerate(SECOND, 1)]
pending_rows = []
for i, (a, s, t, addr, p) in enumerate(PENDING, 1):
    tag = "" if pending_unique[(s, p)] == a else ' <span class="dup">repeat</span>'
    phone = p if is_mobile(p) else f'{p} <span class="ll">landline</span>'
    pending_rows.append((i, e(a), e(s) + tag, e(t), e(addr), phone))

dup_notes = "; ".join(f"{e(s)} ({', '.join(areas)})" for (s, _), areas in duplicates.items())

card_html = "\n".join(
    f'<div class="card{" muted" if v == "—" else ""}"><div class="num">{v}</div>'
    f'<div class="lbl">{e(l)}</div><div class="sub">{e(s)}</div></div>'
    for l, v, s in cards)

month_html = "".join(
    f'<div class="bar"><span>{m}</span><div class="track"><div class="fill" '
    f'style="width:{months[m] * 100 / max(months.values()):.0f}%"></div></div><b>{months[m]}</b></div>'
    for m in month_order if months[m])

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kasaragod Coverage Report</title>
<style>
:root {{ --bg:#fff; --fg:#1d2433; --mute:#5b6475; --line:#e3e7ee; --card:#f5f7fb; --accent:#1f5fbf; --warn:#b4541a; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#12161f; --fg:#e6e9ef; --mute:#9aa3b5; --line:#2a3242; --card:#1a2030; --accent:#6ea2f5; --warn:#f0a36b; }} }}
:root[data-theme="dark"] {{ --bg:#12161f; --fg:#e6e9ef; --mute:#9aa3b5; --line:#2a3242; --card:#1a2030; --accent:#6ea2f5; --warn:#f0a36b; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:1000px; margin:0 auto; padding:28px 16px 48px; }}
h1 {{ font-size:24px; margin:0 0 4px; }}
h2 {{ font-size:17px; margin:32px 0 10px; padding-bottom:6px; border-bottom:2px solid var(--line); }}
.meta {{ color:var(--mute); margin:0 0 20px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }}
.card .num {{ font-size:30px; font-weight:700; color:var(--accent); line-height:1.1; }}
.card.muted .num {{ color:var(--mute); }}
.card .lbl {{ font-weight:600; margin-top:4px; }}
.card .sub {{ color:var(--mute); font-size:12px; }}
.note {{ background:var(--card); border-left:4px solid var(--warn); padding:10px 14px; border-radius:6px; margin:14px 0; font-size:13px; }}
.wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ background:var(--card); font-weight:600; white-space:nowrap; }}
td:first-child {{ color:var(--mute); }}
.num-cols td:not(:first-child), .num-cols th:not(:first-child) {{ text-align:right; }}
.num-cols td:first-child {{ color:var(--fg); }}
.dup, .ll {{ font-size:11px; padding:1px 6px; border-radius:8px; background:var(--line); color:var(--mute); white-space:nowrap; }}
.ll {{ color:var(--warn); }}
.bars {{ max-width:520px; }}
.bar {{ display:grid; grid-template-columns:90px 1fr 32px; align-items:center; gap:8px; margin:4px 0; }}
.track {{ background:var(--card); border:1px solid var(--line); height:14px; border-radius:7px; overflow:hidden; }}
.fill {{ background:var(--accent); height:100%; }}
.bar b {{ text-align:right; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}
@media (max-width:700px) {{ .two {{ grid-template-columns:1fr; }} }}
@media print {{
  :root {{ --bg:#fff; --fg:#1d2433; --mute:#5b6475; --line:#dfe3ea; --card:#f3f5f9; --accent:#1f5fbf; --warn:#b4541a; }}
  main {{ padding:0; max-width:none; }}
  .cards {{ grid-template-columns:repeat(4,1fr); }}
  h2 {{ break-after:avoid; }}
  tr {{ break-inside:avoid; }}
  .card {{ break-inside:avoid; }}
}}
@page {{ size:A4; margin:14mm 12mm; }}
</style></head>
<body><main>
<h1>Kasaragod District – Final School Coverage Report</h1>
<p class="meta">Executives: Emmanuel &amp; Shibili · Visit period: 13 Jul – 21 Aug 2026 · {len(AREAS)} areas</p>

<h2>Summary</h2>
<div class="cards">{card_html}</div>
<div class="note"><b>Free passes:</b> the source report has no free-pass column or figure, so this count cannot be
calculated from it. Share the free-pass log and it can be added.</div>
<div class="note"><b>How the counts work:</b> “covered” = schools already visited once (all are due a second visit).
“Not yet covered” = registered schools in the same areas with no visit yet. {len(PENDING) - not_covered} pending entries
appear under more than one area in the source and are counted once: {dup_notes}.
A number is treated as a mobile number when it is 10 digits starting with 6–9; the rest are landlines.</div>

<div class="two">
<div><h2>Second visits by month</h2><div class="bars">{month_html}</div>
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
<p class="meta" style="font-size:12px">A 0 under “Not covered” for an area such as Mogral Puthur or Shiriya means its pending
school is already counted under another area (see note above).</p>

<h2>Covered schools – second visit due ({covered})</h2>
<div class="wrap"><table>
<tr><th>#</th><th>Area</th><th>School</th><th>Type</th><th>Contact</th><th>Executive</th><th>2nd visit</th></tr>
{rows(second_rows)}
</table></div>

<h2>Schools not yet covered – first visit pending ({len(PENDING)} entries, {not_covered} unique)</h2>
<div class="wrap"><table>
<tr><th>#</th><th>Area</th><th>School</th><th>Type</th><th>Address</th><th>Contact</th></tr>
{rows(pending_rows)}
</table></div>
</main></body></html>
"""

HTML_OUT.write_text(page, encoding="utf-8")
subprocess.run(["/opt/pw-browsers/chromium", "--headless", "--no-sandbox", "--disable-gpu",
                "--no-pdf-header-footer", f"--print-to-pdf={PDF_OUT}", HTML_OUT.as_uri()],
               check=True, capture_output=True)
print(f"total={total} covered={covered} not_covered={not_covered} second={covered} "
      f"mobile={with_mobile} no_mobile={without_mobile}")
