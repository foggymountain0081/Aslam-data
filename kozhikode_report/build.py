"""Join all sources into one model (model.json) that the PDF/HTML renderers use.

Usage: python3 build.py sources.json model.json
"""
import json, re, sys, collections
from rapidfuzz import fuzz, process
from common import norm, mobiles, phones, fmt_phone
from mapping import (ARSHAD_MATCH, AREAS, PLACE_AREA, ROUTE_KEYWORDS, CBSE_AREA, ICSE_AREA,
                     DEEPIKA_EXTRA_AREA, FEEDBACK_MATCH)

src = json.load(open(sys.argv[1]))
MASTER, DEEPIKA, CBSE, ICSE = src["master"], src["deepika"], src["cbse"], src["icse"]
master_by_name = {m["name"]: m for m in MASTER}
cbse_by_no = {c["sno"]: c for c in CBSE}
icse_by_code = {c["code"]: c for c in ICSE}
deepika_by_no = {x["sno"]: x for x in DEEPIKA}

for k, v in ARSHAD_MATCH.items():
    if v[0] == "M":
        assert v[1] in master_by_name, v

# ------------------------------------------------------------------ master -> Deepika
dn = [norm(x["name"]) for x in DEEPIKA]


def deepika_for_master(m):
    _, sc, i = process.extractOne(norm(m["name"]), dn, scorer=fuzz.ratio)
    if sc >= 90 or (m["phone"] and m["phone"] == DEEPIKA[i]["phone"]):
        return DEEPIKA[i]
    # four schools spelt differently in the two lists (verified by phone / place)
    special = {"A T AHAMMED MEMORIAL ALP SCHOOL POOVATTUPARAMBA": 345}
    return deepika_by_no.get(special.get(m["name"]))


# ------------------------------------------------------------------ universe of schools
schools = {}   # key -> school dict


def new_school(key, **kw):
    s = dict(key=key, area="", locality="", name="", source=[], finance="", level="",
             directory_phones=[], deepika=None, visits=[], feedback=[])
    s.update(kw)
    schools[key] = s
    return s


def cbse_numbers(raw):
    toks = [re.sub(r"\D", "", x) for x in raw.split(",")]
    toks = [x for x in toks if x]
    std = toks[0] if toks and len(toks[0]) <= 4 else ""
    std = ("0" + std.lstrip("0")) if std and std not in ("91", "091", "0") else ""
    out = []
    for x in toks[1:] if std or (toks and len(toks[0]) <= 4) else toks:
        if len(x) >= 10 and x[-10] in "6789":
            out.append(x[-10:])
        elif len(x) in (6, 7) and std:
            out.append(std + " " + x)
        elif len(x) >= 6:
            out.append(fmt_phone(x))
    return out


def in_route(area, name):
    if area not in ROUTE_KEYWORDS:
        return True
    n = name.lower()
    return any(k in n for k in ROUTE_KEYWORDS[area])


outside_route = collections.Counter()
for m in MASTER:
    if m["assembly"] not in AREAS:
        continue
    if not in_route(m["assembly"], m["name"]):
        outside_route[m["assembly"]] += 1
        continue
    s = new_school("M:" + m["name"], area=m["assembly"], name=m["name"], source=["State syllabus list"],
                   finance=m["finance"], level=m["level"],
                   directory_phones=[p for p in [m["phone"]] if p])
    d = deepika_for_master(m)
    if d:
        s["deepika"] = d
for sno, area in DEEPIKA_EXTRA_AREA.items():
    d = deepika_by_no[sno]
    new_school("D:%d" % sno, area=area, name=d["name"], source=["Deepika list"], finance=d["finance"],
               directory_phones=[p for p in [d["phone"]] if p], deepika=d)
for sno, area in CBSE_AREA.items():
    c = cbse_by_no[sno]
    loc = re.sub(r"\s*-\s*\d{6}$", "", c["address"]).strip()
    new_school("CBSE:%d" % sno, area=area, name=c["name"], locality=loc.title()[:60], source=["CBSE list"],
               finance="CBSE", directory_phones=[], fixed_numbers=cbse_numbers(c["phone"]))
for code, area in ICSE_AREA.items():
    c = icse_by_code[code]
    new_school("ICSE:" + code, area=area, name=c["name"], locality=c["location"], source=["ICSE list"],
               finance="ICSE", directory_phones=[], fixed_numbers=[fmt_phone(x) for x in c["phone"].split("/")])

# ------------------------------------------------------------------ Arshad visits
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
MON_TOK = (r"(?:jan(?:uary|u)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
           r"sep(?:t|tember)?|oct(?:o|ober)?|nov(?:e|ember)?|dec(?:e|ember)?)")
MON_RE = re.compile(r"\b" + MON_TOK + r"\b", re.I)


def month_word(s):
    m = MON_RE.search(s or "")
    return MONTHS[[x[:3].lower() for x in MONTHS].index(m.group(0)[:3].lower())] if m else ""


def second_visit_label(sv):
    sv = (sv or "").strip()
    if not sv:
        return ""
    low = sv.lower()
    base = month_word(sv)
    if "/" in sv:
        return " / ".join(x for x in (second_visit_label(p) for p in sv.split("/")) if x)
    if "last" in low:
        return base + " (last week)"
    if "first" in low:
        return base + " (1st week)"
    return base


def tour_window(*texts):
    """Pull the tour period the school mentioned, e.g. 'Nov-Dec'."""
    seq = MON_TOK + r"(?:\s*[-,/ ]\s*" + MON_TOK + r"){0,3}"
    for t in texts:
        if not t:
            continue
        t = re.sub(r"\bOc-", "Oct-", t)
        m = (re.search(r"(?:tour|trip|time)\s*t?[i]?me?\s*[:(]?\s*(" + seq + r")\b", t, re.I)
             or re.search(r"trip\s+(?:almost\s+confirmed\s+)?(" + MON_TOK + r"\s*\d{1,2})\b", t, re.I)
             or re.fullmatch(r"\s*(" + seq + r")\s*", t, re.I)
             or (re.search(r"tour|trip", t, re.I) and re.search(r"\b(" + seq + r")\b", t, re.I)))
        if m:
            if re.search(r"\d", m.group(1)):
                return m.group(1)
            ms = [month_word(x) for x in re.findall(MON_TOK, m.group(1), re.I)]
            return "-".join(x[:3] for x in dict.fromkeys(ms))
    return ""


LEVELS = ["Not interested", "Invalid number", "Awaiting follow-up", "Low", "Medium", "High", "Very high"]


def classify(t):
    t = (t or "").lower()
    if not t.strip():
        return None
    if "not interest" in t or "not intereted" in t or "staff trip is done" in t:
        return "Not interested"
    if any(w in t for w in ["wrong number", "invalid", "its a shop", "cannot receive", "no number"]):
        return "Invalid number"
    if "only interested to free pass" in t:
        return "Low"
    if "almost confirm" in t or "booked" in t or "booed" in t or "trip almost" in t:
        return "Very high"
    has_month = bool(MON_RE.search(t)) and "not confirmed" not in t and "not decided" not in t
    shared = "shared" in t or "whatsapp" in t
    if has_month and shared:
        return "High"
    if has_month or "trip nov" in t:
        return "Medium" if "confirm after" in t or "discuss" in t else "High" if "trip" in t else "Medium"
    if any(w in t for w in ["will confirm", "decide", "decided after", "discussing", "details shared",
                            "shared on", "planning", "confirm after", "wishlist"]):
        return "Medium"
    return "Low"


def school_prob(rows, fb):
    best = None
    for r in rows:
        d, s2 = classify(r["direct_call"]), classify(r["second_remarks"])
        if s2 in ("Not interested",):
            c = s2
        else:
            cands = [x for x in (d, s2) if x and x not in ("Invalid number",)] or [x for x in (d, s2) if x]
            c = max(cands, key=LEVELS.index) if cands else None
        if c and (best is None or LEVELS.index(c) > LEVELS.index(best)):
            best = c
    if any(f.get("final_status", "").lower().startswith("intrest") for f in fb):
        best = "Very high" if best == "Very high" else "High"
    if best is None:
        # visited, but no follow-up call recorded yet (e.g. the 24.09 visits)
        return "Awaiting follow-up"
    return best


# group contact rows into schools
groups = collections.OrderedDict()
for r in src["arshad"]:
    groups.setdefault(r["name"] + " @ " + r["place"], []).append(r)

visited_units = []
for akey, rows in groups.items():
    match = ARSHAD_MATCH.get(akey)
    if match and match[0] == "M":
        skey = "M:" + match[1]
    elif match and match[0] == "CBSE":
        skey = "CBSE:%d" % match[1]
    elif match and match[0] == "ICSE":
        skey = "ICSE:" + match[1]
    elif match and match[0] == "D":
        skey = "D:%d" % match[1]
    elif match and match[0] == "A":
        skey = "A:" + match[1]
    else:
        skey = "A:" + akey
    s = schools.get(skey)
    if s is None and match and match[0] == "M":
        # master school outside the route keyword filter but visited -> include it
        m = master_by_name[match[1]]
        s = new_school(skey, area=m["assembly"], name=m["name"], source=["State syllabus list"],
                       finance=m["finance"], level=m["level"], directory_phones=[p for p in [m["phone"]] if p],
                       deepika=deepika_for_master(m))
        outside_route[m["assembly"]] -= 1
    if s is None:
        nm = rows[0]["name"]
        if rows[0]["place"] and rows[0]["place"].lower()[:5] not in nm.lower():
            nm += ", " + rows[0]["place"]
        if not rows[0]["place"]:
            nm += " (place not recorded)"
        s = new_school(skey, area=PLACE_AREA[rows[0]["place"]], name=nm,
                       source=["Visit log only"], finance=rows[0]["type"])
    if not s["deepika"]:
        # not in a directory list: try Deepika directly (name + place)
        q = norm(rows[0]["name"] + " " + rows[0]["place"])
        _, sc, i = process.extractOne(q, dn, scorer=fuzz.token_sort_ratio)
        if sc >= 92:
            s["deepika"] = DEEPIKA[i]
    unit = dict(label=rows[0]["name"], place=rows[0]["place"], type=rows[0]["type"],
                strength=max((r["strength"] for r in rows), key=lambda x: int(re.sub(r"\D", "", x) or 0)),
                first_date=rows[0]["date"], executive=rows[0]["executive"],
                contacts=[dict(person=r["person"], phone=r["phone"]) for r in rows],
                remarks=" | ".join(dict.fromkeys(x for r in rows for x in [r["remarks"]] if x)),
                direct_call=" | ".join(dict.fromkeys(x for r in rows for x in [r["direct_call"]] if x)),
                second_remarks=" | ".join(dict.fromkeys(x for r in rows for x in [r["second_remarks"]] if x)),
                second_visit=" / ".join(dict.fromkeys(second_visit_label(r["second_visit"]) for r in rows
                                                      if r["second_visit"])),
                rows=rows)
    unit["tour_window"] = tour_window(unit["direct_call"], unit["second_remarks"], unit["remarks"])
    s["visits"].append(unit)
    if not s["locality"]:
        s["locality"] = rows[0]["place"]

# ------------------------------------------------------------------ free-pass feedback
fb_in, fb_out = [], []
for f in src["feedback"]:
    ph = re.sub(r"\D", "", f["phone"])[:10]
    target = FEEDBACK_MATCH.get(ph)
    if target:
        kind, name = target.split(":", 1)
        s = schools["M:" + name] if kind == "M" else next(
            s for s in schools.values() if any(u["label"] + " @ " + u["place"] == name for u in s["visits"]))
        s["feedback"].append(f)
        fb_in.append(dict(f, school_key=s["key"], area=s["area"]))
    else:
        fb_out.append(f)

# ------------------------------------------------------------------ derived fields
for s in schools.values():
    s["visited"] = bool(s["visits"])
    s["visited_by"] = sorted({u["executive"] for u in s["visits"]})
    exec_phones = [p for u in s["visits"] for c in u["contacts"] for p in mobiles(c["phone"])]
    dir_phones = [p for x in s["directory_phones"] for p in phones(x)]
    if s["deepika"] and s["deepika"]["phone"]:
        dir_phones.append(s["deepika"]["phone"])
    s["directory_numbers"] = list(dict.fromkeys([fmt_phone(p) for p in dir_phones] + s.get("fixed_numbers", [])))
    s["all_mobiles"] = list(dict.fromkeys(exec_phones + [p for p in s["directory_numbers"]
                                                         if re.fullmatch(r"[6-9]\d{9}", p)]))
    s["directory_mobiles"] = [p for p in s["directory_numbers"] if re.fullmatch(r"[6-9]\d{9}", p)]
    s["in_deepika"] = bool(s["deepika"])
    s["probability"] = school_prob([r for u in s["visits"] for r in u["rows"]], s["feedback"]) if s["visited"] else ""
    s["second_visit"] = " / ".join(dict.fromkeys(u["second_visit"] for u in s["visits"] if u["second_visit"]))
    s["tour_window"] = " / ".join(dict.fromkeys(u["tour_window"] for u in s["visits"] if u["tour_window"]))
    s["first_date"] = s["visits"][0]["first_date"] if s["visits"] else ""
    for u in s["visits"]:
        u.pop("rows")

model = dict(schools=list(schools.values()), outside_route=dict(outside_route),
             feedback_in_area=fb_in, feedback_other=fb_out,
             visit_rows=len(src["arshad"]), visit_units=sum(len(s["visits"]) for s in schools.values()))
json.dump(model, open(sys.argv[2], "w"), indent=1)

# quick console summary
c = collections.Counter()
for s in schools.values():
    c[(s["area"], "total")] += 1
    c[(s["area"], "visited" if s["visited"] else "pending")] += 1
for a in AREAS:
    print(a, c[(a, "total")], "visited", c[(a, "visited")], "pending", c[(a, "pending")],
          "outside route", outside_route.get(a, 0))
print("feedback in area", len(fb_in), "other", len(fb_out))
print(collections.Counter(s["probability"] for s in schools.values() if s["visited"]))
