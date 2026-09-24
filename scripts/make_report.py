"""Render the area-wise report (report.json) as a single self-contained HTML page."""
import json, sys, collections
from html import escape

R = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
AREAS = R["areas"]
e = lambda s: escape(str(s if s is not None else ""))
nk = lambda s: "".join(ch for ch in s.lower() if ch.isalnum())

BOARD_SHORT = {"Govt (State)": "Govt", "Aided (State)": "Aided", "Unaided (State)": "Unaided",
               "Private / Unaided": "Unaided*", "Special school": "Special", "Not recorded": "—",
               "CBSE": "CBSE", "ICSE": "ICSE"}
BOARD_CLS = {"CBSE": "b-cbse", "ICSE": "b-icse", "Govt": "b-govt"}


def board(b):
    s = BOARD_SHORT.get(b, b)
    return f'<span class="badge {BOARD_CLS.get(s, "b-state")}">{e(s)}</span>'


def yesno(v):
    return '<span class="yes">Yes</span>' if v else '<span class="no">No</span>'


STATUS_CLS = {"Overdue": "st-over", "Due now": "st-due", "Upcoming": "st-up"}


def fp_cell(fps):
    if not fps:
        return ""
    out = []
    for f in fps:
        out.append(f'<div class="fp"><b>{e(f["status"])}</b> · {e(f["date"])}, {e(f["persons"])} pers.'
                   f'<br><span class="muted">{e(f["note"])}</span>'
                   + (f'<br><span class="warn">{e(f["conflict"])}</span>' if f.get("conflict") else "") + "</div>")
    return "".join(out)


def phone_cell(r):
    note = r.get("phone_note", "")
    cls = "warn" if note and not note.startswith("Same") else "muted"
    return e(r["phone"]) + (f'<br><span class="{cls} small">{e(note)}</span>' if note else "")


# ------------------------------------------------------------------ totals
T = collections.Counter()
for A in AREAS:
    T["loc"] += len(A["localities"])
    T["data"] += A["data_total"]
    T["vis"] += A["visited"]
    T["vis_in_data"] += A["visited_in_data"]
    T["vis_not_data"] += A["visited_not_in_data"]
    T["second"] += sum(1 for s in A["second"] if s["key"] != [0, 0])
    T["hot"] += sum(1 for s in A["second"] if s["key"] == [0, 0])
    T["pend"] += len(A["pending"])
    T["pend_deep"] += sum(1 for p in A["pending"] if p["deepika"])
    T["fp"] += len(A["fp"])
    T["bad"] += A["bad_phone"]
    T["shared"] += A["shared_phone"]
    T["overdue"] += sum(1 for s in A["second"] if s["status"] == "Overdue")
    T["due"] += sum(1 for s in A["second"] if s["status"] == "Due now")
    for p in A["pending"]:
        T["pb_" + BOARD_SHORT.get(p["board"], p["board"])] += 1
        if p["phone"] != "—" and not p["phone"].startswith(tuple("6789")):
            T["landline_only"] += 1
    T["vis_deep"] += sum(1 for s in A["second"] if s["deepika"])
PI = R["phone_issues"]

html = []
w = html.append
w("""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Musthafa Area Coverage</title>
<style>
:root{--ink:#1d2330;--muted:#5d6675;--line:#d6dbe3;--soft:#f3f5f8;--brand:#1f4e79;--accent:#2f7d5b;
--warn:#b54708;--bad:#b42318;--cbse:#6941c6;--icse:#c11574;--govt:#1f4e79;--state:#475467;--bg:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.45 "Segoe UI",Roboto,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:24px;margin:0 0 4px;color:var(--brand)}
h2{font-size:18px;margin:28px 0 8px;color:var(--brand);border-bottom:2px solid var(--brand);padding-bottom:4px}
h3{font-size:14px;margin:18px 0 6px}
.sub{color:var(--muted);margin:0 0 14px}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:14px 0}
@media (max-width:640px){.tiles{grid-template-columns:repeat(2,1fr)}}
.tile{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--soft)}
.tile b{display:block;font-size:22px;color:var(--brand);line-height:1.1}
.tile span{color:var(--muted);font-size:12px}
.tile.alert b{color:var(--bad)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;margin:6px 0 10px;font-size:12px}
th,td{border:1px solid var(--line);padding:4px 6px;vertical-align:top;text-align:left}
th{background:var(--brand);color:#fff;font-weight:600;font-size:11.5px}
tbody tr:nth-child(even) td{background:#fafbfc}
td.n,th.n{text-align:right;white-space:nowrap}
tr.total td{font-weight:700;background:#e8eef6 !important}
.badge{display:inline-block;padding:1px 6px;border-radius:9px;font-size:11px;font-weight:600;color:#fff;background:var(--state);white-space:nowrap}
.b-cbse{background:var(--cbse)}.b-icse{background:var(--icse)}.b-govt{background:var(--govt)}
.yes{color:var(--accent);font-weight:700}.no{color:var(--muted)}
.muted{color:var(--muted)}.small{font-size:11px}.warn{color:var(--warn);font-size:11px}
.st-over{color:var(--bad);font-weight:700}.st-due{color:var(--warn);font-weight:700}.st-up{color:var(--accent)}
.fp{font-size:11px;margin-bottom:3px}
.area-head{display:flex;flex-wrap:wrap;gap:6px 16px;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:8px 0}
.area-head span b{color:var(--brand)}
.locs{font-size:11.5px;color:var(--muted);margin:4px 0 8px}
.note{background:#fff8e6;border:1px solid #f3d9a4;border-radius:8px;padding:8px 12px;margin:8px 0;font-size:12px}
ul{margin:4px 0 8px 18px;padding:0}
.toc a{color:var(--brand);text-decoration:none;margin-right:10px;white-space:nowrap}
.area{break-before:page}
@media print{
  @page{size:A4 landscape;margin:10mm}
  body{font-size:11px}
  main{max-width:none;padding:0}
  .scroll{overflow:visible}
  .tiles{grid-template-columns:repeat(8,1fr)}
  table{font-size:9.5px}
  th{font-size:9px}
  th,td{padding:3px 4px}
  table.summary td,table.summary th{padding:3px 3px}
  tr,td{break-inside:avoid}
  thead{display:table-header-group}
  .toc{display:none}
  h2{break-after:avoid}
}
</style></head><body><main>
""")

w('<h1>School Visit Coverage – Musthafa (Malappuram District)</h1>')
w('<p class="sub">Area-wise second visits and pending first visits, only for the areas Musthafa has already covered '
  '· Tour 22 Jun – 18 Sep 2026 · Report date 24 Sep 2026</p>')

w('<div class="tiles">')
for val, lab, cls in (
        (T["loc"], "Localities visited", ""), (T["vis"], "Schools visited", ""),
        (T["data"], "Schools in data (these localities)", ""),
        (T["second"], "2nd visits with month fixed", ""),
        (T["overdue"] + T["due"], f"2nd visits overdue / due in Sep", "alert"),
        (T["pend"], "Pending first visit", ""), (T["fp"], "Free passes used", ""),
        (PI.get("Missing", 0) + PI.get("Incomplete (no STD code)", 0), "Schools without an accurate phone number", "alert")):
    w(f'<div class="tile {cls}"><b>{val}</b><span>{e(lab)}</span></div>')
w('</div>')

w('<p class="toc"><b>Areas:</b> ' + " ".join(f'<a href="#a{i}">{e(A["area"])}</a>' for i, A in enumerate(AREAS)) + '</p>')

# ------------------------------------------------------------------ summary
w('<h2>1. Area-wise summary</h2>')
w('<p class="muted small">“Schools in data” = schools in the State-syllabus, Deepika, CBSE and ICSE lists that are located '
  'in the localities Musthafa visited: Total = Already visited + Pending 1st visit. “Schools visited” is every school in '
  'Musthafa’s tour log, including ones that are not in any list (mostly private English-medium, nursery and special '
  'schools).</p>')
w('<div class="scroll"><table class="summary"><thead><tr><th rowspan="2">Main area</th><th class="n" rowspan="2">Localities visited</th>'
  '<th class="n" rowspan="2">Schools visited (tour log)</th><th class="n" rowspan="2">2nd visit planned</th>'
  '<th class="n" rowspan="2">Overdue / due Sep</th>'
  '<th class="n" colspan="3">Schools in data (these localities)</th>'
  '<th class="n" colspan="5">Pending 1st visit by board</th>'
  '<th class="n" rowspan="2">Pending in Deepika</th><th class="n" rowspan="2">Free pass used</th>'
  '<th class="n" rowspan="2">No accurate phone</th></tr><tr><th class="n">Total</th><th class="n">Already visited</th>'
  '<th class="n">Pending 1st visit</th><th class="n">Govt</th><th class="n">Aided</th><th class="n">Unaided</th>'
  '<th class="n">CBSE</th><th class="n">ICSE</th></tr></thead><tbody>')
for A in AREAS:
    pb = collections.Counter(BOARD_SHORT.get(p["board"], p["board"]) for p in A["pending"])
    sec = [s for s in A["second"] if s["key"] != [0, 0]]
    od = sum(1 for s in sec if s["status"] in ("Overdue", "Due now"))
    w(f'<tr><td><a href="#a{AREAS.index(A)}">{e(A["area"])}</a></td><td class="n">{len(A["localities"])}</td>'
      f'<td class="n">{A["visited"]}</td><td class="n">{len(sec)}</td><td class="n">{od or ""}</td>'
      f'<td class="n">{A["data_total"]}</td><td class="n">{A["data_visited"]}</td><td class="n"><b>{len(A["pending"])}</b></td>'
      f'<td class="n">{pb["Govt"] or ""}</td><td class="n">{pb["Aided"] or ""}</td><td class="n">{pb["Unaided"] or ""}</td>'
      f'<td class="n">{pb["CBSE"] or ""}</td><td class="n">{pb["ICSE"] or ""}</td>'
      f'<td class="n">{sum(1 for p in A["pending"] if p["deepika"]) or ""}</td><td class="n">{len(A["fp"]) or ""}</td>'
      f'<td class="n">{A["bad_phone"] or ""}</td></tr>')
w(f'<tr class="total"><td>TOTAL</td><td class="n">{T["loc"]}</td><td class="n">{T["vis"]}</td>'
  f'<td class="n">{T["second"]}</td><td class="n">{T["overdue"] + T["due"]}</td><td class="n">{T["data"]}</td>'
  f'<td class="n">{T["data"] - T["pend"]}</td><td class="n">{T["pend"]}</td><td class="n">{T["pb_Govt"]}</td><td class="n">{T["pb_Aided"]}</td>'
  f'<td class="n">{T["pb_Unaided"]}</td><td class="n">{T["pb_CBSE"]}</td><td class="n">{T["pb_ICSE"]}</td>'
  f'<td class="n">{T["pend_deep"]}</td><td class="n">{T["fp"]}</td><td class="n">{T["bad"]}</td></tr>')
w('</tbody></table></div>')
w('<p class="muted small">Govt / Aided / Unaided = State-syllabus schools (from the State-syllabus and Deepika lists). '
  'Unaided* = private school not found in any list. “No accurate phone” counts both visited and pending schools.</p>')

# ------------------------------------------------------------------ month plan
w('<h2>2. Second-visit plan by month (verified)</h2>')
months = ["Aug 2026", "Sep 2026", "Oct 2026", "Nov 2026", "Dec 2026", "Jan 2027"]
w('<div class="scroll"><table><thead><tr><th>Main area</th><th class="n">Aug 2026<br>(overdue)</th><th class="n">Sep 2026<br>(due now)</th>'
  + "".join(f'<th class="n">{m}</th>' for m in months[2:]) + '<th class="n">Total</th></tr></thead><tbody>')
mt = collections.Counter()
for A in AREAS:
    c = collections.Counter(s["month"] for s in A["second"] if s["key"] != [0, 0])
    mt.update(c)
    w(f'<tr><td>{e(A["area"])}</td>' + "".join(f'<td class="n">{c[m] or ""}</td>' for m in months)
      + f'<td class="n"><b>{sum(c.values())}</b></td></tr>')
w('<tr class="total"><td>TOTAL</td>' + "".join(f'<td class="n">{mt[m]}</td>' for m in months)
  + f'<td class="n">{sum(mt.values())}</td></tr></tbody></table></div>')
w(f'<div class="note"><b>Month check:</b> every second-visit month was compared with the school’s first-visit date and with '
  f'today (24 Sep 2026). All {T["second"]} months fall after the first visit. {T["overdue"]} were planned for August and are '
  f'now overdue; {T["due"]} are due before 30 September. {T["hot"]} hot lead (G H S S Vazhakkad – interested after '
  f'free pass) still has no second-visit month and is listed first in the Kondotty table.</div>')

# ------------------------------------------------------------------ free pass
w('<h2>3. Free-pass feedback</h2>')
w('<div class="scroll"><table><thead><tr><th>#</th><th>School (tour / data name)</th><th>Area / locality</th><th>Visit status</th>'
  '<th>Person &amp; phone (free-pass sheet)</th><th>Park visit</th><th>Feedback status</th><th>What they said</th></tr></thead><tbody>')
i = 0
for A in AREAS:
    for f in A["fp"]:
        i += 1
        vs = ("Visited · hot lead, 2nd visit not fixed" if f.get("second") == "Not fixed" else
              f"Visited · 2nd visit {f['second']}") if f["visited"] and f.get("second") else (
            "Visited · no 2nd-visit month" if f["visited"] else "Not yet visited (pending)")
        w(f'<tr><td class="n">{i}</td><td>{e(f["name"])}<br><span class="muted small">Sheet: {e(f["fp_school"])}</span></td>'
          f'<td>{e(A["area"])} / {e(f["locality"])}</td><td>{e(vs)}</td><td>{e(f["person"])}<br>{e(f["phone"])}</td>'
          f'<td>{e(f["date"])}<br>{e(f["persons"])} persons</td><td><b>{e(f["status"])}</b></td>'
          f'<td>{e(f["note"])}' + (f'<br><span class="warn">{e(f["conflict"])}</span>' if f["conflict"] else "") + '</td></tr>')
w('</tbody></table></div>')
st = collections.Counter(f["status"] for A in AREAS for f in A["fp"])
w(f'<p class="small">Summary: {T["fp"]} free passes used by schools in Musthafa’s areas – '
  + ", ".join(f"{v} {k}" for k, v in st.most_common()) + '.</p>')
if R["fp_unmatched"]:
    w('<h3>Free passes given by Musthafa to institutions not in his visited areas</h3><div class="scroll"><table><thead><tr>'
      '<th>Institution</th><th>Person</th><th>Phone</th><th>Park visit</th><th>Status</th><th>Note</th></tr></thead><tbody>')
    for f in R["fp_unmatched"]:
        w(f'<tr><td>{e(f["school"])}</td><td>{e(f["person"])}</td><td>{e(f["phone"])}</td><td>{e(f["park_date"])}, '
          f'{e(f["persons"])} persons</td><td>{e(f["status"])}</td><td>{e(f["park_opinion"] or f["feedback"])}</td></tr>')
    w('</tbody></table></div>')

# ------------------------------------------------------------------ contact numbers
w('<h2>4. Contact-number check</h2>')
nb = PI.get("Missing", 0) + PI.get("Incomplete (no STD code)", 0)
w(f'<p><b>{nb} schools do not have an accurate contact number</b> ({PI.get("Missing", 0)} missing, '
  f'{PI.get("Incomplete (no STD code)", 0)} incomplete – landline written without its STD code). '
  f'A further {PI.get("Shared with another school", 0)} schools share one number with another school '
  f'(usually LP/UP/HS sections of the same management) – please confirm the right person. '
  f'{T["landline_only"]} of the {T["pend"]} pending schools have only an office landline from the government list, so a '
  f'principal’s mobile number should be collected on the first visit.</p>')
w('<div class="scroll"><table><thead><tr><th>Area</th><th>School</th><th>Visited / Pending</th><th>Number on record</th><th>Problem</th></tr></thead><tbody>')
vd = json.load(open(sys.argv[1].replace(".json", "_visited_debug.json")))
rows = []
for x in vd:
    if x.get("phone_note"):
        rows.append((x["area"], x["name"] + f' ({x["locality"]})', "Visited", x["phone"] or "—", x["phone_note"]))
for A in AREAS:
    for p in A["pending"]:
        if p.get("phone_note"):
            rows.append((A["area"], p["name"], "Pending", p["phone"], p["phone_note"]))
for r in sorted(rows, key=lambda r: (r[4].startswith("Same"), [a["area"] for a in AREAS].index(r[0]))):
    w("<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>")
w('</tbody></table></div>')

# ------------------------------------------------------------------ per area
w('<h2>5. Area-wise school lists</h2>')
w('<p class="muted small">For each main area: (A) schools already visited that have a second-visit month, sorted by month; '
  '(B) schools from the data lists in the same localities that Musthafa has not visited yet. Board: Govt / Aided / '
  'Unaided = State syllabus; CBSE; ICSE. “In Deepika” shows whether the school appears in Deepika’s Malappuram sheet.</p>')
for idx, A in enumerate(AREAS):
    sec = A["second"]
    w(f'<section class="area" id="a{idx}"><h2>{e(A["area"])} area</h2>')
    w(f'<div class="area-head"><span><b>{len(A["localities"])}</b> localities visited</span>'
      f'<span><b>{A["data_total"]}</b> schools in data</span><span><b>{A["visited"]}</b> schools visited</span>'
      f'<span><b>{len([s for s in sec if s["key"] != [0, 0]])}</b> second visits planned</span>'
      f'<span><b>{A["no_date"]}</b> visited, no 2nd-visit month yet</span>'
      f'<span><b>{len(A["pending"])}</b> pending first visit</span><span><b>{len(A["fp"])}</b> free passes</span></div>')
    w(f'<div class="locs"><b>Localities:</b> {e(", ".join(A["localities"]))}</div>')

    w(f'<h3>A. Second visits ({len(sec)})</h3>')
    if sec:
        w('<div class="scroll"><table><thead><tr><th>#</th><th>2nd visit month</th><th>Status</th><th>School</th><th>Locality</th>'
          '<th>Board</th><th>Contact person</th><th>Phone</th><th>1st visit</th><th>In Deepika</th><th>Free pass</th></tr></thead><tbody>')
        for i, s in enumerate(sec, 1):
            w(f'<tr><td class="n">{i}</td><td><b>{e(s["month"])}</b></td><td class="{STATUS_CLS.get(s["status"], "st-over")}">{e(s["status"])}</td>'
              f'<td>{e(s["name"])}' + (f'<br><span class="muted small">Data: {e(s["data_name"])}</span>' if s["data_name"] and nk(s["data_name"]) != nk(s["name"]) else "")
              + f'</td><td>{e(s["locality"])}</td><td>{board(s["board"])}</td><td>{e(s["contact"])}</td>'
              f'<td>{phone_cell(s)}</td><td>{e(s["first"])}</td><td>{yesno(s["deepika"])}</td><td>{fp_cell(s["fp"])}</td></tr>')
        w('</tbody></table></div>')
    else:
        w('<p class="muted">No second-visit month recorded yet for this area.</p>')

    pend = A["pending"]
    w(f'<h3>B. Pending first visit ({len(pend)})</h3>')
    if pend:
        w('<div class="scroll"><table><thead><tr><th>#</th><th>School</th><th>Board</th><th>Locality</th><th>Address</th>'
          '<th>Phone</th><th>In Deepika</th><th>Free pass / note</th></tr></thead><tbody>')
        for i, p in enumerate(pend, 1):
            note = fp_cell(p["fp"])
            if p["check"]:
                note += f'<span class="warn">Check: may be the visited “{e(p["check"][0])}”</span>'
            w(f'<tr><td class="n">{i}</td><td>{e(p["name"])}' + (f'<br><span class="muted small">Classes {e(p["level"])}</span>' if p["level"] else "")
              + f'</td><td>{board(p["board"])}</td><td>{e(p["locality"])}</td><td class="small">{e(p["address"])}</td>'
              f'<td>{phone_cell(p)}</td><td>{yesno(p["deepika"])}</td><td>{note}</td></tr>')
        w('</tbody></table></div>')
    else:
        w('<p class="muted">No pending schools found in the data for these localities.</p>')
    w('</section>')

# ------------------------------------------------------------------ method
s = R["stats"]
w('<section class="area"><h2>6. How this report was made</h2><ul>')
w(f'<li><b>Musthafa’s visits:</b> {s["visited"]} visited schools in {T["loc"]} localities, with first-visit date, '
  f'contact person, phone and next step, taken from Musthafa’s outreach report (tour 22 Jun – 18 Sep 2026).</li>')
w(f'<li><b>School data compared:</b> State-syllabus list ({s["state"]} schools), Deepika’s Malappuram sheet '
  f'({s["deepika"]} schools – {s["deepika"] - 15} of them are the same schools as the State list), CBSE Malappuram '
  f'directory ({s["cbse"]} schools) and ICSE Malappuram list ({s["icse"]} schools); {s["master"]} unique schools in total.</li>')
w('<li><b>Only Musthafa’s areas:</b> a school from the data is included only when its name (or, for CBSE/ICSE, its '
  'address) contains one of the localities Musthafa visited, allowing for spelling variants (Areacode/Areekode, '
  'Kizhisseri/Kizhisheri, Mambad/Mampad). A State-list school must also belong to the same assembly constituency as '
  'the schools Musthafa visited in that locality, so same-named villages elsewhere are left out.</li>')
w(f'<li><b>Visited or pending:</b> a data school counts as visited when it matches a tour entry by Deepika name, '
  f'phone number, or school code / name in the same locality (e.g. “National L P School” = “N L P S Kolathur”). '
  f'{s["linked"]} of the {s["visited"]} visited schools were matched this way; the rest are not in any list. All other '
  f'data schools in those localities are shown as <b>pending first visit</b>. Where a pending school looks similar to '
  f'an unmatched visited school, it carries a “Check” note.</li>')
w('<li><b>Second-visit month:</b> taken from the tour log (“2nd visit: Oct 2026”, “Visit before 30 Sep” = Sep 2026, '
  '“Overdue” = Aug 2026) and checked against the first-visit date and today’s date.</li>')
w('<li><b>Free-pass feedback:</b> each row of the feedback sheet was matched to a visited or pending school by name '
  'and locality, then by phone number. The sheet’s spelling “Nuetral/Intrested” is shown as Neutral/Interested.</li>')
w('<li><b>Accurate phone:</b> a 10-digit mobile number (starting 6–9) or a Malappuram landline with STD code '
  '(0483, 0494, 04931, 04933…). Missing numbers and landlines without STD code are counted as not accurate.</li>')
w('<li><b>Known limits:</b> some contact-person names are cut off in the original tour sheet and are shown as-is. '
  'The State list has no street address, so the address shown is locality, block and constituency.</li>')
w('</ul></section></main></body></html>')

open(OUT, "w").write("\n".join(html))
print("written", OUT, T)
