"""Turn the cross-verified dataset into the report sheets (lists of row dicts)."""
from collections import Counter, OrderedDict

from build_data import MONTHS, PROB_ORDER, TODAY, build, parse_date
from load_data import is_mobile


def display_name(name, place):
    if place and place.lower().split(",")[0].split("(")[0].strip() not in name.lower():
        return f"{name}, {place}"
    return name


def fmt_phones(phones, mobile_only=False):
    ps = [p for p in phones if is_mobile(p)] if mobile_only else phones
    return ", ".join(ps)


def fp_text(fp):
    if not fp:
        return ""
    bits = [f"{fp['status'] or 'No status'}"]
    if fp["feedback"]:
        bits.append(fp["feedback"])
    if fp["tour_period"]:
        bits.append(f"tour {fp['tour_period']}")
    return f"Visited park {fp['date']} ({fp['persons']} pax): " + "; ".join(bits)


def _month_key(label):
    if "Onam" in label:
        return 9
    for i, m in enumerate(MONTHS):
        if label.startswith(m):
            return i + 1 if i + 1 >= 6 else i + 13
    return 99


def make_tables():
    D = build()
    core = D["core"]
    areas = core + (["Other"] if any(s["area"] not in core for s in D["schools"]) else [])

    def area_of(a):
        return a if a in core else "Other"

    # ---------------------------------------------------------------- visited schools
    visited = []
    for s in sorted(D["schools"], key=lambda x: (areas.index(area_of(x["area"])), parse_date(x["dates"][0]) or TODAY)):
        m = s["master"]
        if s["in_deepika"]:
            dk = f"Yes - Sl {m.get('deepika_sl', '')}, {m['deepika_block'] or 'no block'}"
            if m["deepika_phone"]:
                dk += f", ph {m['deepika_phone']}"
        else:
            dk = "No"
        listed = {"State": "State census", "CBSE": "CBSE list", "ICSE": "ICSE list"}.get(m["board"], "") if m else ""
        visited.append(OrderedDict([
            ("Area", area_of(s["area"])),
            ("First visit", s["dates"][0]),
            ("School", display_name(s["name"], s["place"])),
            ("Type", s["type"]),
            ("Contact person", s["person"]),
            ("Contact no.", fmt_phones(s["phones"])),
            ("Strength", s["strength"]),
            ("Visits", str(s["n_visits"]) + (f" ({', '.join(s['dates'][1:])})" if s["n_visits"] > 1 else "")),
            ("Call remarks", " / ".join(x for x in [s["remark"], s["second_remark"]] if x)),
            ("In Deepika data", dk),
            ("Official list", listed or "Not listed"),
            ("Free-pass feedback", fp_text(s["fp"])),
            ("Probability", s["prob"]),
            ("_why", s["prob_why"]),
            ("_mobile", any(is_mobile(p) for p in s["phones"])),
        ]))

    # ---------------------------------------------------------------- second visits
    second = []
    for s in D["schools"]:
        if not s["second_status"]:
            continue
        tour = ", ".join(MONTHS[m - 1] for m in s["tour_months"]) if s["tour_months"] else ""
        second.append(OrderedDict([
            ("Second visit month", s["second_month"] if s["second_status"] == "Planned" else "Already revisited"),
            ("Area", area_of(s["area"])),
            ("School", display_name(s["name"], s["place"])),
            ("Contact person", s["person"]),
            ("Contact no.", fmt_phones(s["phones"])),
            ("First visit", s["dates"][0]),
            ("Tour period (remarks)", tour),
            ("Status", s["second_status"]),
            ("Verification", s["second_check"]),
            ("In Deepika data", "Yes" if s["in_deepika"] else "No"),
            ("Probability", s["prob"]),
            ("_key", (0 if s["second_status"] == "Planned" else 1, _month_key(s["second_month"]),
                      areas.index(area_of(s["area"])))),
        ]))
    second.sort(key=lambda r: r["_key"])

    # ---------------------------------------------------------------- pending first visit
    pend_mob, pend_nomob = [], []
    for m in sorted(D["pending"], key=lambda x: (areas.index(x["area"]), x["board"] != "State", x["name"])):
        src = "CBSE list" if m["board"] == "CBSE" else ("ICSE list" if m["board"] == "ICSE" else
                                                        ("Deepika + State census" if m["in_deepika"] and m["in_state"]
                                                         else "Deepika data" if m["in_deepika"] else "State census"))
        base = OrderedDict([
            ("Area", m["area"]),
            ("School", m["name"]),
            ("Type", m["finance"]),
            ("Classes", m["level"]),
        ])
        if m["mobiles"]:
            row = OrderedDict(base)
            row["Mobile no."] = ", ".join(m["mobiles"])
            row["Other no."] = ", ".join(m["landlines"])
            row["In Deepika data"] = "Yes" if m["in_deepika"] else "No"
            row["Source"] = src
            row["Free-pass feedback"] = fp_text(m.get("fp"))
            row["Probability"] = m["prob"]
            pend_mob.append(row)
        else:
            row = OrderedDict(base)
            row["Landline"] = ", ".join("0" + p for p in m["landlines"]) or "No number"
            row["In Deepika data"] = "Yes" if m["in_deepika"] else "No"
            row["Source"] = src
            pend_nomob.append(row)

    # ---------------------------------------------------------------- Deepika mobile sheet
    deepika = []
    for d in sorted(D["deepika_sheet"], key=lambda x: (areas.index(x["master"]["area"]), x["master"]["deepika_sl"])):
        m, s = d["master"], d["visit"]
        deepika.append(OrderedDict([
            ("Area", m["area"]),
            ("Deepika Sl", str(m["deepika_sl"])),
            ("School", m["name"]),
            ("Deepika block", m["deepika_block"] or "(blank)"),
            ("Type", m["finance"]),
            ("Mobile (Deepika)", ", ".join(d["mobiles"])),
            ("Visited by executive", f"Yes - Aslam, {', '.join(s['dates'])}" if s else "No - not yet visited"),
            ("Executive's remark", " / ".join(x for x in [s["remark"], s["second_remark"]] if x) if s else ""),
            ("Free-pass feedback", fp_text(d["fp"])),
            ("Probability", d["prob"]),
        ]))

    # ---------------------------------------------------------------- free-pass feedback (Aslam's areas)
    freepass = []
    for x in D["freepass"]:
        f, s, m = x["fp"], x["school"], x["master"]
        if not s and not m:
            continue
        area = area_of(s["area"]) if s else m["area"]
        freepass.append(OrderedDict([
            ("Area", area),
            ("Park visit", f["date"]),
            ("Person", f["person"]),
            ("Contact", f["contact"]),
            ("School (feedback form)", f["school"]),
            ("Matched school", display_name(s["name"], s["place"]) if s else m["name"]),
            ("Visited by Aslam", f"Yes - {', '.join(s['dates'])}" if s else "No - pending first visit"),
            ("Persons", f["persons"]),
            ("Executive (form)", f["executive"]),
            ("Glamping stay", f["glamping"]),
            ("Feedback", f["feedback"]),
            ("Tour period", f["tour_period"]),
            ("Final status", f["status"]),
            ("Probability", s["prob"] if s else m["prob"]),
        ]))

    # ---------------------------------------------------------------- area summary
    summary = []
    for a in areas:
        census = sum(1 for m in D["master"] if m["area"] == a and m["board"] == "State") if a != "Other" else 0
        cb = sum(1 for m in D["master"] if m["area"] == a and m["board"] != "State") if a != "Other" else 0
        vis = [r for r in visited if r["Area"] == a]
        extra = sum(1 for r in vis if r["Official list"] == "Not listed")
        pm = sum(1 for r in pend_mob if r["Area"] == a)
        pn = sum(1 for r in pend_nomob if r["Area"] == a)
        sd = [r for r in second if r["Area"] == a]
        dk = [r for r in deepika if r["Area"] == a]
        summary.append(OrderedDict([
            ("Area", a),
            ("State-syllabus schools", census),
            ("CBSE / ICSE schools", cb),
            ("Found only in Aslam's log", extra),
            ("Total schools", census + cb + extra),
            ("Visited (unique)", len(vis)),
            ("Pending 1st visit", pm + pn),
            ("- with mobile", pm),
            ("- no mobile", pn),
            ("2nd visit done", sum(1 for r in sd if r["Status"] == "Done")),
            ("2nd visit planned", sum(1 for r in sd if r["Status"] == "Planned")),
            ("Deepika mobiles", len(dk)),
            ("Deepika visited", sum(1 for r in dk if r["Visited by executive"].startswith("Yes"))),
            ("High / Very High", sum(1 for r in vis if r["Probability"] in ("High", "Very High"))),
        ]))
    tot = OrderedDict([("Area", "TOTAL")])
    for k in list(summary[0].keys())[1:]:
        tot[k] = sum(r[k] for r in summary)
    summary.append(tot)

    stats = dict(
        counts=D["counts"], areas=areas, core=core,
        unique_visited=len(visited), visit_entries=len(D["visits"]),
        in_deepika=sum(1 for r in visited if r["In Deepika data"] != "No"),
        listed=sum(1 for r in visited if r["Official list"] != "Not listed"),
        pending=len(pend_mob) + len(pend_nomob), pend_mob=len(pend_mob), pend_nomob=len(pend_nomob),
        second_planned=sum(1 for r in second if r["Status"] == "Planned"),
        second_done=sum(1 for r in second if r["Status"] == "Done"),
        due_now=sum(1 for r in second if "DUE NOW" in r["Verification"]),
        derived=sum(1 for r in second if r["Verification"].startswith("Derived")),
        deepika_mob=len(deepika), deepika_visited=sum(1 for r in deepika if r["Visited by executive"].startswith("Yes")),
        freepass=len(freepass), prob=Counter(r["Probability"] for r in visited),
        visited_nomob=sum(1 for r in visited if not r["_mobile"]),
        today=TODAY.strftime("%d %B %Y"),
        first_date=min(D["visits"], key=lambda v: parse_date(v["date"]) or TODAY)["date"],
        last_date=max(D["visits"], key=lambda v: parse_date(v["date"]) or TODAY)["date"],
    )
    return dict(summary=summary, visited=visited, second=second, pend_mob=pend_mob,
                pend_nomob=pend_nomob, deepika=deepika, freepass=freepass, stats=stats)


if __name__ == "__main__":
    T = make_tables()
    for k, v in T.items():
        if isinstance(v, list):
            print(k, len(v))
    for r in T["summary"]:
        print(dict(r))
    print(T["stats"])
