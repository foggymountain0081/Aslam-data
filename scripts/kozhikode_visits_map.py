"""Kozhikode district map of areas visited by executives -> PDF."""
import sys, os
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

GEO, OUT = sys.argv[1], sys.argv[2]
WORK = os.path.dirname(os.path.abspath(__file__))

# Approximate centre (lat, lon) of each area as named in the reports
LOC = {
    "Kozhikode City South":        (11.232, 75.786),
    "Kozhikode City North":        (11.285, 75.776),
    "Feroke – Ramanattukara":      (11.172, 75.842),
    "Mavoor – Perumanna":          (11.262, 75.900),
    "Chelannur – Kakkodi":         (11.356, 75.815),
    "Kunnamangalam":               (11.305, 75.877),
    "Mukkam / Thiruvambady":       (11.335, 75.995),
    "Balussery":                   (11.448, 75.830),
    "Koduvally / Thamarassery":    (11.385, 75.925),
    "Perambra":                    (11.562, 75.760),
    "Kuttiyadi / Kunnummal":       (11.655, 75.755),
    "Nadapuram":                   (11.684, 75.655),
    "Thiruvallur / Kadameri":      (11.625, 75.625),
    "Meppayur / Koyilandy side":   (11.528, 75.705),
}

# Schools / institutions visited, per executive and area (from the work reports)
VISITS = {
    "Arshad": {
        "Kozhikode City South": 143, "Kozhikode City North": 116,
        "Feroke – Ramanattukara": 67, "Mavoor – Perumanna": 21,
        "Chelannur – Kakkodi": 24, "Kunnamangalam": 11,
    },
    "Basheer": {
        "Balussery": 18, "Chelannur – Kakkodi": 31, "Koduvally / Thamarassery": 33,
        "Mavoor – Perumanna": 37, "Kunnamangalam": 52,
        "Kozhikode City North": 17, "Feroke – Ramanattukara": 8,
    },
    "Jayarajan": {
        "Balussery": 47, "Koduvally / Thamarassery": 28, "Perambra": 38,
        "Mukkam / Thiruvambady": 32, "Kuttiyadi / Kunnummal": 31,
        "Nadapuram": 15, "Thiruvallur / Kadameri": 7,
        "Meppayur / Koyilandy side": 18,
    },
}
COLOR = {"Arshad": "#2a78d6", "Basheer": "#e07b1a", "Jayarajan": "#1f9e6e"}
NOTES = {  # how report area names map to the map labels
    ("Basheer", "Chelannur – Kakkodi"): "Chelannur",
    ("Basheer", "Mavoor – Perumanna"): "Mavoor",
    ("Basheer", "Kozhikode City North"): "Kozhikode City (URC North)",
    ("Basheer", "Koduvally / Thamarassery"): "Koduvally",
    ("Basheer", "Feroke – Ramanattukara"): "Feroke / Ramanattukara",
    ("Jayarajan", "Mukkam / Thiruvambady"): "Kunnamangalam (Mukkam/Thiruvambady)",
    ("Jayarajan", "Thiruvallur / Kadameri"): "Thiruvallur / Kadameri (Vadakara)",
}

# ---------- map ----------
dist = gpd.read_file(os.path.join(GEO, "dist.geojson")).to_crs(4326)
taluk = gpd.read_file(os.path.join(GEO, "taluk.geojson")).to_crs(4326)
koz = dist[dist.dtname == "Kozhikode"]
ktal = taluk[taluk.DISTRICT.str.contains("Kozhikode")]

minx, miny, maxx, maxy = koz.total_bounds
W_, H_ = (maxx - minx + 0.20) * 0.98, (maxy - miny + 0.10)
fig, ax = plt.subplots(figsize=(10, 10 * H_ / W_))
fig.patch.set_facecolor("white")
ax.set_facecolor("#e8f1f8")
dist.plot(ax=ax, color="#f1efe9", edgecolor="#c9c4b8", linewidth=0.6)
koz.plot(ax=ax, color="#fbfaf6", edgecolor="#555", linewidth=1.4)
ktal.boundary.plot(ax=ax, color="#9a948a", linewidth=0.7, linestyle="--")
for _, r in ktal.iterrows():
    p = r.geometry.representative_point()
    name = {"Quilandy": "Koyilandy"}.get(r.TALUK, r.TALUK)
    ax.text(p.x + (0.07 if name == "Koyilandy" else 0.10), p.y + {"Vadakara": -0.02, "Koyilandy": 0.06}.get(name, -0.05),
            f"{name} Taluk", fontsize=9, color="#8a8478", style="italic", ha="center")
for _, r in dist[dist.dtname.isin(["Kannur", "Wayanad", "Malappuram"])].iterrows():
    p = r.geometry.representative_point()
    ax.text(p.x, p.y, r.dtname, fontsize=10, color="#a8a296", ha="center", clip_on=True)
ax.text(75.55, 11.35, "Arabian Sea", fontsize=11, color="#6c8fae", style="italic", rotation=70)

execs = list(VISITS)
off = {"Arshad": -1, "Basheer": 0, "Jayarajan": 1}
for area, (lat, lon) in LOC.items():
    present = [e for e in execs if area in VISITS[e]]
    n = len(present)
    for i, e in enumerate(present):
        dx = (i - (n - 1) / 2) * 0.034
        v = VISITS[e][area]
        ax.scatter(lon + dx, lat, s=60 + v * 4.2, color=COLOR[e], alpha=0.82,
                   edgecolor="white", linewidth=1.2, zorder=5)
        ax.text(lon + dx, lat, str(v), fontsize=7.5, color="white", weight="bold",
                ha="center", va="center", zorder=6)
    ax.annotate(area, (lon, lat), xytext=(0, -17 - 0.06 * max(VISITS[e][area] for e in present)),
                textcoords="offset points", ha="center", fontsize=8.2, color="#222",
                weight="bold", zorder=7,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))

minx, miny, maxx, maxy = koz.total_bounds
ax.set_xlim(minx - 0.12, maxx + 0.08)
ax.set_ylim(miny - 0.05, maxy + 0.05)
ax.set_aspect(1 / 0.98, adjustable="box")
ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
for s in ax.spines.values():
    s.set_color("#999")
handles = [Line2D([], [], marker="o", ls="", ms=11, color=COLOR[e],
                  label=f"{e} – {sum(VISITS[e].values())} visits, {len(VISITS[e])} areas")
           for e in execs]
ax.legend(handles=handles, loc="upper right", fontsize=9.5, title="Executive",
          title_fontsize=10, framealpha=0.95)
ax.text(0.01, 0.01, "Number in circle = schools/institutions visited (circle size scales with count).\n"
        "Markers placed at approximate area centres; dashed lines = taluk boundaries.",
        transform=ax.transAxes, fontsize=7.5, color="#555", va="bottom",
        bbox=dict(fc="white", ec="none", alpha=0.8))
# north arrow
ax.annotate("N", xy=(0.06, 0.95), xytext=(0.06, 0.88), xycoords="axes fraction",
            ha="center", fontsize=11, weight="bold",
            arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.5))
plt.tight_layout()
png = os.path.join(WORK, "kozhikode_visits_map.png")
fig.savefig(png, dpi=220, bbox_inches="tight", pad_inches=0.05)

# ---------- PDF ----------
ss = getSampleStyleSheet()
h = ParagraphStyle("h", parent=ss["Title"], fontSize=17, spaceAfter=2)
sub = ParagraphStyle("s", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor("#555"),
                     alignment=1)
small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=8, leading=10)
doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                        topMargin=12 * mm, bottomMargin=12 * mm,
                        title="Kozhikode District – Areas Visited by Executives")
from PIL import Image as PI
iw, ih = PI.open(png).size
W = min(182 * mm, 245 * mm * iw / ih)
el = [Paragraph("Kozhikode District – Areas Visited by Executives", h),
      Paragraph("Arshad · Basheer · Jayarajan &nbsp;|&nbsp; Source: executive work reports "
                "(field period Aug–Oct 2026) &nbsp;|&nbsp; Prepared 29 Oct 2026", sub),
      Spacer(1, 5),
      Image(png, width=W, height=W * ih / iw),
      PageBreak(),
      Paragraph("Area-wise visits by executive", ss["Heading2"])]

areas = list(LOC)
hdr = ["Area", "Arshad", "Basheer", "Jayarajan", "Total"]
rows = [hdr]
for a in areas:
    vals = [VISITS[e].get(a) for e in execs]
    rows.append([a] + [str(v) if v else "–" for v in vals] + [str(sum(v or 0 for v in vals))])
tot = [sum(VISITS[e].values()) for e in execs]
rows.append(["TOTAL"] + [str(t) for t in tot] + [str(sum(tot))])
t = Table(rows, colWidths=[70 * mm, 26 * mm, 26 * mm, 26 * mm, 24 * mm])
st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5),
      ("FONT", (0, 1), (-1, -1), "Helvetica", 9.5),
      ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9.5),
      ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#33393f")),
      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
      ("ALIGN", (1, 0), (-1, -1), "CENTER"),
      ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8c8c8")),
      ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eceae4")),
      ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f7f7f5")]),
      ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
for i, e in enumerate(execs, start=1):
    st.append(("TEXTCOLOR", (i, 0), (i, 0), colors.HexColor(COLOR[e])))
    st.append(("BACKGROUND", (i, 0), (i, 0), colors.HexColor("#33393f")))
    st.append(("TEXTCOLOR", (i, 1), (i, -2), colors.HexColor(COLOR[e])))
t.setStyle(TableStyle(st))
el += [t, Spacer(1, 8)]

el.append(Paragraph("Overlap – areas covered by more than one executive", ss["Heading3"]))
for a in areas:
    who = [e for e in execs if a in VISITS[e]]
    if len(who) > 1:
        el.append(Paragraph(f"• <b>{a}</b>: " + ", ".join(f"{e} ({VISITS[e][a]})" for e in who), small))
el.append(Spacer(1, 6))
el.append(Paragraph("Notes", ss["Heading3"]))
notes = [
    "Counts are total schools/institutions visited in each area as given in each report: "
    "Arshad = 'Total visited' (directory + non-directory); Basheer = 'Visited' (district list); "
    "Jayarajan = 'Visited (in list)' + 'Other visited'.",
    "Report area names were merged onto common map locations: "
    + "; ".join(f"{e}'s '{v}' → {a}" for (e, a), v in NOTES.items()) + ".",
    "Marker positions are approximate centres of each area, not individual school locations. "
    "Boundaries: Census 2011 district & taluk outlines (Thamarassery taluk, formed 2013, falls "
    "within the Kozhikode/Koyilandy outlines shown).",
]
for n in notes:
    el.append(Paragraph("• " + n, small))
doc.build(el)
print("wrote", OUT)
