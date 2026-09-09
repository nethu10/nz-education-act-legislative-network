"""
Check whether the graph's 671 components are mostly tiny Stage-6
satellite pairs (as hypothesized) versus something else, and confirm
whether the seed Act's own core structure sits entirely within the
single largest component.
"""

import pickle
import networkx as nx
from collections import Counter

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

components = list(nx.weakly_connected_components(G))
sizes = [len(c) for c in components]
size_counts = Counter(sizes)

print("Component size distribution:")
for size in sorted(size_counts.keys(), reverse=True)[:15]:
    print(f"  size {size}: {size_counts[size]} component(s)")
print(f"  ... total {len(components)} components")

tiny = sum(1 for s in sizes if s <= 3)
print(f"\nComponents of size <= 3 nodes: {tiny} ({100*tiny/len(components):.1f}% of all components)")

# Confirm the seed Act and its direct structure sit in the giant component
components.sort(key=len, reverse=True)
giant = components[0]
seed_in_giant = "SEED_ACT" in giant
print(f"\nSeed Act in the largest component: {seed_in_giant}")

# Sample a few small components to see what they actually contain
print("\nSample small components (size 2-3):")
shown = 0
for c in components:
    if 2 <= len(c) <= 3 and shown < 5:
        node_info = [(n, G.nodes[n].get("node_type"), G.nodes[n].get("name", n)) for n in c]
        print(f"  {node_info}")
        shown += 1