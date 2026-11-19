"""
Three-layer radial diagram: seed Act (Education and Training Act 2020) at
the centre, SG1 (37 Acts) in the first ring, SG2 (437 Acts) in the outer
ring.

Given the scale difference between SG1 (37) and SG2 (437), SG2 nodes are
rendered small and mostly unlabelled -- only the top 20 by score get text
labels -- to keep the diagram legible rather than an unreadable wall of
text. SG1 keeps the same full-label treatment as the original SG1-only
diagram. Edges from SG1 to SG2 use each SG2 Act's strongest linked SG1
source (by that source's own SG1 score) rather than drawing every link,
since many SG2 Acts connect to several SG1 sources and drawing all of
them would produce a hairball.

Uses networkx's shell_layout for the concentric-ring placement (a much
better fit at this scale than manual polar-coordinate placement), with
custom sizing/coloring/labelling on top via matplotlib.

The SG2 shell order is chosen (not just shuffled once) to spread the
top-20 labelled Acts around the ring: SG2 Acts are stored sorted by
combined_score, and shell_layout places shell members around the ring
in list order, so a single fixed shuffle can still land two of the 20
labelled nodes close together by chance (confirmed visually -- a label
collision showed up at the bottom of the ring with one fixed seed). To
fix this properly rather than just re-rolling the dice once, several
candidate shuffles are tried and the one that maximises the minimum
angular gap between the 20 labelled nodes specifically is kept. This
only affects angular position -- edges are built from a per-node lookup
-- so it changes nothing about correctness, only legibility.
"""
import json
import random
import re
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

SEED = "Education and Training Act 2020"
SG1_PATH = Path("data/processed/sg1_final_list.json")
SG2_PATH = Path("data/processed/sg2_final_list.json")
OUTPUT_PATH = Path("outputs/figures/sg1_sg2_network_diagram.png")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

N_SHUFFLE_TRIALS = 300

with open(SG1_PATH) as f:
    sg1 = json.load(f)
with open(SG2_PATH) as f:
    sg2 = json.load(f)

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
def normalize(name):
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()
for a in sg1:
    a["act"] = normalize(a["act"])

# ---- build graph ----
G = nx.Graph()
G.add_node(SEED, layer=0)

for a in sg1:
    G.add_node(a["act"], layer=1)
    G.add_edge(SEED, a["act"])

sg1_score = {a["act"]: a["combined_score"] for a in sg1}
sg1_names = set(sg1_score)

sg2_in_graph = []
for c in sg2:
    # normalize each linked_from entry the same way SG1 names were
    # normalized above, before checking membership. linked_from mixes two
    # formats -- full "Act (cite)" strings from the amendment signal, and
    # bare names from the citation signal -- so comparing raw strings
    # against the already-stripped sg1_names silently dropped every SG2
    # Act whose only matching source happened to be in the full-citation
    # format. Confirmed via diagnostic: this normalization takes the
    # match rate from 328/437 to 437/437.
    linked = [normalize(l) for l in c.get("linked_from", []) if normalize(l) in sg1_names]
    if not linked:
        continue  # shouldn't happen, but skip defensively rather than crash
    G.add_node(c["act"], layer=2)
    best_source = max(linked, key=lambda n: sg1_score.get(n, 0))
    G.add_edge(best_source, c["act"])
    sg2_in_graph.append(c)

print(f"Nodes: {G.number_of_nodes()}  Edges: {G.number_of_edges()}")
print(f"SG2 Acts included: {len(sg2_in_graph)} / {len(sg2)}")

# top-20 by score, computed now (before layout) so the shuffle search
# below can optimise their angular spacing specifically
top_sg2 = sorted(sg2_in_graph, key=lambda c: -c["combined_score"])[:20]
top_names = {c["act"] for c in top_sg2}

# ---- concentric shell layout ----
# Try several shuffles of the SG2 order and keep whichever one maximises
# the minimum angular gap between the 20 labelled nodes on the ring
# (shell_layout spaces a shell's members evenly in list order, so gap
# in list-index directly corresponds to gap in angle).
base_order = [c["act"] for c in sg2_in_graph]
n_sg2 = len(base_order)

best_order = None
best_min_gap = -1
for trial_seed in range(N_SHUFFLE_TRIALS):
    order = base_order[:]
    random.Random(trial_seed).shuffle(order)
    top_idx = sorted(i for i, name in enumerate(order) if name in top_names)
    gaps = [(top_idx[(k + 1) % len(top_idx)] - top_idx[k]) % n_sg2 for k in range(len(top_idx))]
    min_gap = min(gaps)
    if min_gap > best_min_gap:
        best_min_gap = min_gap
        best_order = order

sg2_shell_order = best_order
print(f"Best minimum angular gap between labelled nodes: {best_min_gap} / {n_sg2} positions")

shells = [
    [SEED],
    [a["act"] for a in sg1],
    sg2_shell_order,
]
pos = nx.shell_layout(G, shells)

TARGET_R = {0: 0.0, 1: 1.0, 2: 2.5}
for n, (x, y) in pos.items():
    r = np.hypot(x, y)
    layer = G.nodes[n]["layer"]
    if r > 1e-9:
        pos[n] = (x / r * TARGET_R[layer], y / r * TARGET_R[layer])
    else:
        pos[n] = (0.0, 0.0)

# ---- palette (same validated categorical slots as the SG1 diagram) ----
BLUE = "#2a78d6"    # Amendment
ORANGE = "#eb6834"  # Both
AQUA = "#1baf7a"    # Citation
INK = "#16213e"      # seed
SG2_GREY = "#9a9990"
TEXT_PRIMARY = "#1a1a1a"
TEXT_SECONDARY = "#52514e"
GRID = "#d9d8d3"
SURFACE = "#fcfcfb"

def sg1_classify(a):
    out, cit = a["outgoing_amendments"], a["citations"]
    if out > 0 and cit > 0:
        return ORANGE
    if cit > 0:
        return AQUA
    return BLUE

node_colors = {SEED: INK}
node_sizes = {SEED: 1400}
for a in sg1:
    node_colors[a["act"]] = sg1_classify(a)
    node_sizes[a["act"]] = 90 + (a["combined_score"] / 54) * 220

sg2_max = max(c["combined_score"] for c in sg2_in_graph)
for c in sg2_in_graph:
    node_colors[c["act"]] = SG2_GREY
    node_sizes[c["act"]] = 6 + (c["combined_score"] / sg2_max) * 55

# ---- render ----
fig, ax = plt.subplots(figsize=(22, 22), dpi=200)
ax.set_facecolor(SURFACE)
fig.patch.set_facecolor(SURFACE)
nx.draw_networkx_edges(G, pos, ax=ax, edge_color=GRID, width=0.5, alpha=0.4)

for layer in (2, 1, 0):
    nodes = [n for n in G if G.nodes[n]["layer"] == layer]
    nx.draw_networkx_nodes(
        G, pos, nodelist=nodes, ax=ax,
        node_color=[node_colors[n] for n in nodes],
        node_size=[node_sizes[n] for n in nodes],
        edgecolors="white", linewidths=0.5 if layer == 2 else 1.0,
        alpha=0.85 if layer == 2 else 1.0,
    )

# seed label
ax.text(*pos[SEED], "Education\nand Training\nAct 2020", fontsize=10.5,
        color="white", ha="center", va="center", fontweight="bold", zorder=10)

# SG1 labels (all 37, radiating outward)
for a in sg1:
    x, y = pos[a["act"]]
    angle = np.arctan2(y, x)
    lx, ly = x + 0.16 * np.cos(angle), y + 0.16 * np.sin(angle)
    ha = "left" if np.cos(angle) >= 0 else "right"
    ax.text(lx, ly, a["act"], fontsize=6.0, color=TEXT_PRIMARY, ha=ha, va="center", zorder=6)

# top 20 SG2 labels only
for c in top_sg2:
    x, y = pos[c["act"]]
    angle = np.arctan2(y, x)
    lx, ly = x + 0.11 * np.cos(angle), y + 0.11 * np.sin(angle)
    ha = "left" if np.cos(angle) >= 0 else "right"
    ax.text(lx, ly, f"{c['act']} ({c['combined_score']})", fontsize=6.2,
             color=TEXT_SECONDARY, ha=ha, va="center", style="italic", zorder=6)

# legend
legend_elems = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor=INK, markeredgecolor="white", markersize=13, label="Seed Act"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor="white", markersize=11, label="SG1 — Amendment only"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE, markeredgecolor="white", markersize=11, label="SG1 — Amendment + Citation"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=AQUA, markeredgecolor="white", markersize=11, label="SG1 — Citation only"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=SG2_GREY, markeredgecolor="white", markersize=9, label="SG2 (422 Acts; top 20 labelled)"),
]
leg = ax.legend(handles=legend_elems, loc="upper left", bbox_to_anchor=(0.0, 1.0),
                 frameon=False, fontsize=11, labelcolor=TEXT_PRIMARY)

ax.set_title("Education and Training Act 2020 — Seed, SG1, and SG2\n"
             "37 first-layer Acts and 422 second-layer Acts (score ≥ 3, deduplicated)",
             fontsize=16, fontweight="bold", color=TEXT_PRIMARY, pad=20)

ax.set_aspect("equal")
ax.axis("off")

fig.tight_layout()
fig.savefig(str(OUTPUT_PATH), bbox_inches="tight", facecolor=SURFACE)
print(f"Saved -> {OUTPUT_PATH}")