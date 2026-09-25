"""Render a single self-contained HTML report (tabs + area filter + search)."""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

SHEETS = [
    ("second", "Second visits", ["Second visit month", "Area", "School", "Contact person", "Contact no.",
                                 "First visit", "Tour period (remarks)", "Verification", "In Deepika data",
                                 "Probability"]),
    ("visited", "Visited (1st visit)", ["Area", "First visit", "School", "Type", "Contact person", "Contact no.",
                                        "Strength", "Visits", "Call remarks", "In Deepika data", "Official list",
                                        "Free-pass feedback", "Probability"]),
    ("pend_mob", "Pending – with mobile", ["Area", "School", "Type", "Classes", "Mobile no.", "Other no.",
                                          "In Deepika data", "Source", "Free-pass feedback", "Probability"]),
    ("pend_nomob", "Pending – no mobile", ["Area", "School", "Type", "Classes", "Landline", "In Deepika data",
                                          "Source"]),
    ("deepika", "Deepika mobiles", ["Area", "Deepika Sl", "School", "Deepika block", "Type", "Mobile (Deepika)",
                                    "Visited by executive", "Executive's remark", "Free-pass feedback",
                                    "Probability"]),
    ("freepass", "Free-pass feedback", ["Area", "Park visit", "Person", "Contact", "School (feedback form)",
                                        "Matched school", "Visited by Aslam", "Persons", "Executive (form)",
                                        "Glamping stay", "Feedback", "Tour period", "Final status", "Probability"]),
]
SUMMARY_COLS = ["Area", "State-syllabus schools", "CBSE / ICSE schools", "Found only in Aslam's log",
                "Total schools", "Visited (unique)", "Pending 1st visit", "- with mobile", "- no mobile",
                "2nd visit done", "2nd visit planned", "Deepika mobiles", "Deepika visited", "High / Very High"]

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aslam School Visits</title>
<style>
:root{--bg:#f6f8f8;--surface:#fff;--ink:#1f2933;--muted:#5f6b76;--line:#d5e0e0;--accent:#0b6e6e;
--accent-ink:#fff;--zebra:#f2f6f6;--vh:#0a6b2e;--h:#2f8f46;--m:#a86b00;--l:#5f6b76;--vl:#b3261e;--due:#b3261e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1716;--surface:#16211f;--ink:#e6eeed;
--muted:#9fb0ae;--line:#2a3a38;--accent:#3fb6a8;--accent-ink:#06201d;--zebra:#1a2725;--vh:#5fd38a;--h:#7ccf8f;
--m:#e0a84a;--l:#9fb0ae;--vl:#ff8a80;--due:#ff8a80}}
:root[data-theme="dark"]{--bg:#0f1716;--surface:#16211f;--ink:#e6eeed;--muted:#9fb0ae;--line:#2a3a38;
--accent:#3fb6a8;--accent-ink:#06201d;--zebra:#1a2725;--vh:#5fd38a;--h:#7ccf8f;--m:#e0a84a;--l:#9fb0ae;
--vl:#ff8a80;--due:#ff8a80}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:20px 16px 8px;max-width:1400px;margin:0 auto}
h1{margin:0;font-size:22px}
.sub{color:var(--muted);font-size:13px}
main{max-width:1400px;margin:0 auto;padding:0 16px 40px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:12px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.kpi b{display:block;font-size:22px;color:var(--accent);font-variant-numeric:tabular-nums}
.kpi span{font-size:12px;color:var(--muted)}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0;position:sticky;top:0;
background:var(--bg);padding:8px 0;z-index:3}
select,input[type=search]{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;
background:var(--surface);color:var(--ink)}
input[type=search]{flex:1;min-width:180px}
nav.tabs{display:flex;gap:4px;overflow-x:auto;border-bottom:1px solid var(--line);margin-top:4px}
nav.tabs button{font:inherit;border:0;background:none;color:var(--muted);padding:8px 12px;cursor:pointer;
border-bottom:3px solid transparent;white-space:nowrap}
nav.tabs button[aria-selected=true]{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
.panel{display:none;padding-top:10px}.panel.on{display:block}
.note{color:var(--muted);font-size:12.5px;margin:4px 0 8px}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th{background:var(--accent);color:var(--accent-ink);text-align:left;padding:6px 8px;position:sticky;top:0;
font-weight:600;white-space:nowrap}
td{padding:5px 8px;border-top:1px solid var(--line);vertical-align:top;min-width:7em;max-width:28em}
tbody tr:nth-child(even){background:var(--zebra)}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap;font-weight:600}
.p-VeryHigh{color:var(--vh);font-weight:700}.p-High{color:var(--h);font-weight:600}.p-Medium{color:var(--m);font-weight:600}
.p-Low{color:var(--l)}.p-VeryLow{color:var(--vl);font-weight:600}.due{color:var(--due)}
details.area{background:var(--surface);border:1px solid var(--line);border-radius:8px;margin:10px 0;padding:0 12px}
details.area>summary{cursor:pointer;padding:10px 0;font-weight:600;font-size:16px}
details.area h3{font-size:14px;margin:14px 0 6px}
.count{color:var(--muted);font-weight:400;font-size:13px}
.method p{max-width:900px}
button.theme{margin-left:auto;font:inherit;border:1px solid var(--line);background:var(--surface);color:var(--ink);
border-radius:6px;padding:6px 10px;cursor:pointer}
@media print{.controls,nav.tabs,button.theme{display:none}.panel{display:block!important;page-break-before:always}
th{position:static}}
</style>
</head>
<body>
<header>
<h1>Aslam – School Visit Verification Report</h1>
<div class="sub" id="sub"></div>
</header>
<main>
<div class="kpis" id="kpis"></div>
<div class="controls">
<label for="area">Area</label><select id="area"></select>
<input type="search" id="q" placeholder="Search school, place, phone, remark…">
<button class="theme" id="theme" type="button">Toggle theme</button>
</div>
<nav class="tabs" role="tablist" id="tabs"></nav>
<div id="panels"></div>
</main>
<script>
const DATA = __DATA__;
const SHEETS = __SHEETS__;
const SUMMARY_COLS = __SUMMARY_COLS__;
const S = DATA.stats;
const $ = s => document.querySelector(s);
const esc = v => String(v ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

$("#sub").textContent = `Malappuram district · Visits ${S.first_date} to ${S.last_date} · Prepared ${S.today}`;
const P = S.prob;
$("#kpis").innerHTML = [
  [S.unique_visited, `schools visited by Aslam (${S.visit_entries} visit entries)`],
  [S.pending, "schools pending first visit"], [S.pend_mob, "pending, with mobile no."],
  [S.second_planned, "second visits planned"], [S.due_now, "second visits due now (Sept)"],
  [(P["Very High"]||0)+(P["High"]||0), "High / Very High probability"]
].map(([n,l]) => `<div class="kpi"><b>${n}</b><span>${esc(l)}</span></div>`).join("");

const areaSel = $("#area");
areaSel.innerHTML = `<option value="">All areas</option>` + S.areas.map(a => `<option>${esc(a)}</option>`).join("");

function cell(col, v){
  if (col === "Probability") return `<td class="p-${String(v).replace(/\s/g,"")}">${esc(v)}</td>`;
  if (col === "Verification" && String(v).includes("DUE NOW")) return `<td class="due">${esc(v)}</td>`;
  if (["Mobile no.","Mobile (Deepika)","Contact no."].includes(col)) return `<td class="num">${esc(v)}</td>`;
  return `<td>${esc(v)}</td>`;
}
function tableHTML(rows, cols){
  if (!rows.length) return `<p class="note">No schools in this list.</p>`;
  return `<div class="wrap"><table><thead><tr>${cols.map(c=>`<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>` +
    rows.map(r => `<tr>${cols.map(c => cell(c, r[c])).join("")}</tr>`).join("") + `</tbody></table></div>`;
}
function filtered(rows){
  const a = areaSel.value, q = $("#q").value.trim().toLowerCase();
  return rows.filter(r => (!a || r.Area === a) && (!q || Object.values(r).join(" ").toLowerCase().includes(q)));
}

const NOTES = {
  second: `${S.second_planned} schools need a second visit (month from Aslam's sheet, checked against the tour period in the remarks; ${S.derived} derived as one month before the tour month). ${S.second_done} schools have already been revisited. Red = due now.`,
  visited: `${S.unique_visited} unique schools (${S.visit_entries} visit entries; repeat visits counted once). ${S.in_deepika} are on Deepika's list.`,
  pend_mob: "Schools from the official lists in Aslam's areas that he has not visited yet and that have a mobile number.",
  pend_nomob: "Pending schools with only a landline or no number – plan a direct visit.",
  deepika: `${S.deepika_mob} Deepika schools in Aslam's areas have a mobile number; ${S.deepika_visited} have been visited by the executive.`,
  freepass: `${S.freepass} of the ${S.counts.freepass} free-pass feedback entries belong to schools in Aslam's areas.`,
};

const tabs = [["summary","Summary"],["areawise","Area-wise"],...SHEETS.map(s=>[s[0],s[1]]),["method","How it was checked"]];
$("#tabs").innerHTML = tabs.map(([id,l],i)=>`<button role="tab" data-tab="${id}" aria-selected="${i===0}">${esc(l)}</button>`).join("");
$("#panels").innerHTML = tabs.map(([id],i)=>`<section class="panel${i===0?" on":""}" id="p-${id}"></section>`).join("");
let current = "summary";
try { current = localStorage.getItem("aslam-tab") || "summary"; } catch(e) {}

function render(){
  const a = areaSel.value;
  const sum = DATA.summary.filter(r => !a || r.Area === a || r.Area === "TOTAL");
  $("#p-summary").innerHTML = `<p class="note">Area = assembly constituency (State census). Total schools = State-syllabus + CBSE/ICSE + schools found only in Aslam's log.</p>` + tableHTML(a ? sum.filter(r=>r.Area===a) : sum, SUMMARY_COLS);
  for (const [id,,cols] of SHEETS){
    const rows = filtered(DATA[id]);
    $("#p-"+id).innerHTML = `<p class="note">${esc(NOTES[id])} Showing ${rows.length}.</p>` + tableHTML(rows, cols);
  }
  const areas = a ? [a] : S.areas;
  $("#p-areawise").innerHTML = areas.map(ar => {
    const s = DATA.summary.find(r => r.Area === ar) || {};
    const secs = SHEETS.map(([id,label,cols]) => {
      const rows = filtered(DATA[id]).filter(r => r.Area === ar);
      return `<h3>${esc(label)} <span class="count">(${rows.length})</span></h3>` + tableHTML(rows, cols.filter(c=>c!=="Area"));
    }).join("");
    return `<details class="area"${a?" open":""}><summary>${esc(ar)} <span class="count">– ${s["Total schools"]} schools · ${s["Visited (unique)"]} visited · ${s["Pending 1st visit"]} pending · ${s["2nd visit planned"]} second visits planned</span></summary>` +
      `<p class="note">Total = ${s["State-syllabus schools"]} State-syllabus + ${s["CBSE / ICSE schools"]} CBSE/ICSE + ${s["Found only in Aslam's log"]} found only in Aslam's log.</p>` + secs + `</details>`;
  }).join("");
  $("#p-method").innerHTML = `<div class="method">${DATA.method}</div>`;
}
function show(id){
  current = id;
  document.querySelectorAll("nav.tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab===id));
  document.querySelectorAll(".panel").forEach(p => p.classList.toggle("on", p.id==="p-"+id));
  try { localStorage.setItem("aslam-tab", id); } catch(e) {}
}
$("#tabs").addEventListener("click", e => { const b = e.target.closest("button"); if (b) show(b.dataset.tab); });
areaSel.addEventListener("change", render);
let t; $("#q").addEventListener("input", () => { clearTimeout(t); t = setTimeout(render, 150); });
$("#theme").addEventListener("click", () => {
  const r = document.documentElement, dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  r.dataset.theme = dark ? "light" : "dark";
});
render(); show(tabs.some(x=>x[0]===current) ? current : "summary");
</script>
</body>
</html>
"""

METHOD = """
<p><b>Sources compared.</b> Aslam's visit log ({visits} entries) was compared with Deepika's Malappuram list
({deepika} schools), the State-syllabus census ({state} schools), the CBSE/ICSE directory ({cbse} Malappuram
schools) and the free stay-pass feedback register ({freepass} entries).</p>
<p><b>Matching.</b> Schools were matched by phone number first, then by school type (AMLPS, GMUPS, HSS…) plus
place name, allowing for spelling variants (Tirurangadi/Thirurangadi, Kodinhi/Kodinji). Repeat visits to the same
school are counted once. Schools Aslam visited that are not in any official list (mostly private schools,
pre-schools and anganwadis) are added to the area totals as "found only in Aslam's log".</p>
<p><b>Areas.</b> Assembly constituencies as used in the State census. Places in Aslam's sheet were mapped using
the census school names; a few unclear places were taken from that day's route.</p>
<p><b>Second visit month.</b> From the "Second Visit" column in Aslam's sheet, checked against the tour period in
the call remarks (the sheet's rule is one month before the tour). Where the column was empty but a tour month was
given, the month was derived the same way and marked "Derived".</p>
<p><b>Confirmation probability.</b> Very High = used the free pass with positive feedback, or pass booked;
High = tour month given plus a positive response; Medium = positive response or tour month only;
Low = not reachable / busy / no remark yet; Very Low = wrong number, declined or not interested.
The latest visit's remarks decide the status.</p>
<p><b>Mobile numbers</b> are 10-digit numbers starting with 6–9; other numbers are landlines (shown with a
leading 0).</p>
"""


def build_html(T, path):
    data = {k: [{kk: vv for kk, vv in r.items() if not kk.startswith("_")} for r in v]
            for k, v in T.items() if isinstance(v, list)}
    st = dict(T["stats"])
    st["prob"] = dict(st["prob"])
    data["stats"] = st
    data["method"] = METHOD.format(**st["counts"])
    html = (TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__SHEETS__", json.dumps(SHEETS))
            .replace("__SUMMARY_COLS__", json.dumps(SUMMARY_COLS)))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    from report_tables import make_tables
    build_html(make_tables(), os.path.join(OUT, "Aslam_School_Report.html"))
    print("done")
