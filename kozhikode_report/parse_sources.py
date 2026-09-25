"""Parse the five source PDFs into clean JSON (sources.json).

Usage: python3 parse_sources.py <dir-with-pdfs> <out.json>
"""
import json, re, sys, glob, os
import pymupdf

SRC = sys.argv[1]
OUT = sys.argv[2]


def tables(pattern):
    f = glob.glob(os.path.join(SRC, pattern))[0]
    rows = []
    for p in pymupdf.open(f):
        for t in p.find_tables().tables:
            rows += [[(c or "").replace("\n", " ").strip() for c in r] for r in t.extract()]
    return rows


def clean_phone(s):
    return re.sub(r"\s+", " ", s.replace(",", "")).strip()


# ---------------------------------------------------------------- Arshad
# Cells that the PDF table extractor split in the wrong place (verified by hand
# against the text layer). key = (school name as extracted, place as extracted)
ARSHAD_FIX = {
    ("G U P School a", "duvattom Beyp"): ("G U P School", "Naduvattom Beypore"),
    ("Tip Top Public School a", "duvattom Beyp"): ("Tip Top Public School", "Naduvattom Beypore"),
    ("A M U P School K", "ambilipparamb"): ("A M U P School", "Kambilipparamba"),
    ("G L P School", "ummal, Thiruva"): ("G L P School", "Kottummal, Thiruvannur"),
    ("Thumbayil A.M.L.P.School", "olathara Chunga"): ("Thumbayil A.M.L.P.School", "Kolathara Chungam"),
    ("Govt.U.P.School W", "est Hill Chunga"): ("Govt.U.P.School", "West Hill Chungam"),
    ("Kunnamkulangara A.U.P.School", "Manakkadavu s"): ("Kunnamkulangara A.U.P.School", "Manakkadavu"),
    ("Govt.H.S.East Hill", ""): ("Govt.H.S.", "East Hill"),
}
CONTACT_FIX = {"a Junaid (Tour Co-Ordinator)": "Junaid (Tour Co-Ordinator)",
               "o Geetha (Tour Co-Ordinator)": "Geetha (Tour Co-Ordinator)",
               "o Najeeb": "Najeeb",
               "n Shanoj (Tour Co-Ordinator)": "Shanoj (Tour Co-Ordinator)",
               "m Shameer(HM)": "Shameer(HM)", "m Nisha(HM)": "Nisha(HM)",
               "uddin(Tour Co-ordinator), Anooja(Tour Co-ordi":
               "..uddin (Tour Co-ordinator), Anooja (Tour Co-ordinator)"}

arshad = []  # one entry per contact row
date = ""
for r in tables("*arshad_visited_school.pdf")[1:]:
    r = (r + [""] * 14)[:14]
    d, typ, name, place, person, phone, strength, exe, fu, rem, direct, sv, sr, _ = r
    if d and re.match(r"\d\d\.\d\d\.20?\d+", d):
        date = d.replace(".206", ".2026")
    if not any([typ, name, place, person, phone]):
        continue
    if typ in ("Public Holiday", "Sunday", "Onam leave"):
        continue
    name, place = ARSHAD_FIX.get((name, place), (name, place))
    person = CONTACT_FIX.get(person, person)
    row = dict(date=date, type=typ, name=name, place=place, person=person,
               phone=clean_phone(phone), strength=strength, executive=exe or "Arshad",
               note=fu, remarks=rem, direct_call=direct, second_visit=sv, second_remarks=sr)
    if not name and arshad:
        # extra contact of the previous school (the sheet leaves name/place blank)
        prev = arshad[-1]
        row.update(type=typ or prev["type"], name=prev["name"], place=prev["place"],
                   strength=strength or prev["strength"])
    arshad.append(row)

# ---------------------------------------------------------------- Kozhikode master
master = []
for r in tables("*Kozhikode_School_Data.pdf"):
    if len(r) < 5 or r[0] in ("KOZHIKODE SCHOOL DATA", "School Name") or not r[0]:
        continue
    name, asm, fin, level, phone = r[:5]
    if asm == "uKunnamangalam":
        name, asm = "S" + name + "u", "Kunnamangalam"
    if asm == "h Quilandy":
        name, asm = "U" + name + "h", "Quilandy"
    master.append(dict(name=name, assembly=asm, finance=fin, level=level, phone=phone))

# ---------------------------------------------------------------- Deepika
deepika = []
for r in tables("*deepika_kozhikode_data.pdf"):
    no, name, block, fin, phone = (r + [""] * 5)[:5]
    if name in ("School Name",) or no.startswith("Revenue"):
        continue
    if not no.isdigit():
        if name and deepika:  # wrapped school name
            deepika[-1]["name"] += " " + name
        continue
    deepika.append(dict(sno=int(no), name=name, block=block, finance=fin, phone=phone))

# ---------------------------------------------------------------- ICSE / CBSE (Kozhikode only)
icse, cbse = [], []
rows = tables("*icse_and_cbse_schools_list.pdf")
sec = None
for i, r in enumerate(rows):
    head = r[0]
    if "ICSE Co-ed" in head:
        sec = "icse-kkd" if head.startswith("Kozhikode") else "icse-other"
        continue
    if sec == "icse-kkd" and re.match(r"KE\d+", head):
        icse.append(dict(code=head, name=r[1], location=r[2], pin=r[3], phone=r[4]))
    if head == "S.No":
        continue
    if head == "1" and "haramain" in r[1].lower():
        sec = "cbse-kkd"
    elif head == "1":
        sec = "cbse-other"
    if sec == "cbse-kkd" and head.isdigit():
        cbse.append(dict(sno=int(head), name=r[1], address=r[2], phone=r[3],
                         email=r[4] if len(r) > 4 else ""))

# ---------------------------------------------------------------- Free pass feedback
fb = []
for r in tables("*Free_pass_feedback.pdf"):
    if not r[0] or r[0].startswith(("Date of", "dd/mm")):
        continue
    keys = ["date", "person", "phone", "school", "park_visit", "persons", "executive",
            "park_opinion", "glamping", "stay_opinion", "feedback", "reason_not",
            "tour_period", "final_status"]
    fb.append(dict(zip(keys, (r + [""] * 14)[:14])))

json.dump(dict(arshad=arshad, master=master, deepika=deepika, icse=icse, cbse=cbse,
               feedback=fb), open(OUT, "w"), indent=1)
print({k: len(v) for k, v in dict(arshad=arshad, master=master, deepika=deepika,
                                    icse=icse, cbse=cbse, feedback=fb).items()})
