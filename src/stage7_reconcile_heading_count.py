"""
Reconciles the 206 originally-found heading mismatches against exactly
what happened to each one: still exists as a provisions.json record?
Flagged repealed/empty? Present as a graph node? Did its heading
actually change? -- rather than accepting 49 without knowing why it's
not 206.
"""

import json
import pickle
from lxml import etree
from pathlib import Path

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def full_text(el):
    import re
    raw = " ".join(el.itertext())
    return re.sub(r"\s+", " ", raw).strip()

# Rebuild the original 206 mismatch IDs directly from the XML, same logic as before
xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

mismatch_ids = []
for el in root.iter():
    if local_name(el.tag) != "heading":
        continue
    naive = (el.text or "").strip()
    full = full_text(el)
    if naive != full:
        mismatch_ids.append(el.getparent().get("id"))

print(f"Original mismatch count: {len(mismatch_ids)}")

provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}

with open("data/processed/stage5_graph.pickle", "rb") as f:
    G = pickle.load(f)

not_a_record = 0     # id never appears in provisions.json at all (a def-para parent)
repealed_excluded = 0  # exists, but flagged repealed/empty, never entered the graph
in_graph = 0          # exists as a real graph node

for mid in mismatch_ids:
    if mid not in provisions:
        not_a_record += 1
    elif provisions[mid].get("is_repealed_or_empty"):
        repealed_excluded += 1
    elif mid in G.nodes:
        in_graph += 1
    else:
        print(f"  UNEXPLAINED: {mid}")

print(f"\nNever became their own record (def-para parent, absorbed into definitions): {not_a_record}")
print(f"Exists but flagged repealed/empty (correctly excluded from graph): {repealed_excluded}")
print(f"Exists as a real graph node (should match the 49 patched): {in_graph}")