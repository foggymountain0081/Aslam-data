import re, difflib

LOC_FIX = {"Thirunarayanapura m": "Thirunarayanapuram"}
# district / generic words that must never count as a locality hit in an address
STOP = {"malappuram", "kerala", "dist", "district", "distt", "dt", "po", "via", "post", "india"}


def phon(s):
    """Phonetic-ish key for Malayalam place names written in English."""
    s = re.sub(r"[^a-z]", "", s.lower())
    for a, b in (("zh", "l"), ("th", "t"), ("sh", "s"), ("dh", "d"), ("kh", "k"), ("bh", "b"),
                 ("ph", "p"), ("gh", "g"), ("ee", "i"), ("oo", "u"), ("w", "v"), ("ck", "k"),
                 ("code", "kod"), ("mp", "mb"), ("que", "k"), ("q", "k"), ("sc", "s"), ("kode", "kod"), ("c", "k"), ("y", "i")):
        s = s.replace(a, b)
    s = re.sub(r"(.)\1+", r"\1", s)
    s = re.sub(r"[aeiou]$", "", s)  # Kodasseri / Kodasheri, Areacode / Areekode
    return s


def skel(s):
    return re.sub(r"[aeiou]", "", s)


def words(s):
    return [w for w in re.split(r"[^A-Za-z]+", s) if w]


def loc_hits(text, loc_keys):
    """Return locality names found in text. loc_keys: {locality: phon key}."""
    ws = [w for w in words(text) if w.lower() not in STOP]
    grams = set()
    for n in (1, 2, 3):
        for i in range(len(ws) - n + 1):
            grams.add(phon("".join(ws[i:i + n])))
    hits = []
    for loc, k in loc_keys.items():
        if not k:
            continue
        if k in grams:
            hits.append(loc)
        elif len(k) >= 6:
            sk = skel(k)
            for g in grams:
                if g[:2] == k[:2] and abs(len(g) - len(k)) <= 1 and skel(g) == sk and \
                        difflib.SequenceMatcher(None, g, k).ratio() >= 0.88:
                    hits.append(loc)
                    break
    return hits


def digits(s):
    return re.sub(r"\D", "", s or "")


MALAPPURAM_STD = ("483", "494", "4931", "4933", "4935", "4936", "487")


def phones_of(raw):
    """Split a raw phone cell into normalised 10-digit numbers (landlines as STD+number)."""
    raw = raw or ""
    out = []
    parts = [digits(p) for p in re.split(r"[,/;]| {2,}", raw)]
    parts = [p for p in parts if p]
    i = 0
    while i < len(parts):
        p = parts[i].lstrip("0")
        if p.startswith("91") and len(p) == 12:
            p = p[2:]
        # CBSE style "0483, 2970001" -> STD then number
        if len(p) in (3, 4) and i + 1 < len(parts) and len(parts[i + 1]) in (6, 7) and len(p + parts[i + 1]) == 10:
            out.append(p + parts[i + 1]); i += 2; continue
        if p and p != "91":
            out.append(p)
        i += 1
    return out


def phone_ok(p):
    if len(p) != 10:
        return False
    if p[0] in "6789":
        return len(set(p)) > 2
    return p.startswith(MALAPPURAM_STD)


def best_phone(raw):
    ps = phones_of(raw)
    good = [p for p in ps if phone_ok(p)]
    mob = [p for p in good if p[0] in "6789"]
    return (mob + good + ps + [""])[0], bool(good), ps


def fmt_phone(p):
    if not p:
        return "—"
    if p[0] in "6789" and len(p) == 10:
        return p
    for std in ("4931", "4933", "4935", "4936", "483", "494", "487"):
        if p.startswith(std) and len(p) == 10:
            return f"0{std} {p[len(std):]}"
    return p


ABBR = [(r"GOVERNMENT|GOVT", "G"), (r"HIGHERSECONDARY", "HS"), (r"VOCATIONALHIGHERSECONDARY", "VHS"),
        (r"HIGHSCHOOL", "HS"), (r"LOWERPRIMARY", "LP"), (r"UPPERPRIMARY", "UP"), (r"MAPPILA", "M"),
        (r"GIRLS", "G"), (r"BOYS", "B"), (r"SCHOOL|SCOOL|SCHL", "S"), (r"ENGLISHMEDIUM", "EM")]


def code(name, drop=()):
    """Compact type code: 'A.U.P.School Chembrasseri' -> 'AUPS'."""
    ws = [w for w in words(name.upper()) if phon(w) not in drop and w not in ("PANCHAYATH", "PANCHAYAT")]
    s = "".join(ws)
    for a, b in ABBR:
        s = re.sub(a, b, s)
    return s


GENERIC = {"school", "english", "medium", "public", "high", "higher", "secondary", "senior", "central",
           "the", "of", "and", "memorial", "em", "ems", "hss", "hs", "lp", "up", "ups", "lps", "s", "e", "m",
           "residential", "international", "eng", "med", "englsh", "academy", "vidyalaya", "sr", "sec", "kg", "to", "wing",
           "nursery", "pre", "panchayath", "panchayat", "run", "by", "estate", "primary", "upper", "lower", "govt", "aided", "g", "a", "p", "l", "u", "h"}


def key_words(name, drop=()):
    return {phon(w) for w in words(name) if w.lower() not in GENERIC and len(w) > 2 and phon(w) not in drop
            and not (w.isupper() and len(w) <= 6 and len(re.findall(r"[AEIOU]", w)) <= 1)}


WORD_ABBR = {"school": "S", "schools": "S", "shool": "S", "english": "E", "medium": "M", "higher": "H",
             "high": "H", "secondary": "S", "lower": "L", "upper": "U", "primary": "P", "government": "G",
             "govt": "G", "girls": "G", "boys": "B", "mappila": "M", "vocational": "V", "public": "P",
             "memorial": "M", "aided": "A", "sr": "S", "senior": "S"}


def initials(name, drop=()):
    out = ""
    for w in words(name):
        lw = w.lower()
        if phon(w) in drop or lw in ("panchayath", "panchayat"):
            continue
        if lw in WORD_ABBR:
            out += WORD_ABBR[lw]
        elif len(w) <= 6 and w.isupper() and w.upper() == w:   # already an acronym: GHSS, SVLPS
            out += w.upper()
        elif len(w) == 1:
            out += w.upper()
        else:
            out += w[0].upper()
    return out


def strip_s(x):
    x = re.sub(r"HSS$", "HS", x)
    return x[:-1] if x.endswith("S") and len(x) > 3 else x


def level(name):
    c = initials(name)[1:]
    if "PRE" in name.upper() or "NURSERY" in name.upper() or "KG" in words(name.upper()):
        return "KG"
    for lv, pats in (("LP", ("LP",)), ("UP", ("UP",)), ("HS", ("HS", "HIGH", "VHS"))):
        if any(p in c for p in pats):
            return lv
    return None


def name_score(a, b, drop=()):
    """3 = same school code, 2 = same distinctive words, 0 = different. Level (LP/UP/HS) must agree."""
    la, lb = level(a), level(b)
    if la and lb and la != lb:
        return 0
    ca, cb = strip_s(code(a, drop)), strip_s(code(b, drop))
    ia, ib = strip_s(initials(a, drop)), strip_s(initials(b, drop))
    if len(ca) >= 3 and (ca == cb or ca == ib or ia == cb):
        return 3
    ka, kb = key_words(a, drop), key_words(b, drop)
    share = {w for w in ka & kb if len(w) >= 3}
    if share and len(ka & kb) / len(ka | kb) >= 0.5:
        return 2
    return 0


def maybe_same(a, b, drop=()):
    """Weaker test used only to flag 'please check' notes."""
    la, lb = level(a), level(b)
    if la and lb and la != lb:
        return False
    ca, cb = strip_s(code(a, drop)), strip_s(code(b, drop))
    ia, ib = strip_s(initials(a, drop)), strip_s(initials(b, drop))
    for x in (ca, ia):
        for y in (cb, ib):
            if min(len(x), len(y)) >= 2 and (x.endswith(y) or y.endswith(x)) or \
                    min(len(x), len(y)) >= 3 and (x.startswith(y) or y.startswith(x)):
                return True
    return bool({w for w in key_words(a, drop) & key_words(b, drop) if len(w) >= 4})


def compatible(a, b):
    """Same level and same leading initials - used when the phone number already agrees."""
    la, lb = level(a), level(b)
    if la and lb and la != lb:
        return False
    ia, ib = initials(a), initials(b)
    return ia[:2] == ib[:2] or maybe_same(a, b)
