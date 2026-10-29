"""Palakkad district map of school-visit areas covered by executives Arun and Athul.

Data: Arun_Work_Report.pdf and Athul_Work_Report.pdf (visit data as of 26 Oct 2026).
Boundaries: district polygons from OpenStreetMap (via the vardhan-maps npm package),
saved in maps/geo/. Area zones are approximate: each point in the district is assigned
to the nearest education sub-district HQ town (not official boundaries).

Run:  python3 maps/palakkad_visit_map.py   ->  Palakkad_Executive_Visit_Map.pdf
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from shapely.geometry import shape, Point, MultiPoint
from shapely.ops import voronoi_diagram

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "Palakkad_Executive_Visit_Map.pdf")

ARUN_C, ATHUL_C, BOTH_C, NONE_C = "#2a78d6", "#eb6834", "#1baf7a", "#e6e5e0"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"

# Education sub-district HQ towns (lon, lat)
HQ = {
    "Mannarkkad": (76.461, 10.992), "Ottapalam": (76.377, 10.772),
    "Cherpulassery": (76.311, 10.877), "Shoranur": (76.272, 10.762),
    "Pattambi": (76.195, 10.806), "Parli": (76.565, 10.800),
    "Thrithala": (76.115, 10.808), "Chittur": (76.745, 10.698),
    "Palakkad": (76.651, 10.775), "Alathur": (76.540, 10.645),
    "Kollengode": (76.692, 10.614), "Kuzhalmannam": (76.587, 10.712),
    "Agali": (76.648, 11.095),
}

# Arun: area -> (master-list schools, schools visited, coverage %, 2nd visits done, high leads)
ARUN = {
    "Mannarkkad": (162, 86, 39, 7, 4), "Ottapalam": (125, 83, 58, 4, 1),
    "Cherpulassery": (104, 73, 64, 9, 5), "Shoranur": (107, 74, 63, 4, 2),
    "Pattambi": (95, 64, 66, 0, 2), "Parli": (77, 37, 44, 6, 1),
    "Thrithala": (86, 18, 17, 0, 0), "Chittur": (225, 7, 3, 0, 0),
    "Palakkad": (107, 3, 3, 0, 0),
}
# Athul: area -> (master-list schools, visited in list, coverage %, extra not in list, 2nd done, high leads)
ATHUL = {
    "Alathur": (118, 76, 64, 27, 8, 30), "Kollengode": (102, 61, 60, 23, 15, 19),
    "Kuzhalmannam": (72, 35, 49, 14, 4, 13), "Palakkad": (107, 36, 34, 26, 3, 15),
    "Chittur": (122, 29, 24, 15, 3, 9), "Parli": (71, 6, 8, 3, 0, 4),
    "Mannarkkad": (124, 2, 2, 8, 0, 2), "Shoranur": (89, 3, 3, 0, 0, 1),
}
THRISSUR = {"Arun": 22, "Athul": 100}

# Confirmed bookings (approximate school locations, lon, lat)
BOOKINGS = [
    ("Holy Family School, Ponnamkode", 76.505, 10.955, "Arun", "13/10, 58+10"),
    ("Mujahideen HSS, Parali", 76.535, 10.815, "Both", "17/10, 45+8"),
    ("AMSB School, Kinassery", 76.660, 10.738, "Athul", "10/10, 60+15"),
    ("St Pius X Sunday School, Olippara", 76.620, 10.560, "Athul", "20/10, 42+7"),
]


def athul_visited(a):
    v = ATHUL.get(a)
    return v[1] + v[3] if v else 0


def arun_visited(a):
    return ARUN[a][1] if a in ARUN else 0


def load_geo():
    k = json.load(open(os.path.join(HERE, "geo", "kerala.json")))
    tn = json.load(open(os.path.join(HERE, "geo", "tamil_nadu.json")))
    feats = {f["properties"]["name"]: shape(f["geometry"]) for f in k["features"]}
    feats.update({f["properties"]["name"]: shape(f["geometry"]) for f in tn["features"]
                  if f["properties"]["name"] in ("Coimbatore", "Nilgiris", "Tiruppur")})
    return feats


def zones(district):
    names = list(HQ)
    pts = MultiPoint([Point(HQ[n]) for n in names])
    cells = voronoi_diagram(pts, envelope=district.envelope.buffer(0.5))
    out = {}
    for cell in cells.geoms:
        for n in names:
            if cell.contains(Point(HQ[n])):
                out[n] = cell.intersection(district)
    return out


def draw_geom(ax, g, **kw):
    polys = g.geoms if hasattr(g, "geoms") else [g]
    for p in polys:
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        x, y = p.exterior.xy
        ax.fill(x, y, **kw)


def base_axes(fig, feats, rect=(0.03, 0.06, 0.62, 0.84)):
    ax = fig.add_axes(rect)
    for name, g in feats.items():
        if name == "Palakkad":
            continue
        draw_geom(ax, g, facecolor="#f4f3ef", edgecolor="#c9c8c2", linewidth=0.6)
    for name, (x, y) in {"THRISSUR": (76.22, 10.45), "MALAPPURAM": (76.18, 11.05),
                         "COIMBATORE\n(Tamil Nadu)": (76.93, 10.92),
                         "NILGIRIS": (76.62, 11.30)}.items():
        ax.text(x, y, name, color=MUTED, fontsize=7.5, ha="center", style="italic")
    ax.set_xlim(75.98, 77.05)
    ax.set_ylim(10.22, 11.36)
    ax.set_aspect(1 / 0.983)  # cos(10.8 deg)
    ax.axis("off")
    return ax


def draw_zones(ax, zs, colors, district):
    for n, g in zs.items():
        draw_geom(ax, g, facecolor=colors[n], edgecolor="white", linewidth=1.2)
    draw_geom(ax, district, facecolor="none", edgecolor="#3a3935", linewidth=1.4)


# Labels drawn entirely above or below the HQ dot where neighbours are close
LABEL_POS = {"Pattambi": "above", "Shoranur": "below", "Alathur": "below",
             "Thrithala": "above", "Ottapalam": "below"}


def label(ax, n, lines, dark=False):
    x, y = HQ[n]
    ax.plot(x, y, "o", ms=4, mfc=INK, mec="white", mew=0.8, zorder=5)
    c = "white" if dark else INK
    pos = LABEL_POS.get(n)
    if pos == "above":
        ny, ly, nva, lva = y + 0.034, y + 0.010, "bottom", "bottom"
    elif pos == "below":
        ny, ly, nva, lva = y - 0.010, y - 0.034, "top", "top"
    else:
        ny, ly, nva, lva = y + 0.012, y - 0.013, "bottom", "top"
    ax.text(x, ny, n, ha="center", va=nva, fontsize=8.2, weight="bold", color=c, zorder=6)
    if lines:
        ax.text(x, ly, lines, ha="center", va=lva, fontsize=7, color=c, zorder=6)


def thrissur_callout(ax, text):
    ax.annotate(text, xy=(76.25, 10.62), xytext=(76.00, 10.32), fontsize=7.5, color=INK,
                ha="left", arrowprops=dict(arrowstyle="-|>", color=INK2, lw=0.8),
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#c9c8c2"))


def bookings(ax, who=None):
    for name, x, y, w, _ in BOOKINGS:
        if who and w not in (who, "Both"):
            continue
        ax.plot(x, y, marker="*", ms=13, mfc="#eda100", mec=INK, mew=0.7, zorder=7)


def header(fig, title, sub):
    fig.text(0.03, 0.955, title, fontsize=17, weight="bold", color=INK)
    fig.text(0.03, 0.925, sub, fontsize=9.5, color=INK2)
    fig.text(0.03, 0.025, "Area zones are approximate (nearest sub-district HQ town), not official "
             "boundaries. District boundaries © OpenStreetMap contributors. Booking stars at "
             "approximate school locations.", fontsize=6.8, color=MUTED)


def side_table(fig, rows, cols, title, y0=0.86, x0=0.67, widths=None):
    fig.text(x0, y0, title, fontsize=10.5, weight="bold", color=INK)
    widths = widths or [0.11] + [0.045] * (len(cols) - 1)
    y = y0 - 0.035
    xs = [x0]
    for w in widths[:-1]:
        xs.append(xs[-1] + w)
    for i, c in enumerate(cols):
        fig.text(xs[i] + (0 if i == 0 else widths[i]), y, c, fontsize=7, color=INK2,
                 weight="bold", ha="left" if i == 0 else "right", va="bottom")
    fig.add_artist(Line2D([x0, x0 + sum(widths)], [y - 0.006, y - 0.006],
                          color=INK2, lw=0.6, transform=fig.transFigure))
    for r in rows:
        y -= 0.027
        bold = r[0] in ("TOTAL", "Total")
        for i, v in enumerate(r):
            fig.text(xs[i] + (0 if i == 0 else widths[i]), y, str(v), fontsize=7.6,
                     color=INK, ha="left" if i == 0 else "right", va="bottom",
                     weight="bold" if bold else "normal")
    return y


def page_combined(pdf, feats, district, zs):
    fig = plt.figure(figsize=(16.54, 11.69))
    header(fig, "Palakkad District — Areas Visited by Executives",
           "School visits 22 Jun – 16 Oct 2026 · Arun and Athul · visit data as of 26 Oct 2026")
    ax = base_axes(fig, feats)
    colors = {}
    for n in HQ:
        a, t = arun_visited(n), athul_visited(n)
        if a == 0 and t == 0:
            colors[n] = NONE_C
        elif a >= 5 and t >= 5:
            colors[n] = BOTH_C
        elif a >= t:
            colors[n] = ARUN_C
        else:
            colors[n] = ATHUL_C
    draw_zones(ax, zs, {n: c + "55" if c != NONE_C else c for n, c in colors.items()}, district)
    for n in HQ:
        a, t = arun_visited(n), athul_visited(n)
        parts = []
        if a:
            parts.append(f"Arun {a}")
        if t:
            parts.append(f"Athul {t}")
        label(ax, n, " · ".join(parts) if parts else "not visited")
    bookings(ax)
    thrissur_callout(ax, f"Thrissur border (outside district)\nArun {THRISSUR['Arun']} · "
                     f"Athul {THRISSUR['Athul']} school entries")
    ax.legend(handles=[
        Patch(fc=ARUN_C + "55", ec="white", label="Mainly Arun"),
        Patch(fc=ATHUL_C + "55", ec="white", label="Mainly Athul"),
        Patch(fc=BOTH_C + "55", ec="white", label="Both (5+ schools each)"),
        Patch(fc=NONE_C, ec="white", label="Not visited yet"),
        Line2D([], [], marker="*", ls="", ms=12, mfc="#eda100", mec=INK, label="Confirmed booking"),
    ], loc="upper left", frameon=False, fontsize=8.5, title="Numbers = schools visited",
        title_fontsize=8.5)

    rows = []
    for n in sorted(HQ, key=lambda k: -(arun_visited(k) + athul_visited(k))):
        a, t = arun_visited(n), athul_visited(n)
        rows.append((n, a or "–", t or "–", a + t or "–"))
    rows.append(("Thrissur border", THRISSUR["Arun"], THRISSUR["Athul"],
                 THRISSUR["Arun"] + THRISSUR["Athul"]))
    rows.append(("TOTAL", 445 + 22, 364 + 100, 445 + 22 + 364 + 100))
    y = side_table(fig, rows, ["Area", "Arun", "Athul", "Total"], "Schools visited by area",
                   widths=[0.13, 0.055, 0.055, 0.06])
    notes = [
        "• 12 of 13 Palakkad areas have been visited; Agali (Attappadi) is untouched.",
        "• Arun works the north-west (Mannarkkad, Ottapalam, Cherpulassery,",
        "   Shoranur, Pattambi, Parli); Athul works the south-east (Alathur,",
        "   Kollengode, Kuzhalmannam, Palakkad, Chittur).",
        "• Overlap areas: Mannarkkad, Parli and Chittur (both executives).",
        "• Thin coverage: Thrithala (18), Chittur (51 across both lists of",
        "   122–225 schools).",
        "• Totals may double-count a school visited by both executives.",
    ]
    for i, s in enumerate(notes):
        fig.text(0.67, y - 0.06 - i * 0.022, s, fontsize=8, color=INK)
    fig.text(0.67, y - 0.06 - len(notes) * 0.022 - 0.02, "Confirmed bookings", fontsize=10.5,
             weight="bold", color=INK)
    for i, (name, *_ , who, d) in enumerate(BOOKINGS):
        fig.text(0.67, y - 0.06 - len(notes) * 0.022 - 0.045 - i * 0.022,
                 f"★ {name} — {d} ({'Arun & Athul' if who == 'Both' else who})",
                 fontsize=8, color=INK)
    pdf.savefig(fig)
    plt.close(fig)


def page_exec(pdf, feats, district, zs, who):
    fig = plt.figure(figsize=(16.54, 11.69))
    c = ARUN_C if who == "Arun" else ATHUL_C
    data = ARUN if who == "Arun" else ATHUL
    sub = ("School visits 22 Jun – 16 Oct 2026 · 445 Palakkad schools in 9 areas + 22 Thrissur border"
           if who == "Arun" else
           "School visits 22 Jun – 14 Oct 2026 · 364 Palakkad schools in 8 areas + 100 Thrissur entries")
    header(fig, f"{who} — Areas Visited, Palakkad District", sub)
    ax = base_axes(fig, feats)
    cmap = LinearSegmentedColormap.from_list("s", ["#ffffff", c])
    norm = Normalize(0, 80)
    colors = {n: (cmap(norm(10 + data[n][2] * 0.85)) if n in data else NONE_C) for n in HQ}
    draw_zones(ax, zs, colors, district)
    for n in HQ:
        if n in data:
            v = arun_visited(n) if who == "Arun" else athul_visited(n)
            label(ax, n, f"{v} schools · {data[n][2]}%", dark=data[n][2] >= 55)
        else:
            label(ax, n, "not visited")
    bookings(ax, who)
    thrissur_callout(ax, f"Thrissur border: {THRISSUR[who]} school entries")
    ax.legend(handles=[
        Patch(fc=cmap(norm(10 + 65 * 0.85)), ec="white", label="High coverage (≥55%)"),
        Patch(fc=cmap(norm(10 + 35 * 0.85)), ec="white", label="Medium (30–54%)"),
        Patch(fc=cmap(norm(10 + 5 * 0.85)), ec="white", label="Low (<30%)"),
        Patch(fc=NONE_C, ec="white", label="Not visited"),
        Line2D([], [], marker="*", ls="", ms=12, mfc="#eda100", mec=INK, label="Confirmed booking"),
    ], loc="upper left", frameon=False, fontsize=8.5,
        title="Shade = master-list coverage %", title_fontsize=8.5)

    order = sorted(data, key=lambda k: -data[k][2])
    if who == "Arun":
        rows = [(n, d[0], d[1], f"{d[2]}%", d[3], d[4]) for n, d in ((n, data[n]) for n in order)]
        rows.append(("TOTAL", 1088, 445, "34%", 30, 15))
        y = side_table(fig, rows, ["Area", "Schools", "Visited", "Cover.", "2nd", "High"],
                       "Area-wise summary", widths=[0.10, 0.045, 0.045, 0.045, 0.03, 0.035])
        notes = ["Not yet worked: Agali, Alathur, Kuzhalmannam.",
                 "Priority: expand into Chittur, Palakkad, Thrithala (3–17%).",
                 "Bookings: Holy Family School Ponnamkode (13/10),",
                 "MHSS Parali (17/10) — 103 students, 18 teachers.",
                 "17 second visits pending (7 overdue, 10 due)."]
    else:
        rows = [(n, d[0], d[1] + d[3], f"{d[2]}%", d[4], d[5]) for n, d in ((n, data[n]) for n in order)]
        rows.append(("TOTAL", 805, 364, "31%", 33, 93))
        y = side_table(fig, rows, ["Area", "Schools", "Visited", "Cover.", "2nd", "High"],
                       "Area-wise summary", widths=[0.10, 0.045, 0.045, 0.045, 0.03, 0.035])
        notes = ["Visited = in master list + extra schools not in list.",
                 "Not yet worked: Agali, Ottapalam, Cherpulassery, Pattambi, Thrithala.",
                 "Open ground: Mannarkkad (122), Chittur (93), Shoranur (86),",
                 "Palakkad (71), Parli (65) master-list schools unvisited.",
                 "Bookings: AMSB Kinassery (10/10), MHSS Parali (17/10),",
                 "St Pius X Olippara (20/10, to verify)."]
    fig.text(0.67, y - 0.025, "Schools = master list · Cover. = master-list coverage · "
             "2nd = second visits done · High = high-probability leads", fontsize=6.6, color=MUTED)
    for i, s in enumerate(notes):
        fig.text(0.67, y - 0.07 - i * 0.022, "• " + s, fontsize=8, color=INK)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    feats = load_geo()
    district = feats["Palakkad"]
    zs = zones(district)
    plt.rcParams["font.family"] = "DejaVu Sans"
    with PdfPages(OUT) as pdf:
        page_combined(pdf, feats, district, zs)
        page_exec(pdf, feats, district, zs, "Arun")
        page_exec(pdf, feats, district, zs, "Athul")
        d = pdf.infodict()
        d["Title"] = "Palakkad District — Areas Visited by Executives"
    print("wrote", OUT)


if __name__ == "__main__":
    main()
