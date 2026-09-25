"""Parse the five source PDFs into clean Python records.

Sources (in ../source_data):
  Aslam_visited_school_data.pdf          - Aslam's day-by-day visit log
  Deepikas_Malappuram_data.pdf           - Deepika's Malappuram school list (block-wise)
  State_Syllabus_School_data_Malappuram.pdf - State syllabus census (assembly-wise)
  icse_and_cbse_schools_list.pdf         - ICSE + CBSE directory (all Kerala districts)
  Free_pass_feedback.pdf                 - Free stay-pass feedback register
"""
import os
import re

import pdfplumber

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "source_data")


def _cell(c):
    return re.sub(r"\s+", " ", (c or "").replace("\n", " ")).strip()


def _tables(fname):
    rows = []
    with pdfplumber.open(os.path.join(SRC, fname)) as pdf:
        for pno, page in enumerate(pdf.pages, 1):
            for t in page.extract_tables():
                for r in t:
                    rows.append((pno, [_cell(c) for c in r]))
    return rows


def phones_in(text):
    """Return every 10-digit number (or 0-prefixed 11-digit landline) in text."""
    out = []
    for m in re.findall(r"\d[\d ]{8,12}\d", text or ""):
        d = re.sub(r"\D", "", m)
        if len(d) == 11 and d.startswith("0"):
            d = d[1:]
        if len(d) == 10 and d not in out:
            out.append(d)
    return out


def is_mobile(num):
    return bool(re.fullmatch(r"[6-9]\d{9}", num or ""))


# Overlapping columns in the first page of Aslam's sheet garble some words;
# these are the literal garbles pdfplumber produces, mapped back to the text.
_GARBLE = {
    "After 1 Imntoenrtehstered": "After 1 month - Interested",
    "After 1 mInotnetrhested": "After 1 month - Interested",
    "coordEinxaetciuotrive did not meet": "coordinator. Executive did not meet",
    "Follow-Up N eeded": "Follow-Up Needed",
    "Follow-UpNeeded": "Follow-Up Needed",
}
_NON_VISIT = {"LEAVE", "HOLIDAY", "SUNDAY", "SUNDSY", "SATURDAY", "SCHOOL OFF DAY",
              "SCHOOL LEAVE", "GOVERNEMENT"}
_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


def _fix_date(d):
    d = d.replace("22.072026", "22.07.2026")
    d = re.sub(r"\.206$", ".2026", d)
    d = d.replace("17.08.2028", "17.08.2026")
    return d


def load_aslam():
    rows = _tables("Aslam_visited_school_data.pdf")
    recs, cur_date, first_jun23_seen = [], "", False
    for pno, r in rows:
        if r[1] == "School Type":
            continue
        date = r[0]
        if date:
            if date == "23.06.2026" and not first_jun23_seen:
                first_jun23_seen = True  # the genuine 23 June (a leave day)
            elif date == "23.06.2026":
                date = "23.09.2026"  # typo in log: listed after 22.09.2026
            cur_date = _fix_date(date)
        typ, name, place, person, contact, strength, execu = r[1:8]
        if name.upper() in _NON_VISIT or (not name and not person):
            continue
        remark = "".join(r[8:11]).replace("None", "")
        for k, v in _GARBLE.items():
            remark = remark.replace(k, v)
        remark = re.sub(r"\s+", " ", remark).strip()
        second_remark = r[11]
        month = r[12].strip().capitalize() if r[12] and r[12] != "None" else ""
        if month and not month.startswith("After"):
            month = next((m for m in _MONTHS if m.lower() == month.lower()), month)
        if "After onam" in second_remark:
            month, second_remark = "After Onam vacation (September)", ""
        # "Aliya English School" row has the principal in the Place column.
        if name == "Aliya English School":
            person, place = f"{person} / {place}", ""
        recs.append(dict(
            date=cur_date, type=typ.title() if typ else "", name=name, place=place,
            person=person, contact=contact, phones=phones_in(contact + " " + remark),
            strength=strength, executive="Aslam", remark=remark,
            second_remark=second_remark, second_month=month, page=pno,
        ))
    # Row with only a second contact person belongs to the school above it.
    out = []
    for rec in recs:
        if not rec["name"] and out:
            out[-1]["person"] += f"; {rec['person']} {rec['contact']}"
            out[-1]["phones"] += [p for p in rec["phones"] if p not in out[-1]["phones"]]
            out[-1]["remark"] += f" | {rec['remark']}"
            continue
        out.append(rec)
    return out


def load_deepika():
    recs = []
    for pno, r in _tables("Deepikas_Malappuram_data.pdf"):
        sl, name, blk, fin, phone = r[:5]
        if not sl.isdigit():
            continue
        recs.append(dict(sl=int(sl), name=name, block=blk, finance=fin,
                         phone=phone, phones=phones_in(phone), page=pno))
    return recs


def load_state():
    recs = []
    for pno, r in _tables("State_Syllabus_School_data_Malappuram.pdf"):
        sl, name, asm, fin, level, phone = r[:6]
        if not sl.isdigit():
            continue
        asm = {"ADITirurangadi": "Tirurangadi", "MPerinthalmanna": "Perinthalmanna"}.get(asm, asm)
        recs.append(dict(sl=int(sl), name=name, assembly=asm, finance=fin, level=level,
                         phone=phone, phones=phones_in(phone), page=pno))
    return recs


def load_cbse_icse(district="MALAPPURAM"):
    """ICSE rows (5 cols, district in page heading) + CBSE rows (address holds district)."""
    rows = _tables("icse_and_cbse_schools_list.pdf")
    heading_by_page = {}
    for pno, r in rows:
        if "District" in r[0] and "ICSE" in r[0]:
            heading_by_page[pno] = r[0].split(" District")[0].upper()
    recs = []
    for pno, r in rows:
        if re.fullmatch(r"KE\d+", r[0]) and heading_by_page.get(pno) == district:
            recs.append(dict(board="ICSE", code=r[0], name=r[1], address=f"{r[2]} {r[3]}",
                             phone=r[4], phones=phones_in(r[4]), email=""))
        elif r[0].isdigit() and district in r[2].upper() + r[1].upper():
            # CBSE phone column is "STD, number, mobile" - rebuild numbers.
            parts = [p.strip() for p in r[3].split(",") if p.strip()]
            nums = []
            if len(parts) >= 2 and len(re.sub(r"\D", "", parts[0])) <= 5:
                std = re.sub(r"\D", "", parts[0]).lstrip("0")
                land = re.sub(r"\D", "", parts[1])
                if std and len(std) + len(land) == 10 and not is_mobile(land):
                    nums.append(std + land)
                parts = parts[1:]
            for p in parts:
                d = re.sub(r"\D", "", p)
                if is_mobile(d) and d not in nums:
                    nums.append(d)
            recs.append(dict(board="CBSE", code="", name=r[1], address=r[2],
                             phone=", ".join(nums), phones=nums,
                             email=r[4] if len(r) > 4 else ""))
    return recs


def load_free_pass():
    recs = []
    hdr = ["Date of visit", "Name of Person", "Contact Number", "School/ Institution/ Company",
           "Park visited Date with free Coupon", "No.of Persons Visited", "executive name",
           "Opinion / Suggestions about park", "Whether they used Glamping stay",
           "Opinion/ Suggestions about stay", "Feedback", "Reason if not interested",
           "Approximate tour period", "Final Status"]
    for pno, r in _tables("Free_pass_feedback.pdf"):
        r = r[:14]
        # header cells on each page are merged with the first data row
        r = [c[len(h):].strip() if c.startswith(h) else c for c, h in zip(r, hdr)]
        if not r[2] or r[3] in ("", "School/ Institution/ Company"):
            continue
        recs.append(dict(date=r[0], person=r[1], contact=r[2], phones=phones_in(r[2]),
                         school=r[3], persons=r[5], executive=r[6], park_opinion=r[7],
                         glamping=r[8], stay_opinion=r[9], feedback=r[10],
                         reason=r[11], tour_period=r[12],
                         status=r[13].replace("Nuetral", "Neutral").replace("Intrested", "Interested")))
    return recs


if __name__ == "__main__":
    a = load_aslam(); d = load_deepika(); s = load_state(); c = load_cbse_icse(); f = load_free_pass()
    print(len(a), len(d), len(s), len(c), len(f))
    for x in a[:3] + a[-3:]:
        print(x)
    print(c[:2], f[:2], sep="\n")
