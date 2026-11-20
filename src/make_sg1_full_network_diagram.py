"""
Seed + SG1 network diagram, including the true SG1-internal edges
(citation and amendment relationships directly between SG1 Acts) on
top of each Act's connection to the seed -- not just the seed-star
discovery tree the earlier three-ring diagram used.

Uses a force-directed layout (spring_layout) with the seed Act fixed
at the centre, rather than a rigid ring: with real edges now present
among the 37 SG1 Acts, letting the layout respond to them surfaces
genuine clustering (e.g. tax-related Acts pulling together) that a
fixed ring would hide. At only 38 nodes this is legible without any
of the top-N label truncation the SG2 diagram needed.
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

SEED = "Education and Training Act 2020"
SG1_PATH = Path("data/processed/sg1_final_list.json")
CITATION_EDGES_PATH = Path("data/processed/sg1_internal_citation_edges.json")
AMENDMENT_EDGES_PATH = Path("data/processed/sg1_internal_amendment_edges.json")
OUTPUT_PATH = Path("outputs/figures/sg1_full_network_diagram.png")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
def normalize(name):
    if not name:
        return name
    name = name.replace("\u2019", "'").replace("\u2018", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()

sg1 = json.loads(SG1_PATH.read_text(encoding="utf-8"))
for a in sg1:
    a["act"] = normalize(a["act"])

citation_edges = json.loads(CITATION_EDGES_PATH.read_text(encoding="utf-8"))
amendment_edges = json.loads(AMENDMENT_EDGES_PATH.read_text(encoding="utf-8"))

# ---- merge citation + amendment edges into undirected weighted pairs ----
pair_weight = defaultdict(int)
pair_signal = defaultdict(set)
for e in citation_edges:
    pair = frozenset({normalize(e["source"]), normalize(e["target"])})
    pair_weight[pair] += e["count"]
    pair_signal[pair].add("citation")
for e in amendment_edges:
    pair = frozenset({normalize(e["source"]), normalize(e["target"])})
    pair_weight[pair] += e["count"]
    pair_signal[pair].add("amendment")

# ---- build graph ----
G = nx.Graph()
G.add_node(SEED, layer=0)
for a in sg1:
    G.add_node(a["act"], layer=1)
    G.add_edge(SEED, a["act"], edge_type="seed_link", weight=1)

for pair, weight in pair_weight.items():
    n1, n2 = tuple(pair)
    G.add_edge(n1, n2, edge_type="sg1_internal", weight=math.log1p(weight), raw_weight=weight,
               signal="both" if len(pair_signal[pair]) == 2 else next(iter(pair_signal[pair])))

print(f"Nodes: {G.number_of_nodes()}  Edges: {G.number_of_edges()}")
print(f"SG1-internal edges (merged, undirected): {len(pair_weight)}")

# ---- layout: force-directed, seed fixed at centre ----
init_pos = {SEED: (0.0, 0.0)}
rng = np.random.default_rng(42)
for a in sg1:
    angle = rng.uniform(0, 2 * np.pi)
    init_pos[a["act"]] = (0.8 * np.cos(angle), 0.8 * np.sin(angle))

pos = nx.spring_layout(G, pos=init_pos, fixed=[SEED], k=2.6 / math.sqrt(len(G)),
                        weight="weight", iterations=400, seed=42)

# guarantee clear space around the seed for its label -- the core
# cluster's real density pulls several hub Acts close enough to crowd
# it, regardless of overall spacing
MIN_SEED_DIST = 0.18
seed_x, seed_y = pos[SEED]
for n in G.nodes():
    if n == SEED:
        continue
    x, y = pos[n]
    dx, dy = x - seed_x, y - seed_y
    dist = math.hypot(dx, dy)
    if dist < MIN_SEED_DIST and dist > 1e-9:
        scale = MIN_SEED_DIST / dist
        pos[n] = (seed_x + dx * scale, seed_y + dy * scale)

# ---- palette ----
BLUE = "#2a78d6"           # SG1 node: amendment-only relationship to seed
ORANGE = "#eb6834"         # SG1 node: amendment + citation relationship to seed
AQUA = "#1baf7a"           # SG1 node: citation-only relationship to seed
INK = "#16213e"            # seed
INTERNAL_EDGE = "#8b5fbf"  # SG1-internal edge (citation and/or amendment)
SEED_EDGE = "#d9d8d3"
TEXT_PRIMARY = "#1a1a1a"
SURFACE = "#fcfcfb"

def sg1_classify(a):
    out, cit = a["outgoing_amendments"], a["citations"]
    if out > 0 and cit > 0:
        return ORANGE
    if cit > 0:
        return AQUA
    return BLUE

node_colors = {SEED: INK}
node_sizes = {SEED: 1300}
for a in sg1:
    node_colors[a["act"]] = sg1_classify(a)
    node_sizes[a["act"]] = 70 + (a["combined_score"] / 54) * 150

# ---- render ----
fig, ax = plt.subplots(figsize=(11, 11), dpi=300)
ax.set_facecolor(SURFACE)
fig.patch.set_facecolor(SURFACE)

seed_edges = [(u, v) for u, v, d in G.edges(data=True) if d["edge_type"] == "seed_link"]
nx.draw_networkx_edges(G, pos, edgelist=seed_edges, ax=ax, edge_color=SEED_EDGE, width=0.6, alpha=0.55)

internal_edges = [(u, v) for u, v, d in G.edges(data=True) if d["edge_type"] == "sg1_internal"]
internal_widths = [0.6 + G[u][v]["weight"] * 1.1 for u, v in internal_edges]
nx.draw_networkx_edges(G, pos, edgelist=internal_edges, ax=ax, edge_color=INTERNAL_EDGE,
                        width=internal_widths, alpha=0.55)

nodes = list(G.nodes())
nx.draw_networkx_nodes(G, pos, nodelist=nodes, ax=ax,
                        node_color=[node_colors[n] for n in nodes],
                        node_size=[node_sizes[n] for n in nodes],
                        edgecolors="white", linewidths=1.0)

from adjustText import adjust_text
texts = []
for n in nodes:
    x, y = pos[n]
    label = "Education and\nTraining Act 2020" if n == SEED else n
    fontsize = 10 if n == SEED else 8.5
    color = "white" if n == SEED else TEXT_PRIMARY
    weight = "bold" if n == SEED else "normal"
    t = ax.text(x, y, label, fontsize=fontsize, color=color, ha="center", va="center",
                fontweight=weight, zorder=10 if n == SEED else 6,
                bbox=None if n == SEED else dict(facecolor="white", edgecolor="none", alpha=0.75, pad=0.6))
    if n != SEED:
        texts.append(t)
    else:
        seed_text = t
adjust_text(texts, ax=ax, add_objects=[seed_text], expand=(1.15, 1.35),
            arrowprops=dict(arrowstyle="-", color="#777777", lw=0.5, alpha=0.8),
            max_move=(60, 60))

legend_elems = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor=INK, markeredgecolor="white", markersize=13, label="Seed Act"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor="white", markersize=11, label="SG1 — Amendment only (to seed)"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE, markeredgecolor="white", markersize=11, label="SG1 — Amendment + Citation (to seed)"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=AQUA, markeredgecolor="white", markersize=11, label="SG1 — Citation only (to seed)"),
    Line2D([0], [0], color=SEED_EDGE, lw=2, label="Seed → SG1 connection"),
    Line2D([0], [0], color=INTERNAL_EDGE, lw=2, label="SG1-internal connection (width = strength)"),
]
ax.legend(handles=legend_elems, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=9.5, labelcolor=TEXT_PRIMARY)

ax.set_aspect("equal")
ax.axis("off")
fig.tight_layout()
fig.savefig(str(OUTPUT_PATH), bbox_inches="tight", facecolor=SURFACE, pad_inches=0.05)
fig.savefig(str(OUTPUT_PATH).replace(".png", ".pdf"), bbox_inches="tight", facecolor=SURFACE, pad_inches=0.05)
print(f"Saved -> {OUTPUT_PATH}")