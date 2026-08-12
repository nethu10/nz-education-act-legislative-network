"""
For all 46 unresolved hrefs that ARE real <prov> elements, check
whether each one contains <def-para> children -- confirming whether
they're "parent" provisions that got split into definitions (and so
never received their own top-level provisions.json record), or
something else entirely.
"""

from lxml import etree
from pathlib import Path
from collections import Counter
import json

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

unresolved_provs = set()
for p in extractable:
    for href in p.get("internal_refs", []):
        if href not in extractable_ids and href not in all_ids:
            el = by_id.get(href)
            if el is not None and local_name(el.tag) == "prov":
                unresolved_provs.add(href)

print(f"Distinct unresolved <prov> ids: {len(unresolved_provs)}")

has_defparas = 0
no_defparas = 0
no_defpara_examples = []

for href in unresolved_provs:
    el = by_id[href]
    body = el.find("prov.body")
    def_paras = [c for c in body.iter() if local_name(c.tag) == "def-para"] if body is not None else []
    if def_paras:
        has_defparas += 1
    else:
        no_defparas += 1
        heading_el = el.find("heading")
        heading = heading_el.text if heading_el is not None else None
        no_defpara_examples.append((href, heading))

print(f"Has <def-para> children (definition-parent pattern): {has_defparas}")
print(f"No <def-para> children (genuinely different issue): {no_defparas}")
print("\nExamples of the 'no def-para' group, if any:")
for href, heading in no_defpara_examples[:10]:
    print(f"  {href}: heading={heading!r}")