"""
Investigate three surprising entries in the Katz centrality results
before treating them as final: LMS267809's missing heading, what
"Rules" actually contains, and why a tiny 5-provision Act (Public
Bodies Contracts Act 1959) ranks unexpectedly high.
"""

import json
import pickle
from pathlib import Path

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

print("=" * 60)
print("1. LMS267809 -- what is this provision really?")
print("=" * 60)
node = G.nodes.get("LMS267809", {})
print(f"heading: {node.get('heading')!r}")
print(f"term: {node.get('term')!r}")
print(f"section_number: {node.get('section_number')!r}")
print(f"text: {node.get('text', '')[:300]!r}")
print(f"in-degree: {G.in_degree('LMS267809')}, out-degree: {G.out_degree('LMS267809')}")

print("\n" + "=" * 60)
print('2. Find the "Rules" provision(s)')
print("=" * 60)
for n, d in G.nodes(data=True):
    if d.get("heading") == "Rules":
        print(f"\nid={n}")
        print(f"section_number: {d.get('section_number')!r}")
        print(f"text: {d.get('text', '')[:300]!r}")
        print(f"in-degree: {G.in_degree(n)}, out-degree: {G.out_degree(n)}")

print("\n" + "=" * 60)
print("3. Public Bodies Contracts Act 1959 -- who connects to it, and why?")
print("=" * 60)
target_id = "EXTERNAL::Public Bodies Contracts Act 1959 (1959 No 98)"
if target_id in G:
    preds = list(G.predecessors(target_id))
    succs = list(G.successors(target_id))
    print(f"In-degree: {len(preds)}, Out-degree: {len(succs)}")
    print(f"\nWho points TO it (first 10):")
    for p in preds[:10]:
        print(f"  {G.nodes[p].get('name', p)}")
    print(f"\nWho it points TO (first 10):")
    for s in succs[:10]:
        print(f"  {G.nodes[s].get('name', s)}")
else:
    print("Node not found under that exact id -- check naming.")