"""
make_sg1_sg2_internal_diagram.py

Extends make_sg1_sg2_diagram.py: the same three-layer radial diagram (seed
Act at centre, 37 SG1 Acts in the first ring, 437 SG2 Acts in the outer
ring, identical backbone edges/positions/labels), with SG2-internal
connections added on top as curved chords across the outer ring.

WHY THE INTERNAL LAYER IS FILTERED, AND HOW THE CUTOFF WAS CHOSEN
-------------------------------------------------------------------
sg2_step11_find_internal_links.py found 5,324 distinct SG2-to-SG2 edges
(after deduplication) spread across 376 target Acts. Drawing all of them
would make the diagram unreadable, so a cutoff is needed -- but the
obvious first idea (mirror the score >= 3 cutoff used to build SG2 itself)
does not work here, and it is worth recording why, since the pipeline's
convention is to document each design decision with its specific
justification:

  - The edge mass is extremely concentrated in a handful of mega-hub Acts.
    Criminal Procedure Act 2011 alone is the target of 135 other SG2
    Acts' amendment/citation references.
  - A per-target score/indegree threshold barely reduces the edge count
    no matter how high it's pushed, because it's exactly those few
    highest-scoring Acts that carry almost all the edges: even keeping
    only the top 12 target Acts by indegree (dropping 364 of 376) still
    leaves 855 edges to draw.

What actually gets to a legible count is restricting to a CORE
subnetwork: edges where BOTH the source and the target are themselves
among the most internally-referenced SG2 Acts (TOP_N_HUBS, ranked by
unique-source indegree within the internal-links data). This is a
meaningfully different, and arguably more interesting, cut than a
threshold on raw score -- it surfaces the Acts that are not just
individually well-cited, but that cite/amend each other, i.e. the
densest mutually-connected core of SG2. At TOP_N_HUBS = 25 this core has
199 edges among 25 nodes, which is drawable as clean curved chords
without turning the outer ring into a hairball.

The full 5,324-edge, 376-target unfiltered list is untouched in
data/processed/sg2_internal_links.json for the later centrality /
community-detection stages (Stage 7-8) -- this script only decides what
gets DRAWN, never what gets analysed.
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
INTERNAL_PATH = Path("data/processed/sg2_internal_links.json")
OUTPUT_PATH = Path("outputs/figures/sg1_sg2_internal_network_diagram.png")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

N_SHUFFLE_TRIALS = 300
TOP_N_HUBS = 25  # see docstring above for why this number and not a score threshold

with open(SG1_PATH) as f:
    sg1 = json.load(f)
with open(SG2_PATH) as f:
    sg2 = json.load(f)
with open(INTERNAL_PATH) as f:
    internal = json.load(f)

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
def normalize(name):
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()
for a in sg1:
    a["act"] = normalize(a["act"])

# ---- build backbone graph (identical to make_sg1_sg2_diagram.py) ----
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

backbone_edges = list(G.edges())
print(f"Backbone -- Nodes: {G.number_of_nodes()}  Edges: {G.number_of_edges()}")
print(f"SG2 Acts included: {len(sg2_in_graph)} / {len(sg2)}")

# ---- map internal-links names onto the actual G node names ----
# sg2_internal_links.json's "act"/"linked_from" strings sometimes carry a
# citation suffix (e.g. "Criminal Procedure Act 2011 (2011 No 81)") that
# the SG2 node names in G don't have -- normalize() strips that down to
# what should be the same underlying Act, then map through the actual
# node names found in sg2_in_graph so an edge never gets drawn against a
# name that isn't really a node in G.
norm_to_node = {}
for c in sg2_in_graph:
    norm_to_node[normalize(c["act"])] = c["act"]

indegree = {}          # G-node-name -> unique internal in-degree
sources_by_target = {}  # G-node-name -> set of G-node-names citing it
unmapped_targets = 0
for d in internal:
    t_norm = normalize(d["act"])
    t_node = norm_to_node.get(t_norm)
    if t_node is None:
        unmapped_targets += 1
        continue
    srcs = set()
    for s in d["linked_from"]:
        s_node = norm_to_node.get(normalize(s))
        if s_node is not None and s_node != t_node:
            srcs.add(s_node)
    sources_by_target[t_node] = srcs
    indegree[t_node] = len(srcs)

if unmapped_targets:
    print(f"NOTE: {unmapped_targets} internal-links target(s) didn't map onto a backbone SG2 node (unexpected -- check normalize()).")

ranked = sorted(indegree.items(), key=lambda kv: -kv[1])
hub_nodes = {n for n, _ in ranked[:TOP_N_HUBS]}

core_edges = []
for t in hub_nodes:
    for s in sources_by_target.get(t, ()):
        if s in hub_nodes:
            core_edges.append((s, t))
# de-duplicate (graph is undirected, but source/target roles differ per record)
core_edges = sorted({tuple(sorted(e)) for e in core_edges})

print(f"\nTop {TOP_N_HUBS} SG2-internal hub Acts (by unique in-degree within SG2):")
for n, deg in ranked[:TOP_N_HUBS]:
    print(f"  {deg:>4}  {n}")
print(f"\nCore-only internal edges drawn (both endpoints in top {TOP_N_HUBS}): {len(core_edges)}")

# ---- concentric shell layout (identical logic to make_sg1_sg2_diagram.py,
# extended to also spread the internal-hub nodes around the ring -- without
# this, the shuffle only optimises spacing for the top-20-by-score labels,
# and the 25 hub nodes can land bunched together by chance, which drags
# every one of the 123 core edges into one dense corner instead of letting
# them radiate across the ring) ----
top_sg2 = sorted(sg2_in_graph, key=lambda c: -c["combined_score"])[:20]
top_names = {c["act"] for c in top_sg2}
spacing_priority = top_names | hub_nodes

base_order = [c["act"] for c in sg2_in_graph]
n_sg2 = len(base_order)

best_order = None
best_min_gap = -1
for trial_seed in range(N_SHUFFLE_TRIALS):
    order = base_order[:]
    random.Random(trial_seed).shuffle(order)
    top_idx = sorted(i for i, name in enumerate(order) if name in spacing_priority)
    gaps = [(top_idx[(k + 1) % len(top_idx)] - top_idx[k]) % n_sg2 for k in range(len(top_idx))]
    min_gap = min(gaps)
    if min_gap > best_min_gap:
        best_min_gap = min_gap
        best_order = order

sg2_shell_order = best_order
print(f"\nBest minimum angular gap between labelled+hub nodes: {best_min_gap} / {n_sg2} positions")

shells = [[SEED], [a["act"] for a in sg1], sg2_shell_order]
pos = nx.shell_layout(G, shells)

TARGET_R = {0: 0.0, 1: 1.0, 2: 2.5}
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
HUB_RED = "#c0293c"
TEXT_PRIMARY = "#1a1a1a"
TEXT_SECONDARY = "#52514e"
TEXT_HUB = "#8c1d2c"
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
node_edgecolors = {SEED: "white"}
for a in sg1:
    node_colors[a["act"]] = sg1_classify(a)
    node_sizes[a["act"]] = 90 + (a["combined_score"] / 54) * 220
    node_edgecolors[a["act"]] = "white"

sg2_max = max(c["combined_score"] for c in sg2_in_graph)
for c in sg2_in_graph:
    node_colors[c["act"]] = SG2_GREY
    node_sizes[c["act"]] = 6 + (c["combined_score"] / sg2_max) * 55
    node_edgecolors[c["act"]] = "white"

# hub nodes get a red ring and a larger size so the core stands out
for n in hub_nodes:
    node_sizes[n] = max(node_sizes[n], 40) + 60
    node_edgecolors[n] = HUB_RED

# ---- render ----
fig, ax = plt.subplots(figsize=(24, 24), dpi=200)
ax.set_facecolor(SURFACE)
fig.patch.set_facecolor(SURFACE)

nx.draw_networkx_edges(G, pos, ax=ax, edgelist=backbone_edges,
                        edge_color=GRID, width=0.5, alpha=0.4)
nx.draw_networkx_edges(G, pos, ax=ax, edgelist=core_edges,
                        edge_color=HUB_RED, width=0.9, alpha=0.45,
                        connectionstyle="arc3,rad=0.15", arrows=True, arrowstyle="-")

for layer in (2, 1, 0):
    nodes = [n for n in G if G.nodes[n]["layer"] == layer]
    nx.draw_networkx_nodes(
        G, pos, nodelist=nodes, ax=ax,
        node_color=[node_colors[n] for n in nodes],
        node_size=[node_sizes[n] for n in nodes],
        edgecolors=[node_edgecolors[n] for n in nodes],
        linewidths=[1.6 if n in hub_nodes else (0.5 if layer == 2 else 1.0) for n in nodes],
        alpha=0.9 if layer == 2 else 1.0,
    )

ax.text(*pos[SEED], "Education\nand Training\nAct 2020", fontsize=10.5,
        color="white", ha="center", va="center", fontweight="bold", zorder=10)

for a in sg1:
    x, y = pos[a["act"]]
    angle = np.arctan2(y, x)
    lx, ly = x + 0.16 * np.cos(angle), y + 0.16 * np.sin(angle)
    ha = "left" if np.cos(angle) >= 0 else "right"
    ax.text(lx, ly, a["act"], fontsize=6.0, color=TEXT_PRIMARY, ha=ha, va="center", zorder=6)

# SG2 labels: top-20 by backbone score, top hubs by internal indegree,
# merged where a node is in both so no label is drawn twice
labelled = {}
for c in top_sg2:
    labelled[c["act"]] = f"{c['act']} (score {c['combined_score']})"
for n, deg in ranked[:TOP_N_HUBS]:
    if n in labelled:
        labelled[n] = labelled[n][:-1] + f", internal in-deg {deg})"
    else:
        labelled[n] = f"{n} (internal in-deg {deg})"

for name, label_text in labelled.items():
    x, y = pos[name]
    angle = np.arctan2(y, x)
    lx, ly = x + 0.12 * np.cos(angle), y + 0.12 * np.sin(angle)
    ha = "left" if np.cos(angle) >= 0 else "right"
    is_hub_only = name in hub_nodes and name not in top_names
    ax.text(lx, ly, label_text, fontsize=6.2,
            color=TEXT_HUB if is_hub_only else TEXT_SECONDARY,
            ha=ha, va="center", style="italic", zorder=6)

legend_elems = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor=INK, markeredgecolor="white", markersize=13, label="Seed Act"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor="white", markersize=11, label="SG1 — Amendment only"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE, markeredgecolor="white", markersize=11, label="SG1 — Amendment + Citation"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=AQUA, markeredgecolor="white", markersize=11, label="SG1 — Citation only"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=SG2_GREY, markeredgecolor="white", markersize=9, label="SG2 (422 Acts; top 20 by score labelled)"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=SG2_GREY, markeredgecolor=HUB_RED, markersize=10, markeredgewidth=1.8, label=f"SG2-internal hub (top {TOP_N_HUBS} by internal in-degree)"),
    Line2D([0], [0], color=HUB_RED, lw=1.2, alpha=0.6, label=f"SG2-internal edge ({len(core_edges)} shown, core subnetwork only)"),
]
ax.legend(handles=legend_elems, loc="upper left", bbox_to_anchor=(0.0, 1.0),
          frameon=False, fontsize=10.5, labelcolor=TEXT_PRIMARY)

ax.set_title(
    "Education and Training Act 2020 — Seed, SG1, SG2, and SG2-Internal Connections\n"
    f"37 first-layer Acts, 422 second-layer Acts (score ≥ 3, deduplicated), and the densest {TOP_N_HUBS}-Act "
    f"SG2-internal core ({len(core_edges)} of {sum(len(s) for s in sources_by_target.values())} internal edges)",
    fontsize=15, fontweight="bold", color=TEXT_PRIMARY, pad=20,
)

ax.set_aspect("equal")
ax.axis("off")

fig.tight_layout()
fig.savefig(str(OUTPUT_PATH), bbox_inches="tight", facecolor=SURFACE)
print(f"\nSaved -> {OUTPUT_PATH}")