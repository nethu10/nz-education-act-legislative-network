"""
Visualizes the graph's true current structure -- the two disconnected
networks confirmed in the fragmentation diagnostics, plus a real sample
from within the internal citation network specifically. Run before
Katz centrality so the two-network split is seen, not just proven
numerically.
"""

import pickle
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

components = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
amendment_net = components[0]
internal_net = components[1]
small_components = components[2:]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9), facecolor="white")

# ---------- Panel 1: structural overview, schematic not spring-layout ----------
import numpy as np

def scatter_blob(ax, center, n_points, radius, color, size):
    angles = np.random.uniform(0, 2 * np.pi, n_points)
    radii = radius * np.sqrt(np.random.uniform(0, 1, n_points))
    x = center[0] + radii * np.cos(angles)
    y = center[1] + radii * np.sin(angles)
    ax.scatter(x, y, c=color, s=size, alpha=0.6, linewidths=0)

scatter_blob(ax1, (-3, 0), len(amendment_net), 1.8, "#D85A30", 14)
scatter_blob(ax1, (3, 0), len(internal_net), 1.6, "#534AB7", 10)
small_sizes = [len(c) for c in small_components]
np.random.seed(1)
sx = np.random.uniform(-1, 1, len(small_components))
sy = np.random.uniform(-4.2, -3.2, len(small_components))
ax1.scatter(sx, sy, c="#8A877E", s=[s * 8 for s in small_sizes], alpha=0.5, linewidths=0)

ax1.annotate("", xy=(1.0, 0), xytext=(-1.0, 0),
             arrowprops=dict(arrowstyle="-", color="red", lw=2, linestyle="dashed"))
ax1.text(0, 0.4, "NO CONNECTION", ha="center", fontsize=11, color="red", fontweight="bold")

ax1.text(-3, 2.3, f"Amendment Network\n{len(amendment_net)} nodes\n(seed Act + connected Acts)",
          ha="center", fontsize=12, color="#8B3A1F", fontweight="bold")
ax1.text(3, 2.1, f"Internal Citation Network\n{len(internal_net)} nodes\n(provisions, definitions, containers)",
          ha="center", fontsize=12, color="#3C3489", fontweight="bold")
ax1.text(0, -3.7, f"{len(small_components)} small/isolated components\n({sum(small_sizes)} nodes total)",
          ha="center", fontsize=10, color="#5F5E5A")

ax1.set_title("Structural Overview \u2014 Two Disconnected Networks", fontsize=13, color="#1E2761")
ax1.set_xlim(-6, 6)
ax1.set_ylim(-5.5, 3)
ax1.axis("off")

# ---------- Panel 2: real sample from within the internal citation network ----------
H = G.subgraph(internal_net).copy()
degrees = dict(H.degree())
hub = max(degrees, key=degrees.get)
ego = nx.ego_graph(G.to_undirected(), hub, radius=2)
ego = G.subgraph(set(ego.nodes()) & internal_net).copy()
if ego.number_of_nodes() > 25:
    top_nodes = sorted(ego.nodes(), key=lambda n: degrees.get(n, 0), reverse=True)[:25]
    ego = ego.subgraph(top_nodes)

COLORS = {"provision": "#534AB7", "definition": "#D4537E", "section_container": "#0F6E56", "structural_container": "#1D9E75"}
pos2 = nx.spring_layout(ego, k=0.9, seed=7)
colors2 = [COLORS.get(ego.nodes[n].get("node_type"), "#888780") for n in ego.nodes()]
nx.draw_networkx_edges(ego, pos2, ax=ax2, alpha=0.4, width=0.8, edge_color="#B4B2A9")
nx.draw_networkx_nodes(ego, pos2, ax=ax2, node_color=colors2, node_size=500, linewidths=0.5, edgecolors="white")
labels2 = {n: (ego.nodes[n].get("heading") or ego.nodes[n].get("term") or "")[:22] for n in ego.nodes()}
nx.draw_networkx_labels(ego, pos2, labels2, ax=ax2, font_size=7.5, font_color="#2C2C2A")
ax2.set_title(f'Sample cluster around "{G.nodes[hub].get("heading", hub)}"\n(within the {len(internal_net)}-node internal network)', fontsize=12, color="#1E2761")
ax2.axis("off")

plt.tight_layout()
out_path = Path("outputs/figures/stage7_final_structure.png")
out_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(out_path, dpi=200, facecolor="white", bbox_inches="tight")
print(f"Saved to {out_path}")
print(f"Hub node for panel 2: {G.nodes[hub].get('heading', hub)} (degree {degrees[hub]})")