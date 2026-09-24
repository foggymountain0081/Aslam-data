"""Extract State-syllabus, Deepika, CBSE/ICSE (Malappuram) and free-pass feedback rows."""
import json, sys, re
import pdfplumber

U, OUT = sys.argv[1], sys.argv[2]
import glob


def f(pattern):
    hits = sorted(glob.glob(f"{U}/*{pattern}*.pdf"))
    if not hits:
        sys.exit(f"missing source PDF matching *{pattern}*")
    return hits[0]


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()


def tables(path, pages=None):
    with pdfplumber.open(path) as p:
        for i, pg in enumerate(p.pages):
            if pages and i not in pages:
                continue
            for t in pg.extract_tables():
                for r in t:
                    yield [clean(c) for c in r]


state = [dict(sl=r[0], name=r[1], assembly=r[2], finance=r[3], level=r[4], phone=r[5])
         for r in tables(f("State_Syllabus"))
         if len(r) >= 6 and r[0].isdigit()]
deepika = [dict(sl=r[0], name=r[1], block=r[2], finance=r[3], phone=r[4])
           for r in tables(f("Deepika"))
           if len(r) >= 5 and r[0].isdigit()]

icf = f("cbse")
cbse = [dict(sl=r[0], name=r[1], address=r[2], phone=r[3], email=r[4], board="CBSE")
        for r in tables(icf, range(19, 25)) if r[0].isdigit()]
icse, cur = [], None
for r in tables(icf, range(0, 19)):
    if "District" in r[0] and "ICSE" in r[0]:
        cur = r[0].split(" District")[0]
    elif cur == "Malappuram" and r[0].startswith("KE"):
        icse.append(dict(sl=r[0], name=r[1], address=f"{r[2]} - {r[3]}", phone=r[4], board="ICSE"))

fp = []
for r in tables(f("Free_pass")):
    if len(r) < 14:
        continue
    # first row carries header labels glued to values
    r = [re.sub(r"^(Date of visit|Name of Person|Contact Number|School/ Institution/ Company|"
                r"Park visited Date with free Coupon|No.of Persons Visited|executive name|"
                r"Opinion / Suggestions about park|Whether they used Glamping stay|"
                r"Opinion/ Suggestions about stay|Feedback|Reason if not interested|"
                r"Approximate tour period|Final Status) ?", "", c) for c in r]
    if r[0] in ("", "dd/mm/yyyy") or not r[1].strip("# "):
        continue            # blank template rows
    if r[3] == "School/ Institution/ Company":
        r[3] = ""           # school name left blank on the sheet - matched by phone instead
    fp.append(dict(date=r[0], person=r[1], phone=r[2], school=r[3], park_date=r[4], persons=r[5],
                   executive=r[6], park_opinion=r[7], glamping=r[8], stay_opinion=r[9],
                   feedback=r[10], reason=r[11], tour_period=r[12], status=r[13]))

json.dump(dict(state=state, deepika=deepika, cbse=cbse, icse=icse, freepass=fp),
          open(OUT, "w"), indent=1, ensure_ascii=False)
print(len(state), len(deepika), len(cbse), len(icse), len(fp))
