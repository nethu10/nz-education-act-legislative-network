"""
Fixed visualization: (1) a readable sample of external Acts connected
to the seed Act, rather than all 213 at once, and (2) a genuine
connected cluster of provisions -- using real 'references' edges among
provisions/containers, since those (not the seed Act) are what
provisions actually connect to.
"""

import pickle
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

COLORS = {
    "seed_act": "#5F5E5A", "provision": "#534AB7", "definition": "#D4537E",
    "section_container": "#0F6E56", "structural_container": "#1D9E75",
    "external_act": "#D85A30",
}

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9), facecolor="white")

# ---------- Panel 1: seed Act + a READABLE sample of external Acts ----------
seed_id = "SEED_ACT"
all_external = [n for n, d in G.nodes(data=True) if d.get("node_type") == "external_act"]
sample_external = sorted(all_external, key=lambda n: G.nodes[n]["name"])[:18]  # 18 fits cleanly

H1 = G.subgraph({seed_id} | set(sample_external)).copy()
pos1 = nx.circular_layout(H1)
pos1[seed_id] = (0, 0)  # force seed to true center

colors1 = [COLORS[H1.nodes[n]["node_type"]] for n in H1.nodes()]
sizes1 = [1400 if n == seed_id else 500 for n in H1.nodes()]
nx.draw_networkx_edges(H1, pos1, ax=ax1, alpha=0.4, width=0.8, edge_color="#B4B2A9")
nx.draw_networkx_nodes(H1, pos1, ax=ax1, node_color=colors1, node_size=sizes1, linewidths=0.5, edgecolors="white")

labels1 = {n: (H1.nodes[n].get("name", "Education Act 2020")[:26]) for n in H1.nodes()}
nx.draw_networkx_labels(H1, pos1, labels1, ax=ax1, font_size=8, font_color="#2C2C2A")
ax1.set_title(f"Seed Act \u2192 sample of {len(sample_external)} of 213 connected Acts", fontsize=12, color="#1E2761")
ax1.axis("off")

# ---------- Panel 2: a REAL connected cluster of provisions/containers ----------
prov_container_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") in ("provision", "definition", "section_container", "structural_container")]
subG = G.subgraph(prov_container_nodes)
degrees = dict(subG.degree())
hub_node = max(degrees, key=degrees.get)  # the most-referenced provision/container
ego = nx.ego_graph(G.to_undirected(), hub_node, radius=2)
# Trim to a readable size if the ego network is large
if ego.number_of_nodes() > 25:
    top_nodes = sorted(ego.nodes(), key=lambda n: degrees.get(n, 0), reverse=True)[:25]
    ego = ego.subgraph(top_nodes)

pos2 = nx.spring_layout(ego, k=0.9, seed=7)
colors2 = [COLORS.get(ego.nodes[n].get("node_type"), "#888780") for n in ego.nodes()]
nx.draw_networkx_edges(ego, pos2, ax=ax2, alpha=0.4, width=0.8, edge_color="#B4B2A9")
nx.draw_networkx_nodes(ego, pos2, ax=ax2, node_color=colors2, node_size=500, linewidths=0.5, edgecolors="white")

labels2 = {n: (ego.nodes[n].get("heading") or ego.nodes[n].get("term") or "")[:22] for n in ego.nodes()}
nx.draw_networkx_labels(ego, pos2, labels2, ax=ax2, font_size=7.5, font_color="#2C2C2A")
ax2.set_title(f'Real reference cluster around "{G.nodes[hub_node].get("heading", hub_node)}"', fontsize=12, color="#1E2761")
ax2.axis("off")

for node_type, color in COLORS.items():
    ax1.scatter([], [], c=color, label=node_type, s=80)
fig.legend(*ax1.get_legend_handles_labels(), loc="lower center", ncol=6, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.02))

plt.tight_layout()
out_path = Path("outputs/figures/stage5_graph_visualization.png")
out_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(out_path, dpi=200, facecolor="white", bbox_inches="tight")
print(f"Saved to {out_path}")
print(f"Panel 2 hub node: {G.nodes[hub_node].get('heading', hub_node)} (degree {degrees[hub_node]})")