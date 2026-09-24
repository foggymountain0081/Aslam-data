"""Cross-match Aslam's areas with Deepika's directory and the free-pass log."""
import json, re, sys
from collections import Counter


def digits(p):
    return re.sub(r"\D", "", p or "")


def phones(p):
    """All phone numbers in a cell, normalised to their last 10 (or fewer) digits."""
    out = set()
    for part in re.split(r"[,/]", p or ""):
        d = digits(part)
        if len(d) >= 7:
            out.add(d[-10:])
    return out


def norm(s):
    s = s.lower().replace("school", "s")
    return re.sub(r"[^a-z0-9]", "", s)


ALIASES = {"pulloor": "pullur", "cihilavil": "chilavil", "valiyaparambu": "valiyaparambu"}


def load(path):
    d = json.load(open(path))
    deep_phone, deep_name = {}, {}
    for r in d["deepika"]:
        for p in phones(r["phone"]):
            deep_phone.setdefault(p, r)
        deep_name.setdefault(norm(r["name"]), r)
    return d, deep_phone, deep_name


def deepika_match(name, phone, area, deep_phone, deep_name):
    for p in phones(phone):
        if p in deep_phone:
            return deep_phone[p]
    n = norm(name)
    if n in deep_name:
        return deep_name[n]
    if norm(area) not in n and norm(area) + n not in deep_name:
        cand = n + norm(area)
        if cand in deep_name:
            return deep_name[cand]
    return None


def fp_text(r):
    t = r.get("school", "").lower()
    for a, b in ALIASES.items():
        t = t.replace(a, b)
    return t
