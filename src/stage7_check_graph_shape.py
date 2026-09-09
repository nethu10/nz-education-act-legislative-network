"""
Stage 7, pre-check: confirm edge direction semantics with real examples,
and check basic connectivity/degree properties, before deciding how
Katz centrality should be applied to a graph that mixes provision-level
and Act-level nodes.
"""

import pickle
import networkx as nx
from collections import Counter

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
print(f"Is directed: {G.is_directed()}")

# Show 3 real "references" edges and 3 real "amends" edges, with node types,
# to confirm direction semantics concretely rather than assuming
print("\n--- Sample 'references' edges (source -> target, with node types) ---")
count = 0
for u, v, d in G.edges(data=True):
    if d.get("edge_type") == "references" and count < 3:
        print(f"  {G.nodes[u].get('node_type')} '{u}' --references--> {G.nodes[v].get('node_type')} '{v}'")
        count += 1

print("\n--- Sample 'amends' edges (source -> target, with node types) ---")
count = 0
for u, v, d in G.edges(data=True):
    if d.get("edge_type") == "amends" and count < 3:
        u_name = G.nodes[u].get("name", u)
        v_name = G.nodes[v].get("name", v)
        print(f"  {G.nodes[u].get('node_type')} '{u_name}' --amends--> {G.nodes[v].get('node_type')} '{v_name}'")
        count += 1

# Connectivity: how many weakly-connected components, and how big is the largest?
components = list(nx.weakly_connected_components(G))
components.sort(key=len, reverse=True)
print(f"\nWeakly connected components: {len(components)}")
print(f"Largest component size: {len(components[0])} nodes ({100*len(components[0])/G.number_of_nodes():.1f}% of graph)")
if len(components) > 1:
    print(f"Second largest: {len(components[1])} nodes")

# Degree distribution by node type -- do provisions and external Acts have
# wildly different typical degree, which would make combined centrality hard to interpret?
in_degrees_by_type = {}
for n, d in G.nodes(data=True):
    t = d.get("node_type")
    in_degrees_by_type.setdefault(t, []).append(G.in_degree(n))

print("\nAverage in-degree by node type:")
for t, degs in in_degrees_by_type.items():
    print(f"  {t}: avg={sum(degs)/len(degs):.2f}, max={max(degs)}, n={len(degs)}")