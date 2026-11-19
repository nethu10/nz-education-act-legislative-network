"""
Stage: SG1 visualisation
Builds a radial hub-and-spoke network diagram of SG1 -- the Education and
Training Act 2020 (seed, centre) and its 37 first-layer connected Acts.

Encoding:
  - Node colour   = relationship type (Amendment only / Both / Citation only)
  - Node size     = combined score (bigger = more strongly connected)
  - Ring (radius) = score tier (closer to centre = stronger connection)
  - Edge colour   = matches the node it connects to

Input : data/processed/sg1_final_list.json
        (a list of records: act, outgoing_amendments, incoming_amendments,
         citations, combined_score -- i.e. your finalised SG1 output)
Output: data/processed/sg1_network_diagram.png
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.lines import Line2D

# ---------------------------------------------------------------
# 1. Load your SG1 data
# ---------------------------------------------------------------
INPUT_PATH = Path("data/processed/sg1_final_list.json")
OUTPUT_PATH = Path("outputs/figures/sg1_network_diagram.png")

with open(INPUT_PATH, encoding="utf-8") as f:
    raw = json.load(f)

# handle either a plain list, or a dict wrapping the list under a key
if isinstance(raw, dict):
    for key in ("acts", "sg1", "ranking", "data"):
        if key in raw:
            raw = raw[key]
            break

acts = list(raw)
print(f"Loaded {len(acts)} Acts from {INPUT_PATH}")

# ---------------------------------------------------------------
# 2. Colours (colourblind-checked categorical triplet) and classification
# ---------------------------------------------------------------
BLUE = "#2a78d6"     # Amendment only
ORANGE = "#eb6834"   # Amendment + Citation (both)
AQUA = "#1baf7a"      # Citation only
INK = "#16213e"       # seed / hub node
TEXT_PRIMARY = "#1a1a1a"
TEXT_SECONDARY = "#52514e"
GRID = "#d9d8d3"
SURFACE = "#fcfcfb"

def classify(a):
    out, cit = a.get("outgoing_amendments", 0), a.get("citations", 0)
    if out > 0 and cit > 0:
        return "Both", ORANGE
    if cit > 0:
        return "Citation", AQUA
    return "Amendment", BLUE

for a in acts:
    a["category"], a["color"] = classify(a)

# ---------------------------------------------------------------
# 3. Assign each Act to a score tier (ring) -- adjust the bands if your
#    own score range differs a lot from 6-54
# ---------------------------------------------------------------
def tier_of(score):
    if score >= 30:
        return 0
    if score >= 15:
        return 1
    if score >= 10:
        return 2
    return 3

RADII = [1.55, 2.55, 3.55, 4.55]
for a in acts:
    a["tier"] = tier_of(a["combined_score"])
    a["radius"] = RADII[a["tier"]]

# group by tier, then by category within tier, so same-type nodes cluster
by_tier = defaultdict(list)
for a in acts:
    by_tier[a["tier"]].append(a)

cat_order = {"Amendment": 0, "Both": 1, "Citation": 2}
for t in by_tier:
    by_tier[t].sort(key=lambda a: (cat_order[a["category"]], -a["combined_score"]))

# ---------------------------------------------------------------
# 4. Lay nodes out in a circle, per ring, starting at the top (12 o'clock)
# ---------------------------------------------------------------
START_DEG = 90
tier_offsets = [0, -4, -2.4, -1.3]   # small stagger so labels don't all align radially
for t, items in by_tier.items():
    n = len(items)
    offset = tier_offsets[min(t, len(tier_offsets) - 1)]
    for i, a in enumerate(items):
        angle_deg = START_DEG - offset - (360.0 / n) * i
        angle = math.radians(angle_deg)
        a["angle"] = angle
        a["x"] = a["radius"] * math.cos(angle)
        a["y"] = a["radius"] * math.sin(angle)

# node size scales with score (sequential encoding)
scores = [a["combined_score"] for a in acts]
smin, smax = min(scores), max(scores)
def node_size(score):
    lo, hi = 70, 620
    frac = (score - smin) / (smax - smin) if smax > smin else 0.5
    return lo + frac * (hi - lo)

# ---------------------------------------------------------------
# 5. Draw
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(16, 16), dpi=200)
ax.set_facecolor(SURFACE)
fig.patch.set_facecolor(SURFACE)

for r in RADII:
    ax.add_patch(Circle((0, 0), r, fill=False, edgecolor=GRID, linewidth=1, zorder=1))

for a in acts:
    ax.plot([0, a["x"]], [0, a["y"]], color=a["color"], linewidth=1.1, alpha=0.55,
             zorder=2, solid_capstyle="round")

for a in acts:
    ax.scatter(a["x"], a["y"], s=node_size(a["combined_score"]), color=a["color"],
               edgecolor="white", linewidth=1.1, zorder=4)

LABEL_R_PAD = 0.30
for a in acts:
    lx = (a["radius"] + LABEL_R_PAD) * math.cos(a["angle"])
    ly = (a["radius"] + LABEL_R_PAD) * math.sin(a["angle"])
    ha = "left" if math.cos(a["angle"]) >= 0 else "right"
    label = a["act"]
    if len(label) > 46:
        words = label.split(" ")
        line1, line2, total = [], [], 0
        for w in words:
            if total + len(w) < 30 and not line2:
                line1.append(w); total += len(w) + 1
            else:
                line2.append(w)
        label = " ".join(line1) + "\n" + " ".join(line2)
    ax.text(lx, ly, f"{label}  ({a['combined_score']})", fontsize=8.3, color=TEXT_PRIMARY,
            ha=ha, va="center", zorder=5, linespacing=1.25)

# hub (seed) node -- sized generously so the label never spills past its edge
ax.scatter(0, 0, s=11800, color=INK, edgecolor="white", linewidth=2.4, zorder=6)
ax.text(0, 0.14, "Education\nand Training\nAct 2020", fontsize=11.5, color="white",
        ha="center", va="center", fontweight="bold", zorder=7, linespacing=1.35)
ax.text(0, -0.52, "(seed Act)", fontsize=9, color="#aebbd6",
        ha="center", va="center", zorder=7, style="italic")

# tier ring labels, placed in one consistently clear sector with a light halo
tier_labels = ["score \u2265 30", "score 15\u201329", "score 10\u201314", "score 6\u20139"]
LABEL_ANGLE = math.radians(236)
for r, lbl in zip(RADII, tier_labels):
    tx, ty = r * math.cos(LABEL_ANGLE), r * math.sin(LABEL_ANGLE)
    ax.text(tx, ty, lbl, fontsize=8.3, color=TEXT_SECONDARY, ha="center", va="center", zorder=3,
            bbox=dict(facecolor=SURFACE, edgecolor="none", alpha=0.92, pad=1.6))

# legend: relationship type
legend_elems = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor="white", markersize=11, label="Amendment only"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE, markeredgecolor="white", markersize=11, label="Amendment + Citation (both)"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=AQUA, markeredgecolor="white", markersize=11, label="Citation only"),
]
leg1 = ax.legend(handles=legend_elems, loc="upper left", bbox_to_anchor=(0.0, 1.02),
                  frameon=False, fontsize=10.5, title="Relationship type", title_fontsize=11,
                  labelcolor=TEXT_PRIMARY)
leg1.get_title().set_color(TEXT_PRIMARY)
ax.add_artist(leg1)

# legend: node size = score
size_elems = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor="#9a9990", markeredgecolor="white", markersize=5, label=f"score {smin}"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor="#9a9990", markeredgecolor="white", markersize=10, label=f"score {(smin+smax)//2}"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor="#9a9990", markeredgecolor="white", markersize=16, label=f"score {smax}"),
]
leg2 = ax.legend(handles=size_elems, loc="upper right", bbox_to_anchor=(1.0, 1.02),
                  frameon=False, fontsize=10.5, title="Node size = combined score", title_fontsize=11,
                  labelcolor=TEXT_PRIMARY, labelspacing=1.3)
leg2.get_title().set_color(TEXT_PRIMARY)

ax.set_title(f"SG1 \u2014 First-Layer Subgraph of the Education and Training Act 2020\n"
             f"{len(acts)} directly connected Acts, ranked by combined amendment + citation strength",
             fontsize=15, fontweight="bold", color=TEXT_PRIMARY, pad=18)

lim = RADII[-1] + 2.4
ax.set_xlim(-lim, lim)
ax.set_ylim(-lim, lim)
ax.set_aspect("equal")
ax.axis("off")

fig.tight_layout()
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUTPUT_PATH, bbox_inches="tight", facecolor=SURFACE)
print(f"Saved: {OUTPUT_PATH}")