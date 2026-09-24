"""Parse Musthafa's outreach report PDF into visited / pending school records."""
import json, re, sys
import pdfplumber

SRC = sys.argv[1]
OUT = sys.argv[2]

VCOLS = [("no", 0), ("school", 60), ("type", 163), ("contact", 207), ("phone", 284),
         ("first", 343), ("deepika", 398), ("next", 475)]


PCOLS = [("no", 0), ("school", 66), ("locality", 236), ("type", 313), ("phone", 360), ("in", 462)]


def col_of(x, cols):
    name = cols[0][0]
    for n, x0 in cols:
        if x >= x0:
            name = n
    return name


def bands(page):
    ys = sorted({round(l["top"], 1) for l in page.lines if abs(l["top"] - l["bottom"]) < 0.5})
    return ys


visited, pending = [], []
area = None
section = "visited"
cols_pending = None
locality = None
with pdfplumber.open(SRC) as pdf:
    for pno in range(6, 49):
        pg = pdf.pages[pno]
        words = pg.extract_words(extra_attrs=["size", "fontname"])
        big = [w for w in words if w["size"] > 14]
        if big and big[0]["text"] != "":
            t = " ".join(w["text"] for w in big)
            if t.endswith("Area"):
                area = t[:-5].strip()
                section = "visited"
        # section boundary: "New schools to visit" heading
        new_y = None
        for w in words:
            if w["size"] > 11 and w["text"] == "New":
                new_y = w["top"]
        ys = bands(pg)
        for a, b in zip(ys, ys[1:]):
            ws = [w for w in words if a < w["top"] < b and w["size"] < 11 and w["top"] < 800]
            if not ws:
                continue
            in_pending = section == "pending" or (new_y is not None and a > new_y)
            bold_small = [w for w in ws if "Bold" in w["fontname"] and abs(w["size"] - 8.5) < 0.1]
            if bold_small and len(bold_small) == len(ws):
                locality = " ".join(w["text"] for w in sorted(ws, key=lambda w: w["x0"]))
                continue
            texts = " ".join(w["text"] for w in ws)
            if texts.startswith("# School"):
                if in_pending:
                    hdr = sorted(ws, key=lambda w: w["x0"])
                    cols_pending = [("no", 0)] + [(w["text"].lower(), w["x0"] - 2) for w in hdr[1:]
                                                   if w["text"] in ("School", "Locality", "Type", "Phone", "In")]
                continue
            if in_pending:
                cols = PCOLS
            else:
                cols = VCOLS
            rec = {}
            for w in sorted(ws, key=lambda w: (round(w["top"]), w["x0"])):
                c = col_of(w["x0"], cols)
                if c == "deepika" or c == "in":
                    c = "deepika_detail" if w["size"] < 7.5 else "deepika"
                rec.setdefault(c, []).append(w["text"])
            rec = {k: " ".join(v) for k, v in rec.items()}
            rec["area"] = area
            rec["page"] = pno + 1
            if in_pending:
                section = "pending"
                pending.append(rec)
            else:
                rec["locality"] = locality
                visited.append(rec)

json.dump({"visited": visited, "pending": pending}, open(OUT, "w"), indent=1, ensure_ascii=False)
print(len(visited), len(pending))
