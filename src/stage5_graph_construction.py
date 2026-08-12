"""
Stage 5: Attributed graph construction.

Builds a directed, typed graph from validated Stage 2-4 data. Structural
edges come from government-tagged internal_refs (now fully resolved
across direct hits, section-container hits, and structural-container
hits). Semantic attributes (entities, relations, summary, topic_tags)
are attached directly onto provision/definition nodes. Amendment edges
connect confirmed external Acts to the seed Act node.
"""

import json
import pickle
import networkx as nx
from pathlib import Path
from lxml import etree
from collections import Counter

provisions = json.loads(Path("data/processed/provisions.json").read_text())
extractions = {e["provision_id"]: e["extraction"] for e in json.loads(Path("data/processed/extractions_full.json").read_text())}
outgoing = json.loads(Path("data/processed/outgoing_amendments.json").read_text())
incoming = json.loads(Path("data/processed/amendment_records.json").read_text())

extractable = [p for p in provisions if not p.get("is_repealed_or_empty")]
extractable_ids = {p["id"] for p in extractable}
all_provision_ids = {p["id"] for p in provisions}

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

by_id = {}
for el in root.iter():
    el_id = el.get("id")
    if el_id:
        by_id[el_id] = el

def get_label_heading(el):
    label_el = el.find("label")
    heading_el = el.find("heading")
    return (label_el.text if label_el is not None else None,
            heading_el.text if heading_el is not None else None)

G = nx.DiGraph()
SEED_ACT_ID = "SEED_ACT"
G.add_node(SEED_ACT_ID, node_type="seed_act", name="Education and Training Act 2020")

for p in extractable:
    extraction = extractions.get(p["id"], {})
    G.add_node(
        p["id"],
        node_type=p["type"],
        heading=p.get("heading"),
        section_number=p.get("section_number"),
        term=p.get("term"),
        text=p.get("text"),
        entities=extraction.get("entities", []),
        relations=extraction.get("relations", []),
        summary=extraction.get("summary"),
        topic_tags=extraction.get("topic_tags", []),
    )

print(f"Added {len(extractable)} provision/definition nodes.")

edge_count = 0
container_nodes_added = set()
resolution_counts = Counter()

for p in extractable:
    source_id = p["id"]
    for href in p.get("internal_refs", []):
        if href in extractable_ids:
            G.add_edge(source_id, href, edge_type="references")
            resolution_counts["direct"] += 1
            edge_count += 1
        elif href in all_provision_ids:
            resolution_counts["skipped_repealed_target"] += 1
        else:
            el = by_id.get(href)
            if el is None:
                resolution_counts["truly_unresolved"] += 1
                continue
            tag = local_name(el.tag)
            if tag == "prov":
                if href not in container_nodes_added:
                    label, heading = get_label_heading(el)
                    G.add_node(href, node_type="section_container", section_number=label, heading=heading)
                    container_nodes_added.add(href)
                G.add_edge(source_id, href, edge_type="references")
                resolution_counts["section_container"] += 1
                edge_count += 1
            elif tag in ("part", "subpart", "schedule"):
                if href not in container_nodes_added:
                    label, heading = get_label_heading(el)
                    G.add_node(href, node_type="structural_container", container_type=tag, section_number=label, heading=heading)
                    container_nodes_added.add(href)
                G.add_edge(source_id, href, edge_type="references")
                resolution_counts[f"structural_{tag}"] += 1
                edge_count += 1
            else:
                resolution_counts[f"other_{tag}"] += 1

print(f"\nInternal reference edges added: {edge_count}")
print(f"Container nodes added: {len(container_nodes_added)}")
print("Resolution breakdown:", dict(resolution_counts))

outgoing_targets = sorted(set(r["target_act"] for r in outgoing if r["target_act"]))
for act_name in outgoing_targets:
    node_id = f"EXTERNAL::{act_name}"
    G.add_node(node_id, node_type="external_act", name=act_name)
    G.add_edge(SEED_ACT_ID, node_id, edge_type="amends")

incoming_sources = sorted(set(r["amending_act"] for r in incoming if r["amending_act"]))
for act_name in incoming_sources:
    node_id = f"EXTERNAL::{act_name}"
    if node_id not in G:
        G.add_node(node_id, node_type="external_act", name=act_name)
    G.add_edge(node_id, SEED_ACT_ID, edge_type="amends")

print(f"\nExternal Act nodes (outgoing targets): {len(outgoing_targets)}")
print(f"External Act nodes (incoming sources): {len(incoming_sources)}")

print("\n" + "=" * 60)
print("GRAPH SUMMARY")
print("=" * 60)
print(f"Total nodes: {G.number_of_nodes()}")
print(f"Total edges: {G.number_of_edges()}")

node_type_counts = Counter(d.get("node_type") for _, d in G.nodes(data=True))
print("\nNodes by type:")
for t, c in node_type_counts.most_common():
    print(f"  {t}: {c}")

edge_type_counts = Counter(d.get("edge_type") for _, _, d in G.edges(data=True))
print("\nEdges by type:")
for t, c in edge_type_counts.most_common():
    print(f"  {t}: {c}")

out_dir = Path("data/processed")
with open(out_dir / "stage5_graph.pickle", "wb") as f:
    pickle.dump(G, f)

graph_json = nx.node_link_data(G)
(out_dir / "stage5_graph.json").write_text(json.dumps(graph_json, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"\nSaved to {out_dir / 'stage5_graph.pickle'} (full-fidelity, for Python analysis)")
print(f"Saved to {out_dir / 'stage5_graph.json'} (inspectable JSON)")