import json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon, FancyBboxPatch
from matplotlib.lines import Line2D

GEO = "kerala/geojsons/"  # boundaries from https://github.com/geohacker/kerala
OUT = "Kozhikode_Executive_Visit_Map.pdf"

EXEC = {
    "Arshad":    {"color": "#1f77b4", "period": "13 Aug – 24 Sep 2026"},
    "Basheer":   {"color": "#d62728", "period": "23 Jun – 23 Sep 2026"},
    "Jayarajan": {"color": "#2ca02c", "period": "13 Aug – 24 Sep 2026"},
}

# area: (lat, lon of area, label lon, label lat, {exec: (covered, total)})
AREAS = {
    "Tuneri":            (11.705, 75.665, 75.36, 11.84, {"Jayarajan": (10, 100)}),
    "Thodannur":         (11.605, 75.645, 75.36, 11.71, {"Jayarajan": (5, 86)}),
    "Melady":            (11.520, 75.625, 75.36, 11.59, {"Jayarajan": (11, 47)}),
    "Koyilandy Municipality": (11.440, 75.695, 75.36, 11.47, {"Jayarajan": (3, 47)}),
    "Panthalayani":      (11.405, 75.745, 75.36, 11.36, {"Jayarajan": (4, 48)}),
    "Elathur":           (11.340, 75.790, 75.36, 11.24, {"Arshad": (20, 30), "Basheer": (19, 101)}),
    "Kozhikode North":   (11.280, 75.775, 75.36, 11.105, {"Arshad": (37, 79), "Basheer": (11, 82)}),
    "Kozhikode South":   (11.235, 75.790, 75.36, 10.97, {"Arshad": (101, 119), "Basheer": (3, 75)}),
    "Kunnummal":         (11.650, 75.730, 76.20, 11.84, {"Jayarajan": (25, 75)}),
    "Perambra":          (11.560, 75.765, 76.20, 11.72, {"Jayarajan": (38, 81)}),
    "Balussery":         (11.450, 75.830, 76.20, 11.59, {"Basheer": (18, 119), "Jayarajan": (30, 106)}),
    "Thiruvambadi":      (11.360, 76.000, 76.20, 11.45, {"Basheer": (26, 105)}),
    "Koduvally":         (11.365, 75.910, 76.20, 11.32, {"Basheer": (31, 96), "Jayarajan": (22, 97)}),
    "Kunnamangalam":     (11.305, 75.875, 76.20, 11.16, {"Arshad": (28, 40), "Basheer": (45, 102), "Jayarajan": (4, 113)}),
    "Beypore":           (11.170, 75.830, 76.20, 11.00, {"Arshad": (46, 91), "Basheer": (13, 71)}),
}

XLIM, YLIM = (75.30, 76.62), (10.88, 11.94)


def polys(geom):
    if geom["type"] == "Polygon":
        return [[c[:2] for c in geom["coordinates"][0]]]
    return [[c[:2] for c in p[0]] for p in geom["coordinates"]]


district = json.load(open(GEO + "district.geojson"))["features"]
villages = [f for f in json.load(open(GEO + "village.geojson"))["features"]
            if f["properties"]["DISTRICT"] == "Kozhikode"]
taluks = [f for f in json.load(open(GEO + "taluk.geojson"))["features"]
          if f["properties"]["DISTRICT"] == "Kozhikode"]


def base_map(ax, detail=True, xlim=None, ylim=None):
    ax.set_facecolor("#dbeaf5")  # sea
    for f in district:
        name = f["properties"]["DISTRICT"]
        kz = name == "Kozhikode"
        for ring in polys(f["geometry"]):
            ax.add_patch(Polygon(ring, closed=True,
                                 fc="#fbf8ef" if kz else "#ececec",
                                 ec="#555" if kz else "#bbb",
                                 lw=1.6 if kz else 0.6, zorder=1 if not kz else 2))
    if detail:
        for f in villages:
            for ring in polys(f["geometry"]):
                ax.add_patch(Polygon(ring, closed=True, fill=False, ec="#d9d2bf", lw=0.35, zorder=3))
    for f in taluks:
        for ring in polys(f["geometry"]):
            ax.add_patch(Polygon(ring, closed=True, fill=False, ec="#a89f86", lw=0.8, ls="--", zorder=3))
    for txt, x, y in [("KANNUR", 75.62, 11.90), ("WAYANAD", 76.48, 11.53),
                      ("MALAPPURAM", 76.00, 11.13), ("ARABIAN SEA", 75.74, 10.93)]:
        if (xlim or XLIM)[0] < x < (xlim or XLIM)[1] and (ylim or YLIM)[0] < y < (ylim or YLIM)[1]:
            ax.text(x, y, txt, color="#8a8a8a" if txt != "ARABIAN SEA" else "#6d93b3",
                    fontsize=9 if detail else 6, style="italic", ha="center", zorder=4,
                    rotation=0)
    ax.set_xlim(*(xlim or XLIM)); ax.set_ylim(*(ylim or YLIM))
    ax.set_aspect(1 / math.cos(math.radians(11.4)))
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#999")


def dot_positions(lat, lon, n, step=0.020):
    return [(lon + (i - (n - 1) / 2) * step, lat) for i in range(n)]


# ---------------- Page 1: combined map ----------------
pdf = PdfPages(OUT)
fig = plt.figure(figsize=(16.5, 11.7))  # A3 landscape
ax = fig.add_axes([0.02, 0.03, 0.70, 0.86])
base_map(ax)

for area, (lat, lon, lx, ly, ex) in AREAS.items():
    names = list(ex)
    pts = dot_positions(lat, lon, len(names))
    for (x, y), n in zip(pts, names):
        cov, tot = ex[n]
        ax.scatter(x, y, s=60 + cov * 3.2, c=EXEC[n]["color"], alpha=0.85,
                   edgecolors="white", linewidths=1.2, zorder=10)
    # leader line to the label
    right = lx > 76
    ax.plot([lon, lx - 0.008 if right else lx + 0.25], [lat, ly - 0.01], color="#777", lw=0.7, zorder=8)
    ax.text(lx, ly, area, fontsize=10.5, fontweight="bold", color="#222", zorder=12, va="bottom")
    for i, n in enumerate(names):
        cov, tot = ex[n]
        ax.text(lx, ly - 0.026 * (i + 1), f"● {n}: {cov}/{tot} ({cov / tot:.0%})",
                fontsize=8.8, color=EXEC[n]["color"], zorder=12, va="bottom")

fig.text(0.02, 0.95, "Kozhikode District — Areas Visited by Executives",
         fontsize=22, fontweight="bold", color="#222")
fig.text(0.02, 0.918, "School visit coverage, Jun–Sep 2026  ·  Source: Arshad, Basheer and Jayarajan reports (25 Sep 2026)",
         fontsize=11.5, color="#555")

# side panel
px = 0.745
fig.text(px, 0.86, "Executives", fontsize=14, fontweight="bold")
tot = {"Arshad": (232, 359, "5 assembly areas"),
       "Basheer": (166, 751, "8 assembly areas"),
       "Jayarajan": (152, 800, "10 areas (blocks / municipality)")}
y = 0.82
for n, (c, t, a) in tot.items():
    fig.text(px, y, "●", color=EXEC[n]["color"], fontsize=20, va="center")
    fig.text(px + 0.022, y + 0.008, n, fontsize=12.5, fontweight="bold", va="center")
    fig.text(px + 0.022, y - 0.014, f"{a}  ·  {EXEC[n]['period']}", fontsize=9, color="#555", va="center")
    fig.text(px + 0.022, y - 0.034, f"Schools covered: {c} of {t} ({c / t:.0%})", fontsize=9.5, va="center")
    y -= 0.085

fig.text(px, y, "How to read the map", fontsize=12, fontweight="bold")
notes = [
    "Each dot is one executive's work in an area;",
    "dot size = number of schools covered.",
    "Labels show covered / total schools in that",
    "area (from each executive's own report).",
    "",
    "Where two or three dots sit together, more",
    "than one executive worked that area:",
    "  Kunnamangalam – all three",
    "  Koduvally, Balussery – Basheer & Jayarajan",
    "  Kozhikode North/South, Beypore, Elathur",
    "    – Arshad & Basheer",
    "",
    "Arshad covered only part of Elathur and",
    "Kunnamangalam. Basheer also logged 8 visit",
    "entries in Malappuram (outside the district).",
    "",
    "Dashed lines = taluk boundaries;",
    "thin lines = village boundaries (Census 2001).",
    "Dot positions mark the approximate centre",
    "of each area.",
]
y -= 0.03
for line in notes:
    fig.text(px, y, line, fontsize=9.5, color="#333")
    y -= 0.021

# size legend
handles = [Line2D([], [], ls="", marker="o", color="#888", alpha=0.7,
                  markersize=math.sqrt(60 + v * 3.2), label=f"{v} schools") for v in (10, 50, 100)]
ax.legend(handles=handles, title="Dot size", loc="lower left", bbox_to_anchor=(0.50, 0.01),
          frameon=True, fontsize=9, title_fontsize=9.5, labelspacing=1.3, borderpad=1)
pdf.savefig(fig); plt.close(fig)

# ---------------- Page 2: one map per executive ----------------
fig = plt.figure(figsize=(16.5, 11.7))
fig.text(0.02, 0.95, "Area coverage by executive", fontsize=20, fontweight="bold", color="#222")
fig.text(0.02, 0.922, "Dot size = schools covered; the darker the dot, the higher the share of schools covered in that area.",
         fontsize=11, color="#555")
from matplotlib.colors import to_rgb
WEST = {"Tuneri", "Thodannur", "Melady", "Koyilandy Municipality", "Panthalayani", "Elathur",
        "Kozhikode North", "Kozhikode South", "Beypore"}
OFF = {"Elathur": (-14, 22), "Kozhikode North": (-18, 0), "Kozhikode South": (-18, -18), "Beypore": (-10, -26),
       "Kunnamangalam": (24, -30), "Koduvally": (26, 10), "Thiruvambadi": (12, -14), "Balussery": (16, 22),
       "Panthalayani": (-40, -18), "Koyilandy Municipality": (-14, 8), "Melady": (-12, 0),
       "Thodannur": (-12, 0), "Tuneri": (-12, 10), "Kunnummal": (16, 18), "Perambra": (18, 0)}
for k, n in enumerate(EXEC):
    a = fig.add_axes([0.01 + k * 0.33, 0.05, 0.32, 0.82])
    base_map(a, detail=False, xlim=(75.45, 76.20), ylim=(11.05, 11.86))
    base = to_rgb(EXEC[n]["color"])
    for area, (lat, lon, lx, ly, ex) in AREAS.items():
        if n not in ex:
            continue
        cov, tot_ = ex[n]
        share = cov / tot_
        col = tuple(1 - (1 - c) * (0.25 + 0.75 * share) for c in base)
        a.scatter(lon, lat, s=40 + cov * 2.2, color=col, edgecolors=EXEC[n]["color"], lw=1.2, zorder=10)
        west = area in WEST
        a.annotate(f"{area}\n{cov}/{tot_} ({share:.0%})", (lon, lat),
                   xytext=OFF.get(area, (-10, 0) if west else (10, 0)), textcoords="offset points",
                   ha="right" if west else "left", va="center", arrowprops=dict(arrowstyle="-", color="#888", lw=0.6),
                   fontsize=8.5, zorder=12, color="#222",
                   bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))
    c, t, ar = tot[n]
    a.set_title(f"{n} — {c}/{t} schools covered ({c / t:.0%})", fontsize=13, fontweight="bold",
                color=EXEC[n]["color"])
pdf.savefig(fig); plt.close(fig)

# ---------------- Page 3: table ----------------
fig = plt.figure(figsize=(16.5, 11.7))
fig.text(0.04, 0.94, "Area list — schools covered / total schools", fontsize=20, fontweight="bold", color="#222")
rows = []
for area, (lat, lon, lx, ly, ex) in sorted(AREAS.items(), key=lambda kv: -kv[1][0]):
    cells = [area]
    for n in EXEC:
        cells.append(f"{ex[n][0]} / {ex[n][1]}  ({ex[n][0] / ex[n][1]:.0%})" if n in ex else "–")
    cells.append(str(len(ex)))
    rows.append(cells)
rows.append(["Total (each executive's own area list)"] +
            [f"{tot[n][0]} / {tot[n][1]}  ({tot[n][0] / tot[n][1]:.0%})" for n in EXEC] + [""])
tax = fig.add_axes([0.04, 0.12, 0.92, 0.78]); tax.axis("off")
tbl = tax.table(cellText=rows, colLabels=["Area (north to south)", "Arshad", "Basheer", "Jayarajan", "Executives"],
                loc="upper center", cellLoc="center", colWidths=[0.30, 0.18, 0.18, 0.18, 0.10])
tbl.auto_set_font_size(False); tbl.set_fontsize(11.5); tbl.scale(1, 2.0)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#ccc")
    if r == 0:
        cell.set_facecolor("#333"); cell.get_text().set_color("white"); cell.get_text().set_fontweight("bold")
        if 1 <= c <= 3:
            cell.set_facecolor(EXEC[list(EXEC)[c - 1]]["color"])
    elif r == len(rows):
        cell.set_facecolor("#eee"); cell.get_text().set_fontweight("bold")
    elif c == 0:
        cell.get_text().set_ha("left"); cell._loc = "left"
    elif r % 2 == 0:
        cell.set_facecolor("#f7f7f7")
fig.text(0.04, 0.36,
         "Notes: 'Covered' uses each executive's own definition — Arshad: first visit done; Basheer: visited or given a free pass; "
         "Jayarajan: visited by Jayarajan/Amal\n(another 18 schools in his areas were covered by free passes through other executives). "
         "Totals come from each report's own school list, so the same area can show different totals.\n"
         "Arshad's Elathur and Kunnamangalam are partial areas. Basheer's 8 Malappuram entries are outside the district and not mapped.",
         fontsize=10, color="#444", va="top")
pdf.savefig(fig); plt.close(fig)
pdf.close()
print("wrote", OUT)
