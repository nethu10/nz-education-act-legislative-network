"""
Look up what XML element type each unresolved href actually points to
-- e.g. a <subprov>, <part>, <schedule>, or something else not captured
as its own top-level provisions.json record -- before deciding how to
handle these in the graph's edge construction.
"""

from lxml import etree
from pathlib import Path
from collections import Counter

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

unresolved_hrefs = [
    "LMS262217", "LMS288380", "LMS274508", "LMS176159",
    "LMS171315", "LMS171362", "LMS171878", "LMS202503", "LMS172492", "LMS172574",
]

# Index every element in the document by its id attribute
by_id = {}
for el in root.iter():
    el_id = el.get("id")
    if el_id:
        by_id[el_id] = el

tag_counter = Counter()
for href in unresolved_hrefs:
    el = by_id.get(href)
    if el is None:
        print(f"{href}: NOT FOUND anywhere in the XML by this id")
        tag_counter["not_found"] += 1
        continue
    tag = local_name(el.tag)
    tag_counter[tag] += 1
    # Find nearest ancestor <prov> to see what top-level provision this belongs to
    parent = el.getparent()
    nearest_prov_id = None
    while parent is not None:
        if local_name(parent.tag) == "prov":
            nearest_prov_id = parent.get("id")
            break
        parent = parent.getparent()
    print(f"{href}: tag=<{tag}>, nearest enclosing <prov> id={nearest_prov_id}")

print("\nTag type summary:", dict(tag_counter))
