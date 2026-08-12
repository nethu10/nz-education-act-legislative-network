"""
Full classification of ALL 194 unresolved internal_refs (not just a
10-item sample), plus investigation of why any real <prov> elements
were missed by Stage 2's extraction -- needed before deciding how
Stage 5 should handle Part/Schedule-level references in the graph.
"""

import json
from lxml import etree
from pathlib import Path
from collections import Counter

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

provisions = json.loads(Path("data/processed/provisions.json").read_text())
extractable = [p for p in provisions if not p.get("is_repealed_or_empty")]
extractable_ids = {p["id"] for p in extractable}
all_ids = {p["id"] for p in provisions}

by_id = {}
for el in root.iter():
    el_id = el.get("id")
    if el_id:
        by_id[el_id] = el

# Collect every unresolved href across the whole dataset (not just 10)
unresolved = []
for p in extractable:
    for href in p.get("internal_refs", []):
        if href not in extractable_ids and href not in all_ids:
            unresolved.append(href)

print(f"Total unresolved hrefs: {len(unresolved)}")

tag_counter = Counter()
mystery_provs = []
for href in unresolved:
    el = by_id.get(href)
    if el is None:
        tag_counter["not_found_in_xml_at_all"] += 1
        continue
    tag = local_name(el.tag)
    tag_counter[tag] += 1
    if tag == "prov":
        has_body = el.find("prov.body") is not None
        mystery_provs.append((href, has_body))

print("\nFull tag type breakdown:")
for tag, count in tag_counter.most_common():
    print(f"  {tag}: {count}")

print(f"\n<prov> elements among unresolved refs: {len(mystery_provs)}")
for href, has_body in mystery_provs[:10]:
    print(f"  {href}: has <prov.body>? {has_body}")
    if not has_body:
        el = by_id[href]
        print("   ", etree.tostring(el, pretty_print=True, encoding="unicode")[:400])