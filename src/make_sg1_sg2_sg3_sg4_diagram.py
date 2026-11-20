"""
make_sg1_sg2_sg3_sg4_diagram.py

Extends make_sg1_sg2_sg3_diagram.py with a fifth concentric ring: the
1,135 SG4 Acts (score >= 6), each attached to its strongest SG3 source
(by that source's own SG3 combined_score) -- exactly mirroring how
each SG3 Act attaches to its strongest SG2 source, and each SG2 Act to
its strongest SG1 source.

No XML fetching involved -- sg4_final_list.json already carries each
Act's combined_score and linked_from (the SG3 Acts that cite/amend
it), the same shape SG1/SG2/SG3 already have, so this is a pure
layout/rendering extension, not a new data-collection stage.

SIZE NOTE: with 1 + 37 + 421 + 893 + 1,135 = 2,487 nodes total, the
outer ring roughly doubles the previous diagram's node count. Same
legibility approach as the SG2/SG3 rings: small unlabelled dots by
default, only the top 20 SG4 Acts by score get text labels, and SG4
gets its own colour (dusty rose) so it reads as visually distinct
from the cooler SG2/SG3 rings at a glance.
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
from figkey_helper import make_fig, finish, FIG_W, TOPN

SEED = "Education and Training Act 2020"
SG1_PATH = Path("data/processed/sg1_final_list.json")
SG2_PATH = Path("data/processed/sg2_final_list.json")
SG3_PATH = Path("data/processed/sg3_final_list.json")
SG4_PATH = Path("data/processed/sg4_final_list.json")
OUTPUT_PATH = Path("outputs/figures/sg1_sg2_sg3_sg4_network_diagram.png")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

N_SHUFFLE_TRIALS = 300

with open(SG1_PATH) as f:
    sg1 = json.load(f)
with open(SG2_PATH) as f:
    sg2 = json.load(f)
with open(SG3_PATH) as f:
    sg3 = json.load(f)
with open(SG4_PATH) as f:
    sg4 = json.load(f)

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
MACRON_MAP = str.maketrans("āēīōūĀĒĪŌŪ", "aeiouAEIOU")
def normalize(name):
    """Citation-suffix strip + apostrophe fix, PLUS macron-stripping and
    whitespace collapsing (folds NBSP into a normal space) -- same fix
    applied to sg2_step26_v2 after discovering the original version of
    this normalize() let real matches silently fail (and drop that Act
    from the diagram) whenever a citation used an NBSP or macron variant
    spelling."""
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    name = m.group(1).strip() if m else name.strip()
    name = name.translate(MACRON_MAP)
    name = re.sub(r"\s+", " ", name).strip()
    return name
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
    linked = [normalize(l) for l in c.get("linked_from", []) if normalize(l) in sg1_names]
    if not linked:
        continue
    G.add_node(c["act"], layer=2)
    best_source = max(linked, key=lambda n: sg1_score.get(n, 0))
    G.add_edge(best_source, c["act"])
    sg2_in_graph.append(c)

sg2_score = {c["act"]: c["combined_score"] for c in sg2_in_graph}
sg2_names_set = set(sg2_score)

sg3_in_graph = []
for c in sg3:
    linked = [l for l in c.get("linked_from", []) if l in sg2_names_set]
    if not linked:
        continue
    G.add_node(c["act"], layer=3)
    best_source = max(linked, key=lambda n: sg2_score.get(n, 0))
    G.add_edge(best_source, c["act"])
    sg3_in_graph.append(c)

sg3_score = {c["act"]: c["combined_score"] for c in sg3_in_graph}
sg3_names_set = set(sg3_score)

sg4_in_graph = []
for c in sg4:
    linked = [l for l in c.get("linked_from", []) if l in sg3_names_set]
    if not linked:
        continue
    G.add_node(c["act"], layer=4)
    best_source = max(linked, key=lambda n: sg3_score.get(n, 0))
    G.add_edge(best_source, c["act"])
    sg4_in_graph.append(c)

print(f"Nodes: {G.number_of_nodes()}  Edges: {G.number_of_edges()}")
print(f"SG2 Acts included: {len(sg2_in_graph)} / {len(sg2)}")
print(f"SG3 Acts included: {len(sg3_in_graph)} / {len(sg3)}")
print(f"SG4 Acts included: {len(sg4_in_graph)} / {len(sg4)}")

# ---- concentric shell layout: shuffle-optimise angular spacing of the
# top-labelled nodes at each ring, same technique as the SG1/SG2/SG3 diagram ----
def optimise_ring_order(names, top_names, seed_offset):
    n = len(names)
    best_order, best_gap = None, -1
    for trial in range(N_SHUFFLE_TRIALS):
        order = names[:]
        random.Random(trial + seed_offset).shuffle(order)
        idx = sorted(i for i, name in enumerate(order) if name in top_names)
        if len(idx) < 2:
            return order, n
        gaps = [(idx[(k + 1) % len(idx)] - idx[k]) % n for k in range(len(idx))]
        g = min(gaps)
        if g > best_gap:
            best_gap, best_order = g, order
    return best_order, best_gap

top_sg2 = sorted(sg2_in_graph, key=lambda c: -c["combined_score"])[:20]
top_sg2_names = {c["act"] for c in top_sg2}
best_sg2_order, best_gap2 = optimise_ring_order([c["act"] for c in sg2_in_graph], top_sg2_names, 0)
print(f"SG2 ring -- best minimum angular gap: {best_gap2} / {len(sg2_in_graph)} positions")

top_sg3 = sorted(sg3_in_graph, key=lambda c: -c["combined_score"])[:20]
top_sg3_names = {c["act"] for c in top_sg3}
best_sg3_order, best_gap3 = optimise_ring_order([c["act"] for c in sg3_in_graph], top_sg3_names, 10_000)
print(f"SG3 ring -- best minimum angular gap: {best_gap3} / {len(sg3_in_graph)} positions")

top_sg4 = sorted(sg4_in_graph, key=lambda c: -c["combined_score"])[:20]
top_sg4_names = {c["act"] for c in top_sg4}
best_sg4_order, best_gap4 = optimise_ring_order([c["act"] for c in sg4_in_graph], top_sg4_names, 20_000)
print(f"SG4 ring -- best minimum angular gap: {best_gap4} / {len(sg4_in_graph)} positions")

shells = [[SEED], [a["act"] for a in sg1], best_sg2_order, best_sg3_order, best_sg4_order]
pos = nx.shell_layout(G, shells)

TARGET_R = {0: 0.0, 1: 1.0, 2: 2.5, 3: 4.2, 4: 6.2}
for n, (x, y) in pos.items():
    r = np.hypot(x, y)
    layer = G.nodes[n]["layer"]
    if r > 1e-9:
        pos[n] = (x / r * TARGET_R[layer], y / r * TARGET_R[layer])
    else:
        pos[n] = (0.0, 0.0)

# ---- palette ----
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
INK = "#16213e"
SG2_GREY = "#9a9990"
SG3_LAVENDER = "#8b7cc9"
SG4_ROSE = "#cf6f96"
TEXT_PRIMARY = "#1a1a1a"
TEXT_SECONDARY = "#52514e"
TEXT_SG3 = "#4a3d8f"
TEXT_SG4 = "#8f3e63"
SURFACE = "#fcfcfb"

def sg1_classify(a):
    out, cit = a["outgoing_amendments"], a["citations"]
    if out > 0 and cit > 0:
        return ORANGE
    if cit > 0:
        return AQUA
    return BLUE

node_colors = {SEED: INK}
node_sizes = {SEED: 1200}
node_edgecolors = {SEED: "white"}
for a in sg1:
    node_colors[a["act"]] = sg1_classify(a)
    node_sizes[a["act"]] = 80 + (a["combined_score"] / 54) * 200
    node_edgecolors[a["act"]] = "white"

sg2_max = max(c["combined_score"] for c in sg2_in_graph)
for c in sg2_in_graph:
    node_colors[c["act"]] = SG2_GREY
    node_sizes[c["act"]] = 5 + (c["combined_score"] / sg2_max) * 45
    node_edgecolors[c["act"]] = "white"

sg3_max = max(c["combined_score"] for c in sg3_in_graph)
for c in sg3_in_graph:
    node_colors[c["act"]] = SG3_LAVENDER
    node_sizes[c["act"]] = 3 + (c["combined_score"] / sg3_max) * 35
    node_edgecolors[c["act"]] = "white"

sg4_max = max(c["combined_score"] for c in sg4_in_graph)
for c in sg4_in_graph:
    node_colors[c["act"]] = SG4_ROSE
    node_sizes[c["act"]] = 2 + (c["combined_score"] / sg4_max) * 28
    node_edgecolors[c["act"]] = "white"

# ---- render ----
fig, ax, keyax = make_fig(len(sg1) + TOPN * 3, 4)
_f = (FIG_W / 32) ** 2
_sg1_names = {a["act"] for a in sg1}
node_sizes = {k: (v * _f * 5 if k in _sg1_names else max(v * _f * 6, 4)) for k, v in node_sizes.items()}
node_sizes[SEED] = 380
ax.set_facecolor(SURFACE)
fig.patch.set_facecolor(SURFACE)

nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#d9d8d3", width=0.183, alpha=0.5)

for layer in (4, 3, 2, 1, 0):
    nodes = [n for n in G if G.nodes[n]["layer"] == layer]
    nx.draw_networkx_nodes(
        G, pos, nodelist=nodes, ax=ax,
        node_color=[node_colors[n] for n in nodes],
        node_size=[node_sizes[n] for n in nodes],
        edgecolors=[node_edgecolors[n] for n in nodes],
        linewidths=0.35 if layer >= 2 else 1.0,
        alpha=0.85 if layer >= 2 else 1.0,
    )


legend_elems = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor=INK, markeredgecolor="white", markersize=13, label="Seed Act"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor="white", markersize=11, label="SG1 — Amendment only"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE, markeredgecolor="white", markersize=11, label="SG1 — Amendment + Citation"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=AQUA, markeredgecolor="white", markersize=11, label="SG1 — Citation only"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=SG2_GREY, markeredgecolor="white", markersize=9, label=f"SG2 ({len(sg2_in_graph)} Acts; top 10 by score numbered)"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=SG3_LAVENDER, markeredgecolor="white", markersize=8, label=f"SG3 ({len(sg3_in_graph)} Acts; top 10 by score numbered)"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=SG4_ROSE, markeredgecolor="white", markersize=7, label=f"SG4 ({len(sg4_in_graph)} Acts; top 10 by score numbered)"),
]
finish(fig, ax, keyax, pos, SEED, sg1, [("SG2", top_sg2), ("SG3", top_sg3), ("SG4", top_sg4)], legend_elems, OUTPUT_PATH, SURFACE)
