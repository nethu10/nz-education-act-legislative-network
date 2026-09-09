"""
Corrected diagnostic: confirm whether small/isolated components are
(a) dominated by seed-Act-internal nodes with genuinely zero references
in either direction, versus (b) any real involvement from Stage 6's
external_act nodes -- since the sample output showed internal IDs,
not EXTERNAL:: nodes, contradicting the original Stage-6 hypothesis.
"""

import pickle
import networkx as nx
from collections import Counter

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

components = list(nx.weakly_connected_components(G))
small = [c for c in components if len(c) <= 3]

# How many of the 656 small components contain an external_act node at all?
contains_external = sum(1 for c in small if any(G.nodes[n].get("node_type") == "external_act" for n in c))
print(f"Small components (size <=3): {len(small)}")
print(f"  ...containing at least one external_act node: {contains_external}")
print(f"  ...purely internal (seed-Act) nodes only: {len(small) - contains_external}")

# For isolated singletons specifically: confirm zero in AND out degree
singletons = [c for c in components if len(c) == 1]
zero_both = sum(1 for c in singletons if G.in_degree(next(iter(c))) == 0 and G.out_degree(next(iter(c))) == 0)
print(f"\nIsolated singleton nodes: {len(singletons)}")
print(f"  ...confirmed zero in-degree AND zero out-degree: {zero_both}")

# Node-type breakdown of singletons
singleton_types = Counter(G.nodes[next(iter(c))].get("node_type") for c in singletons)
print(f"\nSingleton node types: {dict(singleton_types)}")

# Sample 5 singleton definitions with their actual text, to confirm they
# are genuinely simple, non-citing, non-cited entries
print("\nSample singleton definitions:")
shown = 0
for c in singletons:
    n = next(iter(c))
    if G.nodes[n].get("node_type") == "definition" and shown < 5:
        print(f"  {n}: term={G.nodes[n].get('term')!r}, text={G.nodes[n].get('text', '')[:80]!r}")
        shown += 1