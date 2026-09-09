"""
Quick check on the second-largest component (906 nodes) before deciding
to exclude it -- confirming what it actually is, since its size is
close enough to the giant component to be worth understanding rather
than assuming it's unimportant.
"""

import pickle
import networkx as nx
from collections import Counter

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

components = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
second = components[1]

type_counts = Counter(G.nodes[n].get("node_type") for n in second)
print(f"Second-largest component: {len(second)} nodes")
print(f"Node types: {dict(type_counts)}")

# If it contains external_act nodes, show which ones, to identify the source
external_names = [G.nodes[n].get("name") for n in second if G.nodes[n].get("node_type") == "external_act"]
print(f"\nExternal Act names present ({len(external_names)}):")
for name in external_names[:10]:
    print(f"  {name}")