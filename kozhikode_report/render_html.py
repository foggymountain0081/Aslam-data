"""Render the interactive HTML report.  Usage: python3 render_html.py model.json out.html"""
import json, sys
import tables
from mapping import AREAS

T = tables.build(json.load(open(sys.argv[1])))
T["areas"] = AREAS
T["notes"] = tables.NOTES
T["today"] = tables.TODAY
T["prob_order"] = tables.PROB_ORDER
data = json.dumps(T, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kozhikode School Coverage</title>
<style>
:root{--bg:#f6f7f9;--card:#ffffff;--ink:#1f2933;--muted:#5f6b7a;--line:#dde2e8;--accent:#1d4e89;--head:#eaf0f7;--zebra:#f8fafc;
--vh:#0b6e4f;--hi:#2a8a4a;--me:#9a6a00;--lo:#8a4b2a;--aw:#5f6b7a;--bad:#b3261e;--chip:#eef2f7}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#111418;--card:#1a1f25;--ink:#e4e8ee;--muted:#9aa5b1;--line:#2c343d;
--accent:#8cb8ec;--head:#222a33;--zebra:#1e242b;--vh:#4cc79a;--hi:#6fcf8a;--me:#e0b04a;--lo:#e09a74;--aw:#9aa5b1;--bad:#ff8a80;--chip:#252d36}}
:root[data-theme="dark"]{--bg:#111418;--card:#1a1f25;--ink:#e4e8ee;--muted:#9aa5b1;--line:#2c343d;--accent:#8cb8ec;--head:#222a33;--zebra:#1e242b;
--vh:#4cc79a;--hi:#6fcf8a;--me:#e0b04a;--lo:#e09a74;--aw:#9aa5b1;--bad:#ff8a80;--chip:#252d36}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:20px 16px 8px;max-width:1400px;margin:0 auto}
h1{margin:0 0 4px;font-size:22px;color:var(--accent)}
.sub{color:var(--muted);font-size:13px}
main{max-width:1400px;margin:0 auto;padding:0 16px 40px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:14px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.kpi b{display:block;font-size:24px;color:var(--accent);font-variant-numeric:tabular-nums}
.kpi span{color:var(--muted);font-size:12px}
nav.tabs{display:flex;gap:4px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin:8px 0 12px;position:sticky;top:0;background:var(--bg);z-index:5;padding-top:6px}
nav.tabs button{border:0;background:none;color:var(--muted);padding:8px 10px;font:inherit;cursor:pointer;border-bottom:2px solid transparent}
nav.tabs button[aria-selected="true"]{color:var(--accent);border-color:var(--accent);font-weight:600}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.chip{border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:999px;padding:4px 10px;font:inherit;font-size:12.5px;cursor:pointer}
.chip[aria-pressed="true"]{background:var(--accent);color:var(--card);border-color:var(--accent)}
input[type=search]{flex:1 1 220px;min-width:0;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:14px}
h2{font-size:17px;margin:4px 0 6px;color:var(--accent)}
h3{font-size:14.5px;margin:14px 0 6px}
.note{color:var(--muted);font-size:12.5px;margin:2px 0 8px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{padding:5px 7px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--head);position:sticky;top:0;font-weight:600;white-space:nowrap}
tbody tr:nth-child(even){background:var(--zebra)}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.loc{color:var(--muted);font-size:11.5px}
.p{font-weight:600;white-space:nowrap}
.p-Very-high{color:var(--vh)}.p-High{color:var(--hi)}.p-Medium{color:var(--me)}.p-Low{color:var(--lo)}
.p-Awaiting-follow-up{color:var(--aw)}.p-Invalid-number,.p-Not-interested{color:var(--bad)}
a.tel{color:inherit;text-decoration:none;border-bottom:1px dotted var(--muted);white-space:nowrap}
.count{color:var(--muted);font-weight:400;font-size:12.5px}
.empty{color:var(--muted);padding:8px}
.theme{margin-left:auto}
@media print{nav.tabs,.controls,.theme{display:none}.tab{display:block!important}}
</style>
</head>
<body>
<header>
  <div style="display:flex;gap:8px;align-items:flex-start">
    <div><h1>School Visit &amp; Coverage Report – Kozhikode</h1>
    <div class="sub">Executive: <b>Arshad</b> · visits logged 13 Aug – 24 Sep 2026 · report date <span id="today"></span></div></div>
    <button class="chip theme" id="themeBtn" title="Switch light / dark">◐ Theme</button>
  </div>
</header>
<main>
  <div class="kpis" id="kpis"></div>
  <nav class="tabs" role="tablist" id="tabs"></nav>
  <div class="controls">
    <span class="note" style="margin:0">Area:</span><span id="areaChips"></span>
    <input type="search" id="q" placeholder="Search school, place, person or number…">
  </div>
  <div id="content"></div>
</main>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const tel = s => esc(s).replace(/\b([6-9]\d{9})\b/g, '<a class="tel" href="tel:+91$1">$1</a>');
const prob = p => p ? `<span class="p p-${p.replace(/ /g,"-")}">${esc(p)}</span>` : "";
const lines = xs => (xs && xs.length) ? xs.map(tel).join("<br>") : "–";
const nameCell = r => `<b>${esc(r.name)}</b>` + (r.locality && !r.name.toLowerCase().includes(r.locality.toLowerCase().slice(0,5)) ? `<div class="loc">${esc(r.locality)}</div>` : "");
let state = {tab: "summary", area: "All", q: ""};
try { const s = JSON.parse(localStorage.getItem("kkd-report") || "{}"); Object.assign(state, {tab: s.tab || "summary", area: s.area || "All"}); } catch(e) {}
const save = () => { try { localStorage.setItem("kkd-report", JSON.stringify({tab: state.tab, area: state.area})); } catch(e) {} };

$("#today").textContent = D.today;
const t = D.totals;
$("#kpis").innerHTML = [[t.schools,"schools in Arshad's areas"],[t.visited,"first visit done"],[t.pending,"first visit pending"],
  [t.pending_no_mobile,"pending with no mobile no."],[t.second_planned,"2nd-visit month fixed"],
  [(t.prob["Very high"]||0)+(t.prob["High"]||0),"very high / high probability"],[t.deepika_mobiles,"Deepika mobile numbers in area"]]
  .map(([v,l]) => `<div class="kpi"><b>${v}</b><span>${l}</span></div>`).join("");

const COLS = {
  visited: [["School / locality", nameCell],["Type", r=>esc(r.type)],["1st visit", r=>esc(r.date)+(r.executive!=="Arshad"?` <span class="loc">(${esc(r.executive)})</span>`:"")],
    ["Contact person – number", r=>lines(r.contacts)],["Str.", r=>esc(r.strength),"num"],["Latest follow-up", r=>esc(r.remark)+(r.feedback?`<div class="loc">Free-pass: ${esc(r.feedback)}</div>`:"")],
    ["Tour time", r=>esc(r.tour)],["2nd visit", r=>esc(r.second||"Not fixed")],["In Deepika", r=>esc(r.in_deepika)],["Probability", r=>prob(r.prob)]],
  plan: [["Area", r=>esc(r.area)],["School / locality", nameCell],["Contact person – number", r=>lines(r.contacts)],["Tour time", r=>esc(r.tour)],
    ["2nd visit (as logged)", r=>esc(r.second||"Not fixed")],["Probability", r=>prob(r.prob)],["Latest follow-up", r=>esc(r.remark)]],
  pending: [["Area", r=>esc(r.area)],["School", r=>`<b>${esc(r.name)}</b>`],["Type", r=>esc(r.type)],["Classes", r=>esc(r.level)],
    ["Mobile number(s)", r=>lines(r.mobiles)],["Other numbers", r=>lines(r.landlines)],["Source list", r=>esc(r.source)],["In Deepika", r=>esc(r.in_deepika)],
    ["Note", r=>r.feedback?`Free-pass: ${esc(r.feedback)}`:""]],
  nomobile: [["Area", r=>esc(r.area)],["School", r=>`<b>${esc(r.name)}</b>`],["Type", r=>esc(r.type)],["Classes", r=>esc(r.level)],
    ["Landline / other number", r=>r.landlines.length?lines(r.landlines):"No number in any list"],["Source list", r=>esc(r.source)],["In Deepika", r=>esc(r.in_deepika)]],
  dmobile: [["Area", r=>esc(r.area)],["Deepika no.", r=>esc(r.sno),"num"],["School (Deepika's list)", r=>`<b>${esc(r.name)}</b>`],["Block", r=>esc(r.block)],
    ["Type", r=>esc(r.finance)],["Deepika mobile", r=>`<b>${tel(r.mobile)}</b>`],["Visited?", r=>esc(r.visited)],["Visit", r=>esc(r.visit)],
    ["Executive's contact(s)", r=>lines(r.exec_contacts)],["Number check", r=>esc(r.same)],["Probability", r=>r.prob==="-"?"–":prob(r.prob)]],
  dcheck: [["Area", r=>esc(r.area)],["School visited", r=>`<b>${esc(r.name)}</b>`],["Visit place", r=>esc(r.locality)],["1st visit", r=>esc(r.date)],
    ["In Deepika's list?", r=>`<b>${esc(r.in_deepika)}</b>`],["Deepika phone", r=>tel(r.deepika_phone||"–")],["Executive's contact(s)", r=>lines(r.contacts)],["Probability", r=>prob(r.prob)]],
  feedback: [["Area", r=>esc(r.area)],["School (matched)", r=>`<b>${esc(r.school)}</b><div class="loc">${esc(r.fb_school)}</div>`],["Person – phone", r=>tel(r.person+" – "+r.phone)],
    ["Free-pass date / persons", r=>esc(r.park+" / "+r.persons)],["Executive", r=>esc(r.executive)],["Park opinion", r=>esc(r.park_opinion)],
    ["Glamping stay / opinion", r=>esc(r.glamping+" / "+r.stay)],["Feedback", r=>esc(r.feedback)],["Tour period", r=>esc(r.period)],["Final status", r=>esc(r.status)],
    ["Arshad visited?", r=>esc(r.visited)],["Probability", r=>r.prob in {"Very high":1,"High":1,"Medium":1,"Low":1,"Awaiting follow-up":1,"Invalid number":1,"Not interested":1}?prob(r.prob):esc(r.prob)]],
};
const inArea = r => state.area === "All" || r.area === state.area;
const matches = r => !state.q || JSON.stringify(r).toLowerCase().includes(state.q);
function tbl(kind, rows, hideArea) {
  rows = rows.filter(r => (r.area === undefined || inArea(r)) && matches(r));
  if (!rows.length) return `<div class="empty">No matching schools.</div>`;
  const cols = COLS[kind].filter(c => !(hideArea && c[0] === "Area"));
  return `<div class="tw"><table><thead><tr><th>#</th>${cols.map(c=>`<th>${c[0]}</th>`).join("")}</tr></thead><tbody>` +
    rows.map((r,i) => `<tr><td class="num">${i+1}</td>${cols.map(c=>`<td class="${c[2]||""}">${c[1](r)}</td>`).join("")}</tr>`).join("") + `</tbody></table></div>`;
}
const cnt = (rows) => rows.filter(r => inArea(r) && matches(r)).length;
const flat = o => D.areas.flatMap(a => o[a]);

const TABS = {
  summary: ["Summary", () => {
    const rows = D.summary.filter(r => state.area==="All" || r.area===state.area);
    const h = ["Area","Schools","1st visit done","Pending","Pending – mobile","Pending – no mobile","2nd month fixed","Visited & in Deepika","Very high","High","Medium","Low","Awaiting follow-up","Not int. / wrong no."];
    const body = rows.map(r => `<tr><td><b>${r.area}</b></td>${[r.total,r.visited,r.pending,r.pending_mobile,r.pending_no_mobile,r.second_planned,`${r.visited_in_deepika} of ${r.visited}`,
      r["p_Very high"],r.p_High,r.p_Medium,r.p_Low,r["p_Awaiting follow-up"],r["p_Not interested"]+r["p_Invalid number"]].map(x=>`<td class="num">${x}</td>`).join("")}</tr>`).join("");
    const tot = state.area==="All" ? `<tr><td><b>Total</b></td>${[t.schools,t.visited,t.pending,t.pending_mobile,t.pending_no_mobile,t.second_planned,`${t.visited_in_deepika} of ${t.visited}`,
      t.prob["Very high"]||0,t.prob.High||0,t.prob.Medium||0,t.prob.Low||0,t.prob["Awaiting follow-up"]||0,(t.prob["Not interested"]||0)+(t.prob["Invalid number"]||0)].map(x=>`<td class="num"><b>${x}</b></td>`).join("")}</tr>` : "";
    return `<div class="card"><h2>Area summary</h2>
      <p class="note">Compares Arshad's visit log with Deepika's list, the Kozhikode School Data (state-syllabus), the CBSE and ICSE lists and the free-pass feedback – only for the areas Arshad works in: Kozhikode South, Kozhikode North and Beypore in full, and the parts of Elathur and Kunnamangalam on his route. Elathur and Kunnamangalam constituencies have ${D.outside_route.Elathur} and ${D.outside_route.Kunnamangalam} more state-syllabus schools outside his route (Basheer's rural beat); they are not counted as pending.</p>
      <div class="tw"><table><thead><tr>${h.map(x=>`<th>${x}</th>`).join("")}</tr></thead><tbody>${body}${tot}</tbody></table></div></div>
      <div class="card"><h2>How confirmation probability is decided</h2><div class="tw"><table><tbody>
      ${[["Very high","School said 'almost confirmed', a visit/date is booked, or 'trip almost confirmed'."],["High","Tour month given AND details shared on WhatsApp, or free-pass feedback says Interested."],
        ["Medium","Tour month given, or 'will confirm after visit / meeting', 'discussing', details shared without a month."],["Low","Only 'call not answered / busy / waiting / not confirmed / not decided' so far."],
        ["Awaiting follow-up","Visited (mostly 24.09) but no follow-up call recorded yet."],["Invalid number","Wrong / invalid number recorded – use the directory number in the pending / Deepika sheets."],
        ["Not interested","School said not interested (or staff trip already done). The latest remark wins."]].map(([a,b])=>`<tr><td>${prob(a)}</td><td>${b}</td></tr>`).join("")}
      </tbody></table></div></div>`; }],
  area: ["Area-wise", () => D.areas.filter(a => state.area==="All"||a===state.area).map(a => {
    const s = D.summary.find(x => x.area===a);
    const sec = Object.values(D.plan).flat().filter(r => r.area===a);
    const dm = D.deepika_mobile.filter(r => r.area===a), fb = D.feedback.filter(r => r.area===a);
    return `<div class="card"><h2>${a}</h2><p class="note"><b>${s.total}</b> schools · first visit done <b>${s.visited}</b> · pending <b>${s.pending}</b> (${s.pending_mobile} with mobile, ${s.pending_no_mobile} without) · 2nd-visit month fixed <b>${s.second_planned}</b> · in Deepika's list ${s.deepika_in_area} (${s.deepika_mobiles} with mobile)${s.outside_route?` · ${s.outside_route} more schools in the constituency are outside Arshad's route`:""}</p>
      <h3>First visit done <span class="count">(${cnt(D.visited[a])})</span></h3>${tbl("visited", D.visited[a], true)}
      <h3>Second visits by month <span class="count">(${cnt(sec)})</span></h3>${tbl("plan", sec, true)}
      <h3>Pending first visit – with mobile <span class="count">(${cnt(D.pending_mobile[a])})</span></h3>${tbl("pending", D.pending_mobile[a], true)}
      <h3>Pending first visit – no mobile <span class="count">(${cnt(D.pending_nomobile[a])})</span></h3>${tbl("nomobile", D.pending_nomobile[a], true)}
      <h3>Deepika's mobile numbers <span class="count">(${cnt(dm)})</span></h3>${tbl("dmobile", dm, true)}
      ${fb.length?`<h3>Free-pass feedback <span class="count">(${cnt(fb)})</span></h3>${tbl("feedback", fb, true)}`:""}</div>`; }).join("")],
  plan: ["2nd visits by month", () => `<div class="card"><h2>Second visits by month</h2><p class="note">Month as written in Arshad's 'Second Visit' column (earliest month where a school has two). September items are due now.</p>` +
    Object.entries(D.plan).map(([m, rows]) => `<h3>${m} <span class="count">(${cnt(rows)})</span></h3>${tbl("plan", rows)}`).join("") +
    `<h3>Visited, still interested, no 2nd-visit month yet <span class="count">(${cnt(D.unplanned)})</span></h3><p class="note">Visits from 17.09 onward have no 2nd-visit month in the log yet; the tour time the school gave is shown.</p>${tbl("plan", D.unplanned)}</div>`],
  pending: ["Pending – with mobile", () => `<div class="card"><h2>Pending first visits – with mobile numbers <span class="count">(${cnt(flat(D.pending_mobile))})</span></h2><p class="note">In the lists but not yet in Arshad's log; at least one mobile number from the state-syllabus, Deepika or CBSE/ICSE list.</p>${tbl("pending", flat(D.pending_mobile))}</div>`],
  nomobile: ["Pending – no mobile", () => `<div class="card"><h2>Pending first visits – no mobile number <span class="count">(${cnt(flat(D.pending_nomobile))})</span></h2><p class="note">Only a landline (or nothing) in every list – needs a direct visit or landline call to get a coordinator's mobile.</p>${tbl("nomobile", flat(D.pending_nomobile))}</div>`],
  dmobile: ["Deepika mobiles", () => `<div class="card"><h2>Deepika's data – mobile numbers <span class="count">(${cnt(D.deepika_mobile)})</span></h2><p class="note">Deepika's list has ${t.deepika_in_area} schools in Arshad's areas; ${t.deepika_mobiles} have a mobile number and ${t.deepika_mobiles_visited} of those are visited. 'Number check' compares Deepika's mobile with the number the executive collected.</p>${tbl("dmobile", D.deepika_mobile)}</div>`],
  dcheck: ["In Deepika's list?", () => `<div class="card"><h2>Is each visited school in Deepika's list? <span class="count">(${cnt(D.deepika_check)})</span></h2><p class="note">${t.visited_in_deepika} of ${t.visited} visited schools are in Deepika's list. 'No' rows (listed first) are mostly unaided English-medium, CBSE/ICSE, anganwadis, colleges and tuition centres, which her state-syllabus list does not cover.</p>${tbl("dcheck", D.deepika_check)}</div>`],
  feedback: ["Free-pass feedback", () => `<div class="card"><h2>Free-pass / stay feedback – Arshad's areas <span class="count">(${cnt(D.feedback)})</span></h2><p class="note">${t.feedback_in_area} of ${t.feedback_total} feedback entries belong to schools in Arshad's areas (matched by phone and name).</p>${tbl("feedback", D.feedback)}</div>`],
  notes: ["Notes", () => `<div class="card"><h2>Method and data notes</h2>${D.notes.map(n=>`<p>${n}</p>`).join("")}</div>`],
};

function render() {
  $("#tabs").innerHTML = Object.entries(TABS).map(([k,[l]]) => `<button role="tab" aria-selected="${k===state.tab}" data-tab="${k}">${l}</button>`).join("");
  $("#areaChips").innerHTML = ["All", ...D.areas].map(a => `<button class="chip" aria-pressed="${a===state.area}" data-area="${a}">${a}</button>`).join(" ");
  $("#content").innerHTML = TABS[state.tab][1]();
}
document.addEventListener("click", e => {
  const b = e.target.closest("[data-tab],[data-area]"); if (!b) return;
  if (b.dataset.tab) state.tab = b.dataset.tab; else state.area = b.dataset.area;
  save(); render();
});
let timer; $("#q").addEventListener("input", e => { clearTimeout(timer); timer = setTimeout(() => { state.q = e.target.value.trim().toLowerCase(); render(); }, 150); });
$("#themeBtn").addEventListener("click", () => {
  const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = cur === "dark" ? "light" : "dark";
});
render();
</script>
</body>
</html>
"""
open(sys.argv[2], "w").write(HTML.replace("__DATA__", data))
print("wrote", sys.argv[2])
