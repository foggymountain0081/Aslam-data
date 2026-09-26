"""Summary report for 7 of Jayarajan's main areas (HTML + PDF).

Perambra, Melady, Panthalayani, Koyilandy Municipality, Kunnummal, Thodannur, Tuneri.
"""
from build_report import area_rows, build_html, build_pdf

NAMES = ["Perambra", "Melady", "Panthalayani", "Koyilandy Municipality", "Kunnummal", "Thodannur", "Tuneri"]

rows, tot = area_rows(NAMES)
T = dict(zip(["total", "visited", "fp", "pending", "second", "with_mob", "without_mob",
              "passes", "matched"], tot))
assert T == dict(total=484, visited=96, fp=2, pending=403, second=45, with_mob=304,
                 without_mob=197, passes=3, matched=83), T

KPIS = [
    ("Total schools in these 7 areas", "484", "As per Deepika's school list. 13 more schools were visited that are not in her list."),
    ("Total schools covered", "96", "Visited by Jayarajan / Amal (13.08 - 24.09.2026). Another 2 schools were covered by other executives through the free stay pass."),
    ("Total schools not yet covered", "403", "Pending first visit. 83% of Deepika's list in these areas is still to be covered."),
    ("Total second visits", "45", "Schools with the 2nd visit / tour month fixed. 51 more visited schools have no month fixed yet (call again). 1 school (Meppayur LPS, Melady) was already revisited."),
    ("Schools with contact mobile number", "304", "95 visited + 2 free-pass + 207 pending schools."),
    ("Schools without contact mobile number", "197", "1 visited (St Joseph AUPS Chempanooda) + 196 pending (landline only / no number)."),
    ("Total free passes issued", "3", "Kannatty LPS (Perambra, a Jayarajan school), NIM LPS Perambra and S.N.H.S.S. Thiruvallur (Thodannur)."),
    ("Schools matched with Deepika's data", "83", "Of the 96 visited schools (79 unique Deepika entries, incl. 2 probable matches in Kunnummal). 13 are not in her list."),
]

MONTHS = [("October", 2), ("November", 11), ("December", 14), ("January", 17), ("February", 1)]

if __name__ == "__main__":
    kw = dict(rows=rows, tot=tot, kpis=KPIS, months=MONTHS, name="Jayarajan_7_Areas_Report",
              title="Jayarajan's 7 Areas Report - Summary",
              subtitle="Perambra, Melady, Panthalayani, Koyilandy, Kunnummal, Thodannur, Tuneri")
    build_html(**kw)
    build_pdf(**kw)
    print("done")
