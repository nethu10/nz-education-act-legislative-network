"""
Merges Stage 6's discovered second-ring connections into the actual
Stage 5 graph object. Enriches the 13 ring-1 external-Act stub nodes
with their real attributes (provision count, date), and adds genuine
second-ring edges and stub nodes for the Acts they connect to --
without this, the graph on disk would not reflect Stage 6 at all.
"""

import json
import pickle
from pathlib import Path

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

print(f"Graph before merge: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

target_summary = json.loads(Path("data/processed/stage6_target_acts_summary.json").read_text())

ring2_nodes_added = 0
ring2_edges_added = 0
ring1_enriched = 0

for act in target_summary:
    ring1_id = f"EXTERNAL::{act['name']}"

    if ring1_id in G:
        G.nodes[ring1_id]["provision_count"] = act["provision_count"]
        G.nodes[ring1_id]["date_as_at"] = act["date_as_at"]
        G.nodes[ring1_id]["expansion_ring"] = 1
        ring1_enriched += 1
    else:
        G.add_node(ring1_id, node_type="external_act", name=act["name"],
                    provision_count=act["provision_count"], date_as_at=act["date_as_at"], expansion_ring=1)

    for target_name in act.get("outgoing_targets", []):
        ring2_id = f"EXTERNAL::{target_name}"
        if ring2_id not in G:
            G.add_node(ring2_id, node_type="external_act", name=target_name, expansion_ring=2)
            ring2_nodes_added += 1
        if not G.has_edge(ring1_id, ring2_id):
            G.add_edge(ring1_id, ring2_id, edge_type="amends", ring=2)
            ring2_edges_added += 1

    for source_name in act.get("incoming_sources", []):
        ring2_id = f"EXTERNAL::{source_name}"
        if ring2_id not in G:
            G.add_node(ring2_id, node_type="external_act", name=source_name, expansion_ring=2)
            ring2_nodes_added += 1
        if not G.has_edge(ring2_id, ring1_id):
            G.add_edge(ring2_id, ring1_id, edge_type="amends", ring=2)
            ring2_edges_added += 1

print(f"\nRing-1 nodes enriched with real attributes: {ring1_enriched}")
print(f"Ring-2 nodes added: {ring2_nodes_added}")
print(f"Ring-2 edges added: {ring2_edges_added}")
print(f"\nGraph after merge: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

with open("data/processed/stage5_graph.pickle", "wb") as f:
    pickle.dump(G, f)
print("\nSaved (overwrote stage5_graph.pickle with the merged, fully-expanded graph)")