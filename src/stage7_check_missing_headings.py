"""
Check how many provisions have a missing heading (like LMS267809),
since this affects readability of ranked results wherever it occurs,
not just this one case.
"""
import pickle

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

missing = [(n, d.get("section_number"), d.get("text", "")[:60]) 
           for n, d in G.nodes(data=True) 
           if d.get("node_type") in ("provision", "definition") and not d.get("heading") and not d.get("term")]

print(f"Provisions/definitions with no heading and no term: {len(missing)}")
for n, sec, text in missing[:15]:
    print(f"  {n} (s.{sec}): {text}")