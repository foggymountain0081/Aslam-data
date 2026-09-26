"""Compare the executive visit log (data.py) with the Sametham register."""
import json
import re
from pathlib import Path

from data import AREAS, PENDING, SECOND

SAMETHAM = [
    dict(no=int(r[0]), code=r[1], name=r[2], block=r[3], local_body=r[4],
         type=r[6], level=r[7], phone=r[8])
    for r in json.loads((Path(__file__).parent / "sametham_raw.json").read_text())
]

# Place-name spellings used in Sametham -> executive area name.
AREA_KEYWORDS = {
    "Kumbla": "Kumbala", "Kodiyamme": "Kodiyamma", "Bovikan": "Bovikkanam",
    "Mogralputhur": "Mogral Puthur", "Perdala Neerchal": "Neerchal",
}
AREA_KEYWORDS.update({a: a for a in AREAS})
# "Kasaragod" in a name usually means the district, so the town is matched
# through the municipality (local body) instead.
del AREA_KEYWORDS["Kasaragod"]


def area_of(s):
    name = s["name"].lower()
    # Longest keyword first so "Mogralputhur" wins over "Mogral".
    for kw in sorted(AREA_KEYWORDS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(kw.lower()), name):
            return AREA_KEYWORDS[kw]
    if s["local_body"] == "Kasaragod(M)":
        return "Kasaragod"
    return None


# Visited school (area, school name as in visit log) -> Sametham code.
VISITED_TO_SAMETHAM = {
    ("Alampady", "GHSS High School"): "HS:11022",
    ("Angadimoger", "GHSS Angadimoger High School"): "HS:11033",
    ("Bovikkanam", "Bar HSS Bovikkanam High School"): "HS:11026",
    ("Chandragiri", "GHSS Chandragiri Higher Secondary"): "HS:11050",
    ("Chemnad", "GHSS Chemnad High School"): "HS:11046",
    ("Ichlampady", "Ichlampady Senior Basic School"): "UP:11349",
    ("Iriyanni", "GVHSS Iriyanni Higher Secondary"): "HS:11025",
    ("Kadambar", "Govt High School Kadambar"): "HS:11067",
    ("Kasaragod", "GMRHSS For Girls"): "HS:11056",
    ("Kodiyamma", "GHS Kodiyamma School"): "HS:11070",
    ("Kumbala", "GHSS Kumbala High School"): "HS:11020",
    ("Kumbala", "GHSS Kumbala Higher Secondary School"): "HS:11020",
    ("Mogral", "GVHSS Mogral High School"): "HS:11029",
    ("Munnad", "GHS Munnad"): "HS:11073",
    ("Neerchal", "MSC High School Neerchal"): "HS:11039",
    ("Neerchal", "MSC Higher Secondary School Neerchal"): "HS:11039",
    ("Nellikunnu", "GVHSS Girls School (Higher Secondary)"): "HS:11006",
    ("Paivalike", "GHSS School"): "HS:11018",
    ("Puthige", "Junior Basic School"): "LP:11320",
}
# Pending entries in the visit-log report that are really visited schools.
PENDING_ALREADY_VISITED = {
    "A. S. B. S. Ichlampady": "same phone as visited Ichlampady Senior Basic School",
    "A. J. B. S. Puthige": "same as visited Junior Basic School, Puthige",
    "G. H. S. S. Paivalike Nagar": "same as visited GHSS School, Paivalike",
    "M P International School": "same as visited MP International School, Shiribagilu",
}


def is_mobile(num):
    return bool(re.fullmatch(r"[6-9]\d{9}", num))


def build():
    by_code = {s["code"]: s for s in SAMETHAM}
    visited_codes = set(VISITED_TO_SAMETHAM.values())

    covered = [dict(area=a, name=n, type=t, phone=p, exec=x, month=m,
                    sametham=VISITED_TO_SAMETHAM.get((a, n), ""))
               for a, n, t, p, x, m in SECOND]

    # Not covered: Sametham schools in executive areas that were not visited...
    pending, seen = [], set()
    for s in SAMETHAM:
        area = area_of(s)
        if area and s["code"] not in visited_codes:
            pending.append(dict(area=area, name=s["name"], type=s["type"], phone=s["phone"],
                                source="Sametham", code=s["code"]))
            seen.add(s["phone"])
    # ...plus CBSE/other pending schools from the visit-log report not in Sametham.
    names_sam = {s["name"] for s in SAMETHAM}
    for area, name, typ, _, phone in PENDING:
        if name in PENDING_ALREADY_VISITED or name in names_sam or phone in seen:
            continue
        pending.append(dict(area=area, name=name, type=typ, phone=phone,
                            source="Visit-log report (CBSE list)", code=""))
        seen.add(phone)

    in_area_sam = [s for s in SAMETHAM if area_of(s) or s["code"] in visited_codes]
    # Spellings differ between the two files, so match on phone number.
    old_pending_phones = {p[4] for p in PENDING}
    new_from_sametham = [p for p in pending if p["source"] == "Sametham"
                         and p["phone"] not in old_pending_phones]
    return dict(
        covered=covered, pending=pending, by_code=by_code,
        sametham_total=len(SAMETHAM), sametham_in_area=len(in_area_sam),
        sametham_outside=len(SAMETHAM) - len(in_area_sam),
        visited_matched=sorted({c["sametham"] for c in covered if c["sametham"]}),
        visited_rows_matched=sum(1 for c in covered if c["sametham"]),
        new_from_sametham=new_from_sametham,
        sametham_pending=sum(p["source"] == "Sametham" for p in pending),
    )


if __name__ == "__main__":
    r = build()
    print("sametham in area", r["sametham_in_area"], "outside", r["sametham_outside"])
    print("visited rows matched", r["visited_rows_matched"], "codes", len(r["visited_matched"]))
    print("pending", len(r["pending"]), "new from sametham", len(r["new_from_sametham"]))
    for p in r["pending"]:
        print(f'{p["area"]:14} {p["source"][:8]:8} {p["type"][:10]:10} {p["phone"]:12} {p["name"]}')
    cov, pen = r["covered"], r["pending"]
    print("total", len(cov) + len(pen), "mobile", sum(is_mobile(x["phone"]) for x in cov + pen))
