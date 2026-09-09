"""
Patches the heading attribute on existing graph nodes using the
corrected provisions.json, without rebuilding the graph's structure
(edges, IDs, and text were never affected by this bug).
"""
import json
import pickle
from pathlib import Path

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

provisions = json.loads(Path("data/processed/provisions.json").read_text())
updated = 0
for p in provisions:
    if p["id"] in G.nodes:
        if G.nodes[p["id"]].get("heading") != p["heading"]:
            G.nodes[p["id"]]["heading"] = p["heading"]
            updated += 1

print(f"Updated headings on {updated} existing graph nodes")
with open("data/processed/stage5_graph.pickle", "wb") as f:
    pickle.dump(G, f)
print("Saved.")