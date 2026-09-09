"""
Visualizes the amendment network as concentric rings around the seed
Act, using the real expansion_ring attribute set during the Stage 6
merge. Ring 1 (13 Acts) is labelled individually since it's small
enough to read; Ring 2 (969 Acts) is shown as a dense outer ring
without individual labels, since that many labels would be unreadable.
"""

import pickle
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

seed_id = "SEED_ACT"
ring1 = [n for n, d in G.nodes(data=True) if d.get("expansion_ring") == 1]
ring2 = [n for n, d in G.nodes(data=True) if d.get("expansion_ring") == 2]
# Anything external_act but never tagged with a ring is an original Stage-2
# connection that wasn't among the 13 selected for expansion -- treat as ring 1.5
other_external = [n for n, d in G.nodes(data=True)
                   if d.get("node_type") == "external_act" and n not in ring1 and n not in ring2]

print(f"Seed: 1, Ring 1: {len(ring1)}, Ring 2: {len(ring2)}, Other original connections: {len(other_external)}")

H = G.subgraph([seed_id] + ring1 + ring2 + other_external).copy()

# shell_layout draws each list as its own concentric ring, seed innermost
shells = [[seed_id], ring1, other_external, ring2]
pos = nx.shell_layout(H, nlist=shells)

fig, ax = plt.subplots(figsize=(14, 14), facecolor="white")

nx.draw_networkx_edges(H, pos, ax=ax, alpha=0.15, width=0.5, edge_color="#B4B2A9", arrows=False)

nx.draw_networkx_nodes(H, pos, nodelist=[seed_id], ax=ax, node_color="#1E2761", node_size=1400)
nx.draw_networkx_nodes(H, pos, nodelist=ring1, ax=ax, node_color="#D85A30", node_size=450)
nx.draw_networkx_nodes(H, pos, nodelist=other_external, ax=ax, node_color="#E8A67B", node_size=90)
nx.draw_networkx_nodes(H, pos, nodelist=ring2, ax=ax, node_color="#F1D9C4", node_size=25)

labels = {seed_id: "Education and\nTraining Act 2020"}
for n in ring1:
    labels[n] = G.nodes[n].get("name", n)[:28]
nx.draw_networkx_labels(H, pos, labels, ax=ax, font_size=8, font_color="#2C2C2A")

ax.scatter([], [], c="#1E2761", s=200, label="Seed Act (1)")
ax.scatter([], [], c="#D85A30", s=200, label=f"Ring 1 \u2014 selected for expansion ({len(ring1)})")
ax.scatter([], [], c="#E8A67B", s=100, label=f"Original connections, not expanded ({len(other_external)})")
ax.scatter([], [], c="#F1D9C4", s=60, label=f"Ring 2 \u2014 discovered via Ring 1 ({len(ring2)})")
ax.legend(loc="upper left", frameon=False, fontsize=10)

ax.set_title("Amendment Network \u2014 Concentric Ring Expansion from the Seed Act", fontsize=14, color="#1E2761")
ax.axis("off")
plt.tight_layout()

out_path = Path("outputs/figures/stage7_ring_diagram.png")
out_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(out_path, dpi=200, facecolor="white", bbox_inches="tight")
print(f"Saved to {out_path}")