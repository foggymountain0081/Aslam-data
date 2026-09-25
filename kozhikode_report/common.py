"""Shared helpers: name normalisation and phone classification."""
import re

_WORDS = [
    (r"\bgovernment\b|\bgovt\b", "g"), (r"\bschool\b|\bschoo\b", "s"),
    (r"\benglish medium\b|\benglish\b", "em"), (r"\bmedium\b", ""),
    (r"\bhigher secondary\b", "hss"), (r"\bhigh\b", "h"), (r"\bsecondary\b", "s"),
    (r"\bvocational\b", "v"), (r"\bpublic\b", "p"), (r"\bsection\b", ""),
    (r"\bthe\b", ""), (r"\band\b", ""), (r"\bfor\b", ""), (r"\bpo\b", ""),
    (r"\bst\b", "st"), (r"\bsaint\b", "st"),
]


def norm(s):
    s = s.lower().replace("`", "'").replace("'s", "s").replace("’s", "s")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    for a, b in _WORDS:
        s = re.sub(a, b, s)
    toks = s.split()
    out, buf = [], ""
    for t in toks:           # "g l p s" -> "glps"
        if len(t) == 1:
            buf += t
        else:
            if buf:
                out.append(buf); buf = ""
            out.append(t)
    if buf:
        out.append(buf)
    # "glp s" style leftovers
    return " ".join(out)


def phones(s):
    """Split a free-text phone cell into individual numbers (digits only)."""
    s = s.replace("-", " / ").replace(",", " / ")
    parts = [re.sub(r"\D", "", p) for p in re.split(r"/|;|\s{2,}| ", s)]
    return [p for p in parts if len(p) >= 6]


def is_mobile(p):
    p = re.sub(r"\D", "", p)
    if p.startswith("91") and len(p) == 12:
        p = p[2:]
    return len(p) == 10 and p[0] in "6789"


def mobiles(s):
    return [p[-10:] for p in phones(s) if is_mobile(p)]


def fmt_phone(p):
    """Landlines stored without the leading 0 (e.g. 4952414565) -> 0495 2414565."""
    p = re.sub(r"\D", "", p)
    if is_mobile(p):
        return p[-10:]
    if len(p) == 10 and p[:3] in ("495", "496"):
        return "0" + p[:3] + " " + p[3:]
    if len(p) == 12 and p.startswith("91495"):
        return "0495 " + p[5:]
    if len(p) == 7:
        return "0495 " + p
    return p
