"""Parse the three source PDFs (Aslam master report, Deepika's Malappuram sheet,
Free-pass feedback) into JSON for build_report.py."""
import json, re, sys
import pdfplumber

MONTHS = "January February March April May June July August September October November December".split()


def lines_of(path):
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            out.extend((page.extract_text() or "").splitlines())
    return out


def parse_aslam(path):
    raw = [l.strip() for l in lines_of(path)]
    raw = [l for l in raw if l and not l.startswith("Aslam – Areawise School Outreach Master Report")]
    # skip cover page + intro
    start = next(i for i, l in enumerate(raw) if l.startswith("133 localities"))
    raw = raw[start + 1:]
    sections = ("Second Visit Scheduled", "Pending – First Visit")
    headers = ("School Name Board Contact Phone Month", "School Name Board Detail Phone")
    areas, area, mode, last = [], None, None, None
    sv_re = re.compile(r"^(.*) (Govt|CBSE|ICSE) (.*?) (\d{6,}|—) (%s)$" % "|".join(MONTHS))
    pf_re = re.compile(r"^(.*) (Govt|CBSE|ICSE) (Aided|Government|Unaided Recognised|CBSE|ICSE) ?(.*)$")
    for i, l in enumerate(raw):
        if l in headers:
            continue
        if l in sections:
            mode = "sv" if l == sections[0] else "pf"
            continue
        nxt = next((x for x in raw[i + 1:] if x not in headers), "")
        if nxt in sections and not sv_re.match(l) and not pf_re.match(l):
            area = {"area": l, "sv": [], "pf": []}
            areas.append(area)
            last = None
            continue
        m = sv_re.match(l) if mode == "sv" else pf_re.match(l)
        if m:
            if mode == "sv":
                last = dict(name=m[1], board=m[2], contact=m[3], phone=m[4], month=m[5])
            else:
                last = dict(name=m[1], board=m[2], detail=m[3], phone=m[4] or "—")
            area[mode].append(last)
            continue
        # continuation of a wrapped cell
        if last is None:
            print("UNPARSED", l, file=sys.stderr)
        elif re.fullmatch(r"[\d, ]+", l):
            last["phone"] = (last["phone"] + " " + l).strip()
        elif mode == "sv" and len(l) <= 4 or l.endswith(")") and mode == "sv" and "(" not in l:
            last["contact"] += l
        else:
            last["name"] += " " + l
    return areas


def parse_deepika(path):
    rows = []
    fin = r"(Government|Aided|Unaided Recognised|Unaided|Partially Aided)"
    blocks = r"(Areacode|Edappal|Kondotty|Kottakkal|Kuttippuram|Malappuram|Manjeri|Mankada|Melattur|Nilambur|Parappanangadi|Perinthalmanna|Ponnani|Tanur|Tavanur|Tirur|Tirurangadi|Valanchery|Vengara|Wandoor)"
    rx = re.compile(r"^(\d+) (.*?)(?: %s)? %s ?([\d ]*)$" % (blocks, fin))
    for l in lines_of(path):
        m = rx.match(l.strip())
        if m:
            rows.append(dict(no=int(m[1]), name=m[2], block=m[3] or "", finance=m[4], phone=m[5].strip()))
        elif re.match(r"^\d+ ", l.strip()):
            print("DEEPIKA UNPARSED", l, file=sys.stderr)
    return rows


def parse_freepass(path):
    rows = []
    rx = re.compile(r"^(\d\d/\d\d/\d{4}) (.*?) ((?:\d ?){10})\b ?(.*)$")
    for l in lines_of(path):
        l = l.strip()
        if l.startswith("dd/mm") or not re.match(r"^\d\d/\d\d/", l):
            continue
        m = rx.match(l)
        if not m:
            print("FP UNPARSED", l, file=sys.stderr)
            rows.append(dict(raw=l))
            continue
        rest = m[4]
        d2 = re.search(r"(\d\d/\d\d/?\d{2,4}) (\d+)", rest)
        school = rest[: d2.start()].strip() if d2 else rest
        tail = rest[d2.end():] if d2 else ""
        status = ""
        for s, lab in (("Not interested", "Not interested"), ("Intrested", "Interested"), ("Nuetral", "Neutral")):
            if tail.rstrip().endswith(s):
                status = lab
        tour = ", ".join(dict.fromkeys(re.findall(r"(%s)" % "|".join(MONTHS), tail, re.I)))
        feedback = "Interested for group visit" if "Interested for group visit" in tail else (
            "Not interested" if "Not interested" in tail else ("Neutral" if "Neutral" in tail else ""))
        rows.append(dict(date=m[1], person=m[2], phone=m[3].replace(" ", ""), school=school,
                         visit_date=d2[1] if d2 else "", persons=d2[2] if d2 else "",
                         tail=tail.strip(), status=status, feedback=feedback, tour=tour))
    return rows


if __name__ == "__main__":
    aslam, deepika, fp, out = sys.argv[1:5]
    json.dump(dict(aslam=parse_aslam(aslam), deepika=parse_deepika(deepika), freepass=parse_freepass(fp)),
              open(out, "w"), indent=1, ensure_ascii=False)
