"""School-name normalisation, fuzzy matching and place -> area (block) mapping."""
import re
from collections import Counter, defaultdict

from rapidfuzz import fuzz

# Words that describe the kind of school rather than where it is.
GENERIC = set("""
SCHOOL SCHOOOL SCHOOLM SCHOOLS S HIGHER SECONDARY HIGH UPPER LOWER PRIMARY ENGLISH MEDIUM EM EMS
PUBLIC CENTRAL INTERNATIONAL GLOBAL PRE PLAY PRESCHOOL NURSERY KIDS KG GOVT GOVERNMENT GOVERNEMENT
AIDED UNAIDED ISLAMIC ISLAM MODEL RESIDENTIAL MONTESSORI THE OF AND FOR WITH COLLEGE ARTS SCIENCE
INSTITUTE INSTITUTION ACADEMY VIDYALAYA VIDYALAYAM SENIOR JUNIOR NEW OFFICE DAY CARE HOUSE SPECIAL
GIRLS BOYS WOMENS INTEGRATED INTERNATIOANL CENTARAL MONTISSORY CBSE ICSE ANGANWADI NORTH SOUTH EAST WEST CENTER CENTRE MALAPPURAM
MALAPPURAM DISTT DIST DISTRICT KERALA PO P O POST VIA NAGAR ANGADI BAZAR ROAD HSS HS UP LP VHSS
LPS UPS AMLPS AMUPS GMLPS GMUPS GLPS GUPS ALPS AUPS GHSS GVHSS GHS AMLP AMUP GMLP GMUP GLP GUP ALP AUP
""".split())

TYPE_WORDS = [
    (r"HIGHER SECONDARY SCHOOL", "HSS"), (r"HIGHER SECONDARY", "HSS"), (r"H\.?S\.?S\b", "HSS"),
    (r"VOCATIONAL", "V"), (r"HIGH SCHOOL", "HS"), (r"UPPER PRIMARY", "UP"), (r"LOWER PRIMARY", "LP"),
    (r"ENGLISH MEDIUM", "EM"), (r"GOVERNMENT|GOVERNEMENT|GOVT", "G"), (r"SCHOOOL|SCHOOLM|SCHOOL", "S"),
]


def clean(s):
    s = (s or "").upper().replace("&", " AND ").replace("`", "'")
    s = re.sub(r"[().,/'\-:;]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def phon(tok):
    """Loose phonetic key for Malayalam place-name spellings (Thirur/Tirur, Kodinji/Kodinhi)."""
    t = tok.lower()
    t = t.replace("zh", "l").replace("oo", "u").replace("ee", "i").replace("w", "v")
    t = t.replace("nj", "nh").replace("y", "i")
    t = re.sub(r"(?<=[^aeiou])h", "", t)
    t = re.sub(r"(.)\1+", r"\1", t)
    t = re.sub(r"[aeiou]+$", "", t)  # trailing vowel (Chiramangalam/-u)
    return t


_ABBR = re.compile(r"(G|A|GOVT)?M{0,2}(L|U)PS?|A?(U|L)PS?|[GAO]?V?HSS?|IEC|EMS?|S")


def _is_abbr(t):
    if t in ("AL", "EL", "ST", "DR", "MY", "E"):
        return False
    if len(t) <= 2 or _ABBR.fullmatch(t):
        return True
    vowels = sum(ch in "AEIOU" for ch in t)
    return len(t) <= 8 and vowels / len(t) <= 0.25 and "Y" not in t


def type_code(name):
    """Compact school-type code, e.g. 'A M L P School' -> 'AMLPS', 'G.V.H.S.S.' -> 'GVHSS'."""
    s = clean(name)
    s = re.sub(r"\b([A-Z]{2,8}?)(SCHOO+L\w*)\b", r"\1 \2", s)  # AMLPSchool -> AMLP School
    for pat, rep in TYPE_WORDS:
        s = re.sub(pat, rep, s)
    code = ""
    toks = s.split()
    while toks and toks[0] in ("CENTRAL", "CENTARAL", "NEW", "G", "THE") and len(toks) > 1 and _is_abbr(toks[1]):
        code += "G" if toks[0] == "G" else ""
        toks = toks[1:]
    for t in toks:
        if _is_abbr(t):
            code += t
        else:
            break
    if code[-2:] in ("LP", "UP"):
        code += "S"
    return code


def level(name):
    """Coarse school level used to keep LP / UP / HSS / pre-school on one campus apart."""
    s = " " + clean(name) + " "
    s = re.sub(r"\b([A-Z]{2,8}?)(SCHOO+L\w*)\b", r"\1 \2", s)
    if re.search(r"PRE ?SCHOOL|PRE PRIMARY|PLAY ?SCHOOL|NURSERY|KIDS|KIDDIE|MONTESS?OR|MONTISS|KINDER|DAY CARE| PRE ", s):
        return "PRE"
    if re.search(r"COLLEGE|ITI|INSTITUTE", s):
        return "COLLEGE"
    if "ANGANWADI" in s:
        return "ANGANWADI"
    code = type_code(name)
    if re.search(r"HIGHER SECONDARY|H ?S ?S\b|HSS", s) or code.endswith("HSS"):
        return "HSS"
    if re.search(r"L ?P ?S?\b|LOWER PRIMARY|LPS", s):
        return "LP"
    if re.search(r"U ?P ?S?\b|UPPER PRIMARY|UPS", s):
        return "UP"
    if re.search(r"HIGH SCHOOL|H ?S\b", s):
        return "HS"
    return ""


def levels_ok(a, b):
    la, lb = level(a), level(b)
    return not la or not lb or la == lb or {la, lb} == {"HS", "HSS"}


def place_tokens(text):
    toks = []
    for t in clean(text).split():
        if len(t) < 4 or t in GENERIC or t.isdigit():
            continue
        if re.fullmatch(r"[AGMLPUSHV]{2,6}", t):  # stray type code
            continue
        toks.append(t)
    return toks


def tok_match(a, b):
    pa, pb = phon(a), phon(b)
    if pa == pb:
        return True
    if min(len(pa), len(pb)) >= 5 and abs(len(pa) - len(pb)) <= 3 and (
            pa.startswith(pb) or pb.startswith(pa)):
        return True
    return min(len(pa), len(pb)) >= 5 and fuzz.ratio(pa, pb) >= 85


def share_place(toks_a, toks_b):
    return any(tok_match(a, b) for a in toks_a for b in toks_b)


def name_score(a, b):
    return fuzz.token_sort_ratio(clean(a), clean(b))


class AreaMapper:
    """Learns place-name -> block from the government school list, then maps free-text places."""

    def __init__(self, schools, key="block"):
        votes = defaultdict(Counter)
        for s in schools:
            for t in place_tokens(s["name"]):
                votes[phon(t)][s[key]] += 1
        self.votes = votes
        self.overrides = {}

    def add_overrides(self, mapping):
        for place, block in mapping.items():
            self.overrides[phon(place)] = block

    def lookup(self, *texts):
        for text in texts:  # first text (the Place column) takes priority
            toks = place_tokens(text)
            for t in toks:
                if phon(t) in self.overrides:
                    return self.overrides[phon(t)]
            tally = Counter()
            for t in toks:
                p = phon(t)
                if p in self.votes:
                    tally.update(self.votes[p])
                else:
                    for k, v in self.votes.items():
                        if len(p) >= 6 and len(k) >= 6 and fuzz.ratio(p, k) >= 88:
                            tally.update(v)
            if tally:
                return tally.most_common(1)[0][0]
        return ""
