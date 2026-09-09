"""
Confirm the hypothesis that the giant component is almost entirely the
external-Act amendment web (not the seed Act's internal structure),
and that it is genuinely, completely disconnected from the internal
provision-citation network -- before deciding how Katz centrality
should be applied.
"""

import pickle
import networkx as nx
from collections import Counter

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

components = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
giant = components[0]

type_counts = Counter(G.nodes[n].get("node_type") for n in giant)
print(f"Giant component: {len(giant)} nodes")
print(f"Node types: {dict(type_counts)}")

total_external = sum(1 for n, d in G.nodes(data=True) if d.get("node_type") == "external_act")
print(f"\nTotal external_act nodes in whole graph: {total_external}")
print(f"Expected giant component size if it = all external Acts + seed Act: {total_external + 1}")

# Is there truly zero connection between the "internal" world (provisions/
# definitions/containers) and the "external" world (seed_act/external_act)?
internal_types = {"provision", "definition", "section_container", "structural_container"}
external_types = {"seed_act", "external_act"}

cross_edges = 0
for u, v in G.edges():
    u_type = G.nodes[u].get("node_type")
    v_type = G.nodes[v].get("node_type")
    if (u_type in internal_types and v_type in external_types) or (u_type in external_types and v_type in internal_types):
        cross_edges += 1

print(f"\nEdges connecting the internal world to the external world: {cross_edges}")