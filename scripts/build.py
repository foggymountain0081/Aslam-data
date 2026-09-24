"""Cross-check Musthafa's visits against the school directories and build the report dataset."""
import json, re, sys, collections, difflib
from datetime import date
from common import *

M = json.load(open(sys.argv[1]))
SRC = json.load(open(sys.argv[2]))
OUT = sys.argv[3]
TODAY = date(2026, 9, 24)

nrm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())

# ---------------------------------------------------------------- localities
AREA_ORDER = ["Manjeri", "Ernad", "Nilambur", "Mankada", "Wandoor", "Perinthalmanna", "Kondotty",
              "Malappuram", "Tirur", "Ponnani", "Tavanur", "Tanur", "Other Localities"]
loc_area = {}
for v in M["visited"]:
    v["locality"] = LOC_FIX.get(v["locality"], v["locality"])
    loc_area.setdefault(v["locality"], v["area"])
loc_keys = {l: phon(l) for l in loc_area}


loc_asm = collections.defaultdict(set)   # assemblies each locality is known to belong to


def pick_loc(hits, assembly=None, text=""):
    if not hits:
        return None
    if assembly:
        # a State-sheet school must sit in the same assembly as Musthafa's area, or the assembly of a
        # school he visited in that locality (Other Localities excepted)
        hits = [h for h in hits if assembly in (loc_asm[h] or {loc_area[h]}) or loc_area[h] == "Other Localities"]
        if not hits:
            return None
    # most specific: longest name, then the one written last in the school name ("Mankada Pallippuram")
    low = text.lower()
    return max(hits, key=lambda h: (len(loc_keys[h]), low.rfind(h.lower()[:5])))


# ---------------------------------------------------------------- master directory
master = []  # one row per real school
by_phone = collections.defaultdict(list)


def add(rec):
    rec["id"] = len(master)
    master.append(rec)
    for p in rec["phones"]:
        by_phone[p].append(rec)
    return rec


for r in SRC["state"]:
    ph, ok, allp = best_phone(r["phone"])
    add(dict(name=r["name"], board="State", mgmt={"Government": "Govt", "Aided": "Aided"}.get(r["finance"], "Unaided"),
             assembly=r["assembly"], block="", level=r["level"], phone=ph, phone_ok=ok, phones=allp,
             raw_phone=r["phone"], address="", src="State syllabus list", deepika=None))

state_by_name = {nrm(m["name"]): m for m in master}
deepika_by_name = {}
for r in SRC["deepika"]:
    ph, ok, allp = best_phone(r["phone"])
    twin = state_by_name.get(nrm(r["name"]))
    if not twin and ph:
        cands = [m for m in by_phone.get(ph, []) if m["board"] == "State" and m["deepika"] is None
                 and (code(m["name"]) == code(r["name"]) or key_words(m["name"]) & key_words(r["name"]))]
        twin = cands[0] if cands else None
    if twin:
        twin["deepika"] = r
        twin["block"] = r["block"]
        if not twin["phone_ok"] and ok:
            twin.update(phone=ph, phone_ok=ok)
    else:
        twin = add(dict(name=r["name"], board="State", mgmt={"Government": "Govt", "Aided": "Aided"}.get(r["finance"], "Unaided"),
                        assembly="", block=r["block"], level="", phone=ph, phone_ok=ok, phones=allp,
                        raw_phone=r["phone"], address="", src="Deepika sheet only", deepika=r))
    deepika_by_name[nrm(r["name"])] = twin

for r in SRC["cbse"] + SRC["icse"]:
    ph, ok, allp = best_phone(r["phone"])
    add(dict(name=r["name"], board=r["board"], mgmt="Unaided", assembly="", block="", level="",
             phone=ph, phone_ok=ok, phones=allp, raw_phone=r["phone"], address=r["address"],
             src=f"{r['board']} directory", deepika=None))

# ---------------------------------------------------------------- visited -> directory links
def clean_name(s):
    return re.sub(r"\s*Free pass used.*$", "", s).strip()


visited = []
for v in M["visited"]:
    name = clean_name(v["school"])
    ph = digits(v.get("phone"))
    rec = dict(area=v["area"], locality=v["locality"], name=name, mtype=v.get("type", "—"),
               contact=v.get("contact", ""), phone=ph, first=v.get("first", ""), next=v.get("next", ""),
               m_deepika=v.get("deepika") == "Yes", m_detail=v.get("deepika_detail", ""), link=None, how="")
    lk = {phon(w) for w in words(v["locality"])}
    # 1. Deepika name recorded in Musthafa's report
    if rec["m_detail"] and rec["m_detail"] != "block blank":
        dn = nrm(re.sub(r"\s*\([^)]*\)\s*$", "", rec["m_detail"]))
        if dn in deepika_by_name:
            rec["link"], rec["how"] = deepika_by_name[dn], "Deepika name"
    # 2. same phone number, same kind of school
    if not rec["link"] and ph:
        for m in by_phone.get(ph, []):
            rec["link"], rec["how"] = m, "phone"
            break
    visited.append(rec)

for rec in visited:
    if rec["link"] and rec["link"]["assembly"]:
        loc_asm[rec["locality"]].add(rec["link"]["assembly"])

# locality for each directory school
for m in master:
    text = m["name"] + (" " + m["address"] if m["address"] else "")
    hits = loc_hits(m["name"], loc_keys) or (loc_hits(m["address"], loc_keys) if m["address"] else [])
    m["locality"] = pick_loc(hits, m["assembly"] or None, text)
    m["area"] = loc_area.get(m["locality"])

loc_master = collections.defaultdict(list)
for m in master:
    if m["locality"]:
        loc_master[m["locality"]].append(m)

area_master = collections.defaultdict(list)
for m in master:
    if m["area"]:
        area_master[m["area"]].append(m)
taken = {rec["link"]["id"] for rec in visited if rec["link"]}
for rec in visited:
    v, name, lk = rec, rec["name"], {phon(w) for w in words(rec["locality"])}
    # 3. same school code / distinctive words inside the same locality (then anywhere in the same area)
    if not rec["link"]:
        best = (0, None)
        for m in loc_master.get(v["locality"], []):
            sc = name_score(name, m["name"], lk)
            if sc:
                sc += 0.5 if m["id"] not in taken else 0
                sc += difflib.SequenceMatcher(None, code(name, lk), code(m["name"], lk)).ratio() / 10
            if sc >= 1 and sc > best[0]:
                best = (sc, m)
        if not best[1]:
            for m in area_master.get(v["area"], []):
                d2 = lk | {phon(w) for w in words(m["locality"] or "")}
                distinctive = {w for w in key_words(name, d2) & key_words(m["name"], d2) if len(w) >= 3}
                if m["id"] not in taken and distinctive and name_score(name, m["name"], d2) >= 2:
                    best = (2, m)
                    rec["area_wide"] = True
                    break
        if best[1]:
            rec["link"], rec["how"] = best[1], "name+locality"
    if rec["link"]:
        taken.add(rec["link"]["id"])

linked_ids = collections.Counter(v["link"]["id"] for v in visited if v["link"])

# ---------------------------------------------------------------- 2nd visit month check
MON = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def second_visit(v):
    n = v["next"]
    d, mth, yr = (int(x) for x in v["first"].split(".")) if re.match(r"\d\d\.\d\d\.\d{4}", v["first"]) else (0, 0, 0)
    first = date(yr, mth, d) if yr else None
    if n.startswith("2nd visit:"):
        mo, y = n.split(":")[1].split()
        sm = (int(y), MON[mo])
    elif n.startswith("Visit before 30 Sep"):
        sm = (2026, 9)
    elif n.startswith("OVERDUE"):
        sm = (2026, 8)
    elif n.startswith("Hot lead"):
        return dict(month="Not fixed", key=(0, 0), status="Hot lead – fix date now", check="No month given")
    else:
        return None
    label = date(sm[0], sm[1], 1).strftime("%b %Y")
    now = (TODAY.year, TODAY.month)
    if sm < now:
        status = "Overdue"
    elif sm == now:
        status = "Due now"
    else:
        status = "Upcoming"
    check = "OK"
    if first and (sm[0], sm[1]) < (first.year, first.month):
        check = "Month before 1st visit"
    elif first and (sm[0], sm[1]) == (first.year, first.month):
        check = "Same month as 1st visit"
    return dict(month=label, key=sm, status=status, check=check)


for v in visited:
    v["second"] = second_visit(v)

# ---------------------------------------------------------------- free pass feedback
fp_rows = SRC["freepass"]
pending_masters = [m for m in master if m["area"] and m["id"] not in linked_ids]
visited_by_phone = collections.defaultdict(list)
for v in visited:
    if v["phone"]:
        visited_by_phone[v["phone"]].append(v)
fp_of = collections.defaultdict(list)
fp_unmatched = []
for f in fp_rows:
    f["phone_d"] = best_phone(f["phone"])[0]
    f["status"] = {"Nuetral": "Neutral", "Intrested": "Interested"}.get(f["status"], f["status"]) or "Awaiting feedback"
    fname = re.sub(r"^UPST\s+", "", f["school"])          # 'UPST' = UP School Teacher, not part of the name
    hits = loc_hits(fname, loc_keys)
    drop = {phon(w) for h in hits for w in words(h)} | {phon(w) for w in STOP if len(phon(w)) >= 3}
    best, target = 0, None
    for kind, items in (("v", visited), ("m", pending_masters)):
        for t in items:
            if t["locality"] not in hits:
                continue
            d = drop | {phon(w) for w in words(t["locality"])}
            sc = name_score(fname, t["name"], d) or (1 if maybe_same(fname, t["name"], d) else 0)
            if sc > best:
                best, target = sc, (kind, t)
    for t in visited_by_phone.get(f["phone_d"], []):
        if not fname or compatible(fname, t["name"]):
            best, target = 4, ("v", t)   # same number and a compatible name: certain
            break
    f["how"] = "name"
    if not target and f["phone_d"]:
        if visited_by_phone.get(f["phone_d"]):
            target = ("v", visited_by_phone[f["phone_d"]][0])
        else:
            ms = [m for m in by_phone.get(f["phone_d"], []) if m in pending_masters]
            target = ("m", ms[0]) if ms else None
        f["how"] = "phone"
    if target:
        kind, t = target
        other = [v["name"] for v in visited_by_phone.get(f["phone_d"], []) if v is not t]
        f["conflict"] = (f"Free-pass phone {f['phone_d']} is listed for {other[0]} in the tour log"
                         if other and f["how"] == "name" else "")
        fp_of[(kind, id(t) if kind == "v" else t["id"])].append(f)
    elif f["executive"].lower() == "musthafa" or (hits and not f["executive"]):
        fp_unmatched.append(f)


def fp_view(f):
    return dict(status=f["status"], date=f["park_date"].replace("24/072026", "24/07/2026"), persons=f["persons"],
                person=f["person"], phone=f["phone"], fp_school=f["school"] or "(school name blank on sheet)", conflict=f.get("conflict", ""),
                note="; ".join(x for x in (f["park_opinion"], f["stay_opinion"] and "Stay: " + f["stay_opinion"],
                                          f["feedback"], f["tour_period"] and "Tour: " + f["tour_period"])
                               if x and x.lower() not in ("", "no suggestion", "no suggestions", "neutral", "nuetral",
                                                          "interested", "intrested")) or "No suggestions")


# ---------------------------------------------------------------- board label
def board_of(v):
    m = v["link"]
    if m and m["board"] in ("CBSE", "ICSE"):
        return m["board"]
    if v["mtype"] in ("CBSE", "ICSE"):
        return v["mtype"]
    if m:
        return {"Govt": "Govt (State)", "Aided": "Aided (State)", "Unaided": "Unaided (State)"}[m["mgmt"]]
    return {"Govt": "Govt (State)", "Aided": "Aided (State)", "Unaided": "Private / Unaided",
            "Special": "Special school"}.get(v["mtype"], "Not recorded")


def board_m(m):
    if m["board"] in ("CBSE", "ICSE"):
        return m["board"]
    return {"Govt": "Govt (State)", "Aided": "Aided (State)", "Unaided": "Unaided (State)"}[m["mgmt"]]


def in_deepika_v(v):
    return bool((v["link"] and v["link"]["deepika"]) or v["m_deepika"])


# ---------------------------------------------------------------- assemble per area
areas = collections.OrderedDict((a, dict(area=a, localities=set(), second=[], pending=[], visited=0,
                                          visited_in_data=0, data_total=0, no_date=0, fp=[],
                                          bad_phone_v=0, bad_phone_p=0))
                                for a in AREA_ORDER)
for v in visited:
    A = areas[v["area"]]
    A["localities"].add(v["locality"])
    A["visited"] += 1
    if v["link"]:
        A["visited_in_data"] += 1
    ok = phone_ok(v["phone"])
    v["phone_ok"] = ok
    if not ok:
        A["bad_phone_v"] += 1
    row = dict(name=v["name"], locality=v["locality"], board=board_of(v), contact=v["contact"],
               data_name=v["link"]["name"] if v["link"] else "",
               phone=fmt_phone(v["phone"]), phone_ok=ok, first=v["first"], deepika=in_deepika_v(v),
               fp=[fp_view(f) for f in fp_of.get(("v", id(v)), [])])
    v["_row"] = row
    if v["second"]:
        row.update(v["second"])
        A["second"].append(row)
    else:
        A["no_date"] += 1
    for f in row["fp"]:
        A["fp"].append(dict(name=v["name"], locality=v["locality"], visited=True,
                            second=row.get("month", ""), **f))

pend_ids = set()
for m in master:
    if not m["area"]:
        continue
    A = areas[m["area"]]
    A["data_total"] += 1
    if m["id"] in linked_ids:
        continue
    pend_ids.add(m["id"])
    addr = m["address"] or ", ".join(x for x in (
        m["locality"],
        f"{m['block']} block" if m["block"] else "",
        f"{m['assembly']} constituency" if m["assembly"] else "",
        "Malappuram") if x)
    fps = fp_of.get(("m", m["id"]), [])
    lk = {phon(w) for w in words(m["locality"])}
    check = [v["name"] for v in visited if v["locality"] == m["locality"] and not v["link"]
             and maybe_same(v["name"], m["name"], lk)]
    if not m["phone_ok"]:
        A["bad_phone_p"] += 1
    row = dict(name=m["name"], locality=m["locality"], board=board_m(m), level=m["level"], address=addr,
               phone=fmt_phone(m["phone"]) if m["phone"] else "—", phone_ok=m["phone_ok"],
               raw_phone=m["raw_phone"], deepika=bool(m["deepika"]), src=m["src"], check=check, _digits=m["phone"],
               fp=[fp_view(f) for f in fps])
    A["pending"].append(row)
    for f in row["fp"]:
        A["fp"].append(dict(name=m["name"], locality=m["locality"], visited=False, second="", **f))

# ---------------------------------------------------------------- contact-number accuracy
def phone_issue(p):
    if not p:
        return "Missing"
    if len(p) in (6, 7, 8):
        return "Incomplete (no STD code)"
    if not phone_ok(p):
        return "Invalid format"
    return ""


all_rows = []   # (area, name, phone digits, row or None)
for v in visited:
    all_rows.append((v["area"], v["name"], v["phone"], v.get("_row")))
for A in areas.values():
    for p in A["pending"]:
        all_rows.append((A["area"], p["name"], p["_digits"], p))
num_users = collections.defaultdict(set)
for a, n, p, _ in all_rows:
    if p and phone_ok(p):
        num_users[p].add(n)
issues = collections.Counter()
area_issue = collections.defaultdict(collections.Counter)
for a, n, p, row in all_rows:
    iss = phone_issue(p)
    shared = sorted(num_users.get(p, set()) - {n}) if p else []
    if iss:
        issues[iss] += 1
        area_issue[a]["bad"] += 1
    elif shared:
        issues["Shared with another school"] += 1
        area_issue[a]["shared"] += 1
    if row is not None:
        row["phone_note"] = iss or (f"Same no. as {shared[0]}" if shared else "")
for v in visited:
    v["phone_note"] = v["_row"].get("phone_note", "")
for A in areas.values():
    A["bad_phone"] = area_issue[A["area"]]["bad"]
    A["shared_phone"] = area_issue[A["area"]]["shared"]

for A in areas.values():
    A["localities"] = sorted(A["localities"])
    A["second"].sort(key=lambda r: (r["key"], r["locality"], r["name"]))
    A["pending"].sort(key=lambda r: (r["locality"], r["board"], r["name"]))
    A["visited_not_in_data"] = A["visited"] - A["visited_in_data"]
    A["data_visited"] = A["data_total"] - len(A["pending"])

json.dump(dict(areas=list(areas.values()), fp_unmatched=fp_unmatched, phone_issues=issues,
               stats=dict(master=len(master), state=len(SRC["state"]), deepika=len(SRC["deepika"]),
                          cbse=len(SRC["cbse"]), icse=len(SRC["icse"]), visited=len(visited),
                          linked=sum(1 for v in visited if v["link"]),
                          how=collections.Counter(v["how"] for v in visited),
                          freepass=len(fp_rows))),
          open(OUT, "w"), indent=1, ensure_ascii=False, default=str)

# debug dump
json.dump([dict({k: x for k, x in v.items() if k != "_row"}, link=v["link"]["name"] if v["link"] else None) for v in visited],
          open(OUT.replace(".json", "_visited_debug.json"), "w"), indent=1, ensure_ascii=False, default=str)
print(json.dumps(json.load(open(OUT))["stats"], indent=0))
for A in areas.values():
    print(f"{A['area']:16} loc={len(A['localities']):3} data={A['data_total']:4} vis={A['visited']:3} "
          f"linked={A['visited_in_data']:3} 2nd={len(A['second']):3} pend={len(A['pending']):3} fp={len(A['fp'])} "
          f"badV={A['bad_phone_v']} badP={A['bad_phone_p']}")
