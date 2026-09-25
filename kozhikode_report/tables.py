"""Turn model.json into the report's sheets (plain lists of rows) - shared by PDF and HTML."""
import re, collections
from mapping import AREAS

PROB_ORDER = ["Very high", "High", "Medium", "Low", "Awaiting follow-up", "Invalid number", "Not interested"]
MONTH_ORDER = ["September", "October", "November", "December", "January", "February", "March"]
TODAY = "25 Sep 2026"

NOTES = [
    "<b>Sources:</b> Arshad's visit sheet (13.08-24.09.2026, 308 contact rows, incl. 5 rows by Basheer in Palath/Payambra); "
    "Deepika's Kozhikode list (1,283 schools, block-wise + city list); Kozhikode School Data (1,277 schools, by assembly "
    "constituency); CBSE and ICSE Kerala school lists (Kozhikode part: 99 CBSE, 4 ICSE); free-pass feedback sheet (84 entries).",
    "<b>Matching:</b> every school in Arshad's log was checked by hand against the directories (name + place, confirmed by "
    "phone number where both lists have one). Sections of one institution (LP/UP/HS/HSS) are matched to the single directory "
    "entry. A few matches are best judgement and should be checked on the next visit: 'Govt HS/HSS Pantheerankavu' = "
    "'Pantheerankave H.S.' (listed as Aided), 'P.B.M. English Medium School Chaliyam' = 'Hajee P.B.M.K.U.P.S.', "
    "'MIMLP School Puthiyapalam' = 'Muneerul Islam L.P.S.', 'NSS UP School Meenchanda' = 'N.S.S. U.P.S. Beypore', "
    "'Govt UP School Paimbra' (Basheer) = 'G.H.S.S. Payambra'.",
    "<b>Areas:</b> the area of a school is its assembly constituency in the Kozhikode School Data. Schools that are only in "
    "Arshad's log were given the area of their place. Deepika's list covers all 389 state-syllabus schools of these "
    "constituencies (every one matched), so 'In Deepika list = No' means the school is outside the state-syllabus list "
    "(private unaided, CBSE/ICSE, anganwadi, college, tuition centre) - not that it was missed.",
    "<b>Mobile vs landline:</b> a mobile is a 10-digit number starting 6-9. Landlines in the lists are stored without the "
    "leading 0 (e.g. 4952414565 = 0495 2414565) and are shown in that form. Where the state-syllabus list and Deepika's "
    "list give different numbers for the same school, both are shown.",
    "<b>Second visit:</b> taken from Arshad's 'Second Visit' column. It is blank for visits from 17.09 onward; those "
    "schools are listed under 'no 2nd-visit month fixed yet' with the tour time they gave.",
    "<b>Free-pass feedback:</b> matched to Arshad's areas by phone number (4 of 5 match a contact in his log exactly; "
    "'salman, AMLP School Arathilparamba' 9846438183 matches Arshad's 'Salman, A.M.L.P School Paramba' 9846431883 by "
    "name and place). J.D.T. Islam A.L.P.S. Merikkunnu is interested in a group visit (via Nidhin) but Arshad has not visited it yet.",
    "<b>Numbers to fix:</b> 6 schools have a wrong/invalid number in the log (e.g. G.U.P.S. Panniyankara - directory "
    "number 0495 2320180; St. Joseph's Anglo-Indian Girls HSS - 0495 2366932 recorded as mobile).",
]


def contacts_text(s):
    out = []
    for u in s["visits"]:
        for c in u["contacts"]:
            if c["person"] or c["phone"]:
                out.append(f'{c["person"]} - {c["phone"]}'.strip(" -"))
    return list(dict.fromkeys(out))


def latest_remark(s):
    parts = []
    for u in s["visits"]:
        seq = [x for x in (u["direct_call"], u["second_remarks"]) if x]
        if seq:
            parts.append(" -> ".join(seq))
    txt = " | ".join(dict.fromkeys(parts))
    return txt if len(txt) < 170 else txt[:167] + "..."


def first_month(label):
    for m in MONTH_ORDER:
        if m in (label or ""):
            idx = [label.find(x) for x in MONTH_ORDER if x in label]
            return min((label.find(x), x) for x in MONTH_ORDER if x in label)[1]
    return ""


def type_of(s):
    if s["visits"] and s["visits"][0]["type"]:
        t = s["visits"][0]["type"].rstrip(".")
        return {"Government": "Govt", "Special School": "Special"}.get(t, t)
    return {"Government": "Govt", "Unaided Recognised": "Private", "Aided": "Aided"}.get(s["finance"], s["finance"])


def feedback_text(s):
    out = []
    for f in s["feedback"]:
        st = f["final_status"].replace("Intrested", "Interested").replace("Nuetral", "Neutral") or "no status"
        out.append(f'{f["person"]} ({f["date"]}): {f["feedback"] or "-"}; stay: {f["glamping"] or "-"}; status: {st}')
    return " | ".join(out)


def build(model):
    S = model["schools"]
    by_area = collections.OrderedDict((a, [s for s in S if s["area"] == a]) for a in AREAS)
    for a in by_area:
        by_area[a].sort(key=lambda s: (not s["visited"], s["name"].lower()))

    visited = [s for s in S if s["visited"]]
    pending = [s for s in S if not s["visited"]]

    summary = []
    for a, ss in by_area.items():
        v = [s for s in ss if s["visited"]]
        p = [s for s in ss if not s["visited"]]
        pc = collections.Counter(s["probability"] for s in v)
        summary.append(dict(
            area=a, total=len(ss), visited=len(v), pending=len(p),
            pending_mobile=sum(1 for s in p if s["directory_mobiles"]),
            pending_no_mobile=sum(1 for s in p if not s["directory_mobiles"]),
            second_planned=sum(1 for s in v if s["second_visit"]),
            visited_in_deepika=sum(1 for s in v if s["in_deepika"]),
            deepika_in_area=sum(1 for s in ss if s["in_deepika"]),
            deepika_mobiles=sum(1 for s in ss if s["in_deepika"] and re.fullmatch(r"[6-9]\d{9}", s["deepika"]["phone"] or "")),
            feedback=sum(len(s["feedback"]) for s in ss),
            outside_route=model["outside_route"].get(a, 0),
            **{"p_" + k: pc.get(k, 0) for k in PROB_ORDER}))

    def vrow(s):
        return dict(area=s["area"], name=s["name"], locality=s["locality"], type=type_of(s),
                    date=s["first_date"], executive=", ".join(s["visited_by"]),
                    contacts=contacts_text(s), strength=max((u["strength"] for u in s["visits"]), key=lambda x: int(re.sub(r"\D", "", x) or 0)),
                    remark=latest_remark(s), tour=s["tour_window"], second=s["second_visit"],
                    in_deepika="Yes" if s["in_deepika"] else "No",
                    deepika_phone=(s["deepika"]["phone"] if s["deepika"] else ""),
                    prob=s["probability"], feedback=feedback_text(s), units=len(s["visits"]))

    def prow(s):
        return dict(area=s["area"], name=s["name"], type=type_of(s), level=s["level"], source=", ".join(s["source"]),
                    mobiles=s["directory_mobiles"],
                    landlines=[p for p in s["directory_numbers"] if p not in s["directory_mobiles"]],
                    in_deepika="Yes" if s["in_deepika"] else "No", feedback=feedback_text(s))

    visited_rows = {a: [vrow(s) for s in ss if s["visited"]] for a, ss in by_area.items()}
    pending_mobile = {a: [prow(s) for s in ss if not s["visited"] and s["directory_mobiles"]] for a, ss in by_area.items()}
    pending_nomobile = {a: [prow(s) for s in ss if not s["visited"] and not s["directory_mobiles"]] for a, ss in by_area.items()}

    # second visit plan by month
    plan = collections.OrderedDict((m, []) for m in MONTH_ORDER)
    unplanned = []
    for s in visited:
        m = first_month(s["second_visit"])
        r = vrow(s)
        if m:
            plan[m].append(r)
        elif s["probability"] not in ("Not interested", "Invalid number"):
            unplanned.append(r)
    for m in plan:
        plan[m].sort(key=lambda r: (AREAS.index(r["area"]), PROB_ORDER.index(r["prob"]), r["name"]))
    plan = collections.OrderedDict((m, v) for m, v in plan.items() if v)
    unplanned.sort(key=lambda r: (AREAS.index(r["area"]), PROB_ORDER.index(r["prob"]), r["name"]))

    # Deepika mobile sheet (Arshad's areas only)
    deepika_mobile = []
    for s in S:
        d = s["deepika"]
        if not d or not re.fullmatch(r"[6-9]\d{9}", d["phone"] or ""):
            continue
        exec_nums = [re.sub(r"\D", "", c["phone"]) for u in s["visits"] for c in u["contacts"]]
        same = any(d["phone"] in n for n in exec_nums)
        deepika_mobile.append(dict(
            area=s["area"], sno=d["sno"], name=d["name"], block=d["block"] or "(no block - city list)",
            finance=d["finance"], mobile=d["phone"], visited="Yes" if s["visited"] else "No",
            visit=(f'{s["first_date"]} by {", ".join(s["visited_by"])}' if s["visited"] else "Not visited yet"),
            exec_contacts=contacts_text(s), same=("Same number" if same else ("Different number" if s["visited"] else "-")),
            prob=s["probability"] or "-"))
    deepika_mobile.sort(key=lambda r: (AREAS.index(r["area"]), r["visited"] == "Yes", r["name"].lower()))

    deepika_check = [vrow(s) for s in visited]
    deepika_check.sort(key=lambda r: (AREAS.index(r["area"]), r["in_deepika"] == "Yes", r["name"].lower()))

    feedback_rows = []
    for f in model["feedback_in_area"]:
        s = next(x for x in S if x["key"] == f["school_key"])
        feedback_rows.append(dict(area=s["area"], school=s["name"], fb_school=f["school"], person=f["person"],
                                  phone=f["phone"], date=f["date"], park=f["park_visit"], persons=f["persons"],
                                  executive=f["executive"] or "-", park_opinion=f["park_opinion"] or "-",
                                  glamping=f["glamping"] or "-", stay=f["stay_opinion"] or "-",
                                  feedback=f["feedback"] or "-", period=f["tour_period"] or "-",
                                  status=(f["final_status"].replace("Intrested", "Interested").replace("Nuetral", "Neutral") or "Not recorded"),
                                  visited="Yes" if s["visited"] else "No (first visit pending)",
                                  prob=s["probability"] or "First visit pending"))

    totals = dict(
        schools=len(S), visited=len(visited), pending=len(pending),
        pending_mobile=sum(1 for s in pending if s["directory_mobiles"]),
        pending_no_mobile=sum(1 for s in pending if not s["directory_mobiles"]),
        second_planned=sum(1 for s in visited if s["second_visit"]),
        visit_rows=model["visit_rows"], units=model["visit_units"],
        visited_in_deepika=sum(1 for s in visited if s["in_deepika"]),
        deepika_in_area=sum(1 for s in S if s["in_deepika"]),
        deepika_mobiles=len(deepika_mobile),
        deepika_mobiles_visited=sum(1 for r in deepika_mobile if r["visited"] == "Yes"),
        feedback_in_area=len(feedback_rows), feedback_total=len(model["feedback_in_area"]) + len(model["feedback_other"]),
        prob=collections.Counter(s["probability"] for s in visited))
    return dict(summary=summary, visited=visited_rows, pending_mobile=pending_mobile,
                pending_nomobile=pending_nomobile, plan=plan, unplanned=unplanned,
                deepika_mobile=deepika_mobile, deepika_check=deepika_check, feedback=feedback_rows,
                totals=totals, outside_route=model["outside_route"])
