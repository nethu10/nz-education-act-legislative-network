"""
Stage 7: Katz centrality, computed separately on the two genuinely
disconnected structures identified in the graph -- the amendment
network (seed Act + external Acts) and the internal citation network
(provisions, definitions, containers within the seed Act). Computing
these together would mix two incomparable kinds of centrality into
one meaningless number.
"""

import pickle
import json
import networkx as nx
from pathlib import Path

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

components = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
amendment_network = G.subgraph(components[0]).copy()
internal_network = G.subgraph(components[1]).copy()

print(f"Amendment network: {amendment_network.number_of_nodes()} nodes, {amendment_network.number_of_edges()} edges")
print(f"Internal citation network: {internal_network.number_of_nodes()} nodes, {internal_network.number_of_edges()} edges")


def run_katz(graph, label_fn, top_n=15):
    centrality = nx.katz_centrality(graph, alpha=0.05, max_iter=1000)
    ranked = sorted(centrality.items(), key=lambda x: -x[1])
    print(f"\nTop {top_n} by Katz centrality:")
    results = []
    for node_id, score in ranked[:top_n]:
        label = label_fn(node_id)
        print(f"  {score:.4f}  {label}")
        results.append({"node_id": node_id, "label": label, "katz_centrality": score})
    return results, centrality


print("\n" + "=" * 60)
print("AMENDMENT NETWORK")
print("=" * 60)
amendment_results, amendment_full = run_katz(
    amendment_network,
    lambda n: G.nodes[n].get("name", n)
)

print("\n" + "=" * 60)
print("INTERNAL CITATION NETWORK")
print("=" * 60)
internal_results, internal_full = run_katz(
    internal_network,
    lambda n: f"{G.nodes[n].get('heading') or G.nodes[n].get('term') or n} [{G.nodes[n].get('node_type')}]"
)

Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/processed/stage7_katz_amendment_network.json").write_text(
    json.dumps(amendment_results, indent=2, ensure_ascii=False), encoding="utf-8"
)
Path("data/processed/stage7_katz_internal_network.json").write_text(
    json.dumps(internal_results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("\nSaved both ranked result sets to data/processed/")