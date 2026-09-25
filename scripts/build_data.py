"""Cross-verify all sources and produce one structured dataset for the reports."""
import datetime as dt
import re
from collections import Counter, defaultdict

from rapidfuzz import fuzz

from load_data import (is_mobile, load_aslam, load_cbse_icse, load_deepika, load_free_pass,
                       load_state)
from matching import (AreaMapper, clean, levels_ok, name_score, phon, place_tokens, share_place,
                      type_code)

TODAY = dt.date(2026, 9, 25)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

# Places the automatic lookup gets wrong or cannot find (checked against the day's route).
PLACE_OVERRIDES = {
    "Tavanur": "Tavanur", "Pariyapuram": "Tanur", "Thennala": "Tirurangadi",
    "Puliyaparamba": "Tirurangadi", "Pullur": "Tirur", "Shanthinagar": "Tirur",
    "Kallingal": "Tirur", "Palapettyppara": "Vallikunnu", "Padikkal": "Vallikunnu",
    "Alungal": "Tirurangadi", "Ananthavoor": "Tirur", "Athanikkal": "Tirurangadi",
    "Schoolppadi": "Tirur", "Valiyaparambu": "Tirurangadi", "Pazhur": "Kottakkal",
    "Muttichira": "Tirurangadi", "Chettiyamkinar": "Tanur", "Angadi": "Tirur",
    "Payyanangadi": "Tirur", "Chettippadi": "Tirurangadi", "Illathpadam": "Tirur",
    "Nellikkad": "Tirur", "Puthanpeedika": "Tanur", "Puthanpedika": "Tanur", "PGDI": "Tirurangadi",
    "Cherulal": "Tirur", "Cherural": "Tirur", "Chilavilvailathoor": "Tanur",
    "Kooriyad": "Kottakkal", "Puthanangadi": "Vengara", "Nayadi": "Kottakkal",
    "Kakkidapara": "Tanur", "Mannarikal": "Tanur", "Mannarakkal": "Tanur",
    "Kohinoor": "Vallikunnu", "Kadappadi": "Vallikunnu", "Konnellur": "Tirur",
    "Thumarkkavu": "Tanur", "Olapeedika": "Tirurangadi", "Panaghattor": "Tanur",
    "Thazheppalam": "Tirur", "Thayyilakkadavu": "Vallikunnu", "Ottupuram": "Vallikunnu",
    "Mambra": "Tirur", "Kavumpuram": "Kottakkal", "Poonthottappadi": "Kottakkal",
    "Eranallur": "Tirurangadi", "Thoombathiparamba": "Tirurangadi",
    "Edayathuparamba": "Vengara", "Valiyaparappur": "Kottakkal", "Kalamkolliyala": "Vallikunnu",
    "Puthiyaparamba": "Tirurangadi", "Murikkal": "Tirurangadi", "Kurunkad": "Tanur",
    "Pandimuttam": "Tanur", "Chirakkal": "Tanur", "Puthukulangara": "Tanur",
    "Alankode": "Ponnani", "Nadakkavu": "Tanur",
}


# ------------------------------------------------------------------ helpers
def months_in(text):
    t = (text or "").lower()
    found = []
    for i, m in enumerate(MONTHS):
        if re.search(r"\b" + m[:3].lower() + r"[a-z]*", t):
            found.append(i + 1)
    if "sep" in t and 9 not in found:
        found.append(9)
    return sorted(set(found))


def parse_date(s):
    try:
        return dt.datetime.strptime(s, "%d.%m.%Y").date()
    except ValueError:
        return None


NEG_HARD = ["wrong", "invalied", "invalid", "incorrect", "unavailable", "not interested",
            "declined", "already visited another"]
NEG_SOFT = ["not connected", "not conne", "didn't conn", "switch", "voice", "not answer",
            "not incoming", "call cut", "cut call", "not sure", "busy", "call later",
            "call not answered", "not connnetced", "currently", "range issue", "transferred",
            "rerired", "retired", "not confirmed"]
POS_MED = ["will contact", "details shared", "shared the details", "share the details",
           "shared details", "follow up", "interested", "after discussion", "wp", "whatsapp",
           "connected"]


def probability(texts, fp=None, history=()):
    """Confirmation probability from the latest visit's remarks (+ tour months from earlier
    visits in `history`) and free-pass feedback."""
    t = " ".join(x for x in texts if x).lower()
    older = " ".join(x for x in history if x).lower()
    if fp:
        st = fp["status"].lower()
        if "not" in st:
            return "Very Low", "Free-pass feedback: not interested"
        if "interested" in st:
            return "Very High", "Used free pass; feedback 'Interested for group visit'"
        return "High", "Used free pass; neutral feedback"
    if "free pass booked" in t or "booked" in t:
        return "Very High", "Free pass booked"
    if any(k in t for k in NEG_HARD):
        return "Very Low", "Wrong/invalid number or not interested"
    tour = bool(months_in(t + " " + older)) or any(k in t + " " + older for k in ("tour time", "trip time", "onam"))
    pos = any(k in t for k in POS_MED)
    latest_bad = any(k in t for k in NEG_SOFT)
    if tour and ("interested" in t or "they will contact" in t or "details shared" in t
                 or "shared the details" in t or "follow" in t):
        if latest_bad:
            return "Medium", "Tour period given, but latest follow-up not successful"
        return "High", "Tour period given + positive response"
    if tour:
        return "Medium", "Tour period given"
    if pos and not latest_bad:
        return "Medium", "Positive response, no tour date yet"
    if pos and latest_bad:
        return "Low", "Mixed response; not reachable on follow-up"
    if latest_bad:
        return "Low", "Not reachable / busy"
    return "Low", "No call remark recorded yet"


def compatible(code, name, place, m, need_distinct=False):
    """Could visit-sheet school (code, name, place) be the directory school m?"""
    cm = m["code"]
    if not levels_ok(name, m["name"]):
        return False
    if code and cm:
        return code == cm or code.rstrip("S") == cm.rstrip("S")
    distinct = [t for t in place_tokens(name) if t not in place_tokens(place)]
    mtoks = place_tokens(m["name"])
    if distinct:
        if need_distinct:  # name-only evidence: every distinctive word must be present
            return all(share_place([t], mtoks) for t in distinct)
        return share_place(distinct, mtoks)
    if need_distinct:  # generic name such as "New U P School": compare whole strings
        return fuzz.token_sort_ratio(clean(m["name"]), clean(name + " " + place)) >= 80
    return True


PROB_ORDER = {"Very High": 0, "High": 1, "Medium": 2, "Low": 3, "Very Low": 4, "-": 5}


# ------------------------------------------------------------------ build
def build():
    visits = load_aslam()
    deepika = load_deepika()
    state = load_state()
    cbse = load_cbse_icse()
    freepass = load_free_pass()

    # ---- master list of State-syllabus schools (Deepika + State census merged)
    master, by_name = [], {}
    for s in state:
        rec = dict(name=s["name"], area=s["assembly"], block="", finance=s["finance"],
                   level=s["level"], phones=list(s["phones"]), in_deepika=False,
                   deepika_phone="", deepika_block="", in_state=True, board="State",
                   address="", email="")
        master.append(rec)
        by_name.setdefault(s["name"].upper(), rec)
    mapper = AreaMapper(state, key="assembly")
    mapper.add_overrides(PLACE_OVERRIDES)
    block_asm = defaultdict(Counter)  # Deepika block -> assemblies of the same schools in the census
    for d in deepika:
        if d["block"] and d["name"].upper() in by_name:
            block_asm[d["block"]][by_name[d["name"].upper()]["area"]] += 1
    for d in deepika:
        rec = by_name.get(d["name"].upper())
        if rec is None:
            cand = [m for m in master if not m["in_deepika"] and name_score(m["name"], d["name"]) >= 92
                    and type_code(m["name"]) == type_code(d["name"])]
            rec = cand[0] if cand else None
        if rec is None:
            area = mapper.lookup(d["name"]) or ""
            if d["block"] and block_asm[d["block"]] and area not in block_asm[d["block"]]:
                area = block_asm[d["block"]].most_common(1)[0][0]  # trust Deepika's block
            rec = dict(name=d["name"], area=area, block=d["block"],
                       finance=d["finance"], level="", phones=[], in_deepika=True, in_state=False,
                       board="State", address="", email="")
            master.append(rec)
        rec["in_deepika"] = True
        rec["deepika_phone"] = ", ".join(d["phones"])
        rec["deepika_block"] = d["block"]
        rec["deepika_sl"] = d["sl"]
        for p in d["phones"]:
            if p not in rec["phones"]:
                rec["phones"].append(p)
    for c in cbse:
        master.append(dict(name=c["name"], area=mapper.lookup(c["address"], c["name"]) or "",
                           block="", finance=f"{c['board']} (Unaided)", level="",
                           phones=list(c["phones"]), in_deepika=False, deepika_phone="",
                           deepika_block="", in_state=False, board=c["board"],
                           address=c["address"], email=c.get("email", "")))
    for m in master:
        m["code"] = type_code(m["name"])
        m["ptoks"] = place_tokens(m["name"] + " " + m["address"])
        m["visits"] = []

    # ---- area for each visit
    day_votes = defaultdict(Counter)
    for v in visits:
        v["area"] = mapper.lookup(v["place"], v["name"])
        v["area_note"] = ""
        if v["area"]:
            day_votes[v["date"]][v["area"]] += 1
    for v in visits:
        if not v["area"]:
            v["area"] = day_votes[v["date"]].most_common(1)[0][0]
            v["area_note"] = "area taken from that day's route"

    # ---- link visits to master schools
    phone_index = defaultdict(list)
    for m in master:
        for p in m["phones"]:
            phone_index[p].append(m)
    for v in visits:
        v["code"] = type_code(v["name"])
        v["ptoks"] = place_tokens(v["place"] + " " + v["name"])
        # geographic words only: the Place column plus known place names inside the school name
        last = clean(v["name"]).split()[-1:]  # a place name usually ends the school name
        v["gtoks"] = place_tokens(v["place"]) + [t for t in place_tokens(" ".join(last)) if phon(t) in mapper.votes]
        best, best_sc = None, 0
        for p in v["phones"]:
            for m in phone_index.get(p, []):
                if compatible(v["code"], v["name"], v["place"], m):
                    sc = 100 + name_score(m["name"], v["name"])
                    if sc > best_sc:
                        best, best_sc = m, sc
        if not best:
            for m in master:
                if not share_place(v["ptoks"], m["ptoks"]):
                    continue
                if v["code"] and m["code"] and v["code"] == m["code"] and levels_ok(v["name"], m["name"]) \
                        and (not v["gtoks"] or share_place(v["gtoks"], m["ptoks"])):
                    sc = 90 + name_score(m["name"], v["name"] + " " + v["place"]) / 10
                elif compatible(v["code"], v["name"], v["place"], m, need_distinct=True) and (
                        share_place(v["gtoks"], m["ptoks"]) if v["gtoks"] else m["area"] == v["area"]):
                    sc = 85 + name_score(m["name"], v["name"]) / 10
                else:
                    sc = 0
                if sc > best_sc:
                    best, best_sc = m, sc
        v["school"] = best
        v["match"] = ("phone" if best_sc >= 100 else "name + place") if best else ""
        if best:
            best["visits"].append(v)

    # ---- group repeat visits of the same school
    groups = []
    for v in sorted(visits, key=lambda x: (parse_date(x["date"]) or TODAY)):
        g = None
        for gg in groups:
            g0 = gg["visits"][0]
            lv_ok = levels_ok(v["name"], g0["name"])
            same_school = v["school"] is not None and v["school"] is gg["school"] and lv_ok
            codes_ok = not (v["code"] and g0["code"]) or v["code"] == g0["code"]
            same_phone = set(v["phones"]) & gg["phones"] and lv_ok and codes_ok and (
                name_score(v["name"], g0["name"]) >= 70 or (v["code"] and v["code"] == g0["code"])
                or share_place(place_tokens(v["place"]), place_tokens(g0["place"])))
            same_name = (name_score(v["name"], g0["name"]) >= 90 and lv_ok and codes_ok and v["place"]
                         and share_place(place_tokens(v["place"]), place_tokens(g0["place"])))
            if same_school or same_phone or same_name:
                g = gg
                break
        if g is None:
            g = dict(visits=[], phones=set(), school=v["school"])
            groups.append(g)
        g["visits"].append(v)
        g["phones"].update(v["phones"])
        if g["school"] is None:
            g["school"] = v["school"]

    fp_phone = defaultdict(list)
    for f in freepass:
        for p in f["phones"]:
            fp_phone[p].append(f)

    def find_fp(phones, name, place, code, area):
        for p in phones:
            if fp_phone.get(p):
                return None, fp_phone[p][0]
        for f in freepass:
            fcode = type_code(f["school"])
            ftoks = place_tokens(f["school"])
            if code and fcode == code and share_place(place_tokens(place) or place_tokens(name), ftoks) \
                    and name_score(f["school"], name + " " + place) >= 80:
                return None, f
            if not code and not fcode and compatible("", name, place,
                                                      dict(code="", name=f["school"]), need_distinct=True) \
                    and share_place(place_tokens(place), ftoks):
                return None, f
        return None, None

    schools = []
    for g in groups:
        vs = g["visits"]
        first, last = vs[0], vs[-1]
        m = g["school"]
        all_remarks = [x["remark"] for x in vs] + [x["second_remark"] for x in vs]
        phones = []
        for x in vs:
            for p in x["phones"]:
                if p not in phones:
                    phones.append(p)
        _, fp = find_fp(phones + (m["phones"] if m else []), first["name"], first["place"],
                        first["code"], first["area"])
        latest = next(([x["remark"], x["second_remark"]] for x in reversed(vs)
                       if x["remark"] or x["second_remark"]), [])
        prob, why = probability(latest, fp, history=all_remarks)
        planned = next((x["second_month"] for x in vs if x["second_month"]), "")
        tour_months = sorted({mm for r in all_remarks for mm in months_in(r)})
        area, area_note = first["area"], first["area_note"]
        if m and m["area"] and m["area"] != area:
            area, area_note = m["area"], f"official list places it in {m['area']}"
        schools.append(dict(
            name=first["name"], place=first["place"], area=area, area_note=area_note,
            type=first["type"] or (m["finance"] if m else ""), person=last["person"] or first["person"],
            phones=phones, strength=last["strength"] or first["strength"],
            dates=[x["date"] for x in vs], n_visits=len(vs),
            remark=" | ".join(dict.fromkeys(r for r in [x["remark"] for x in vs] if r)),
            second_remark=" | ".join(dict.fromkeys(r for r in [x["second_remark"] for x in vs] if r)),
            planned_month=planned, tour_months=tour_months, prob=prob, prob_why=why,
            fp=fp, master=m, in_deepika=bool(m and m["in_deepika"]),
            deepika_phone=m["deepika_phone"] if m else "", deepika_block=m["deepika_block"] if m else "",
            board=m["board"] if m else "", match=first["match"] or (vs[-1]["match"]),
        ))

    # ---- second visit verification
    for s in schools:
        pm, tm = s["planned_month"], s["tour_months"]
        s["second_status"], s["second_month"], s["second_check"] = "", "", ""
        if s["n_visits"] > 1:
            s["second_status"] = "Done"
            s["second_month"] = f"Visited again {s['dates'][-1]}"
            s["second_check"] = f"{s['n_visits']} visits: " + ", ".join(s["dates"])
            continue
        if pm:
            s["second_status"] = "Planned"
            s["second_month"] = pm
            pm_i = next((i + 1 for i, m in enumerate(MONTHS) if pm.startswith(m)), 9 if "Onam" in pm else 0)
            fut = [m for m in tm if m >= 9] or [m + 12 for m in tm if m < 9]
            if fut and pm_i:
                exp = (min(fut) - 1 - 1) % 12 + 1
                s["second_check"] = "OK - one month before tour" if pm_i in (exp, min(fut) % 12 or 12) \
                    else f"Check - tour month {', '.join(MONTHS[(x - 1) % 12] for x in fut)}"
            else:
                s["second_check"] = "OK"
        elif tm and s["prob"] not in ("Very Low",):
            fut = sorted([m for m in tm if m >= 9] + [m + 12 for m in tm if m < 6])
            if fut:
                target = fut[0] - 1
                s["second_status"] = "Planned"
                s["second_month"] = MONTHS[(target - 1) % 12]
                s["second_check"] = "Derived: one month before tour month (" + MONTHS[(fut[0] - 1) % 12] + ")"
        if s["second_status"] == "Planned":
            mi = next((i + 1 for i, m in enumerate(MONTHS) if s["second_month"].startswith(m)), 0)
            if "Onam" in s["second_month"] or mi == 9:
                s["second_check"] += " - DUE NOW (September)"

    # ---- scope: areas Aslam actually covered
    area_counts = Counter(s["area"] for s in schools)
    core = [a for a, n in area_counts.most_common() if n >= 3]
    visited_master = {id(s["master"]) for s in schools if s["master"]}
    pending = [m for m in master if m["area"] in core and id(m) not in visited_master]
    for m in pending:
        _, fp = find_fp(m["phones"], m["name"], m["address"], m["code"], m["area"])
        m["fp"] = fp
        m["prob"], m["prob_why"] = probability([], fp) if fp else ("-", "Not yet contacted")
        m["mobiles"] = [p for p in m["phones"] if is_mobile(p)]
        m["landlines"] = [p for p in m["phones"] if not is_mobile(p)]

    # ---- Deepika mobile sheet (Deepika schools in Aslam's areas having a mobile number)
    deepika_sheet = []
    for m in master:
        if not m["in_deepika"] or m["area"] not in core:
            continue
        dmob = [p for p in m["deepika_phone"].split(", ") if is_mobile(p)]
        if not dmob:
            continue
        s = next((x for x in schools if x["master"] is m), None)
        fp = s["fp"] if s else m.get("fp")
        prob = (s["prob"], s["prob_why"]) if s else (probability([], fp) if fp else ("-", "Not yet contacted"))
        deepika_sheet.append(dict(master=m, mobiles=dmob, visit=s, fp=fp, prob=prob[0], prob_why=prob[1]))

    fp_malappuram = []
    for i, f in enumerate(freepass):
        linked = next((s for s in schools if s["fp"] is f), None)
        linked_m = next((m for m in master if m.get("fp") is f), None)
        fp_malappuram.append(dict(fp=f, school=linked, master=linked_m))

    return dict(visits=visits, schools=schools, master=master, pending=pending, core=core,
                deepika_sheet=deepika_sheet, freepass=fp_malappuram, cbse=cbse,
                counts=dict(visits=len(visits), deepika=len(deepika), state=len(state),
                            cbse=len(cbse), freepass=len(freepass)))


if __name__ == "__main__":
    D = build()
    S = D["schools"]
    print(D["counts"], "unique schools", len(S), "core", D["core"])
    print("matched to master", sum(1 for s in S if s["master"]), "in deepika", sum(1 for s in S if s["in_deepika"]))
    print("pending", len(D["pending"]), Counter(m["area"] for m in D["pending"]))
    print("deepika sheet", len(D["deepika_sheet"]))
    print(Counter(s["prob"] for s in S))
    print(Counter(s["second_status"] for s in S))
    print("fp linked", sum(1 for s in S if s["fp"]))
    for s in S:
        if s["fp"]:
            print(" FP:", s["name"], s["place"], "<-", s["fp"]["school"], s["fp"]["status"])
