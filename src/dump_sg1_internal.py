import json

edges = json.load(open("outputs/graph/edges.json"))
sg1_internal = [e for e in edges if e["layer"] == "SG1" and e["edge_type"] == "internal_link"]

with open("sg1_internal_edges_dump.txt", "w") as f:
    for e in sorted(sg1_internal, key=lambda e: (e["source"], e["target"])):
        f.write(f"{e['source']!r} -> {e['target']!r}  (weight={e['weight']})\n")

print(f"Wrote {len(sg1_internal)} rows to sg1_internal_edges_dump.txt")