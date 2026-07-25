"""
Look at the full raw structure around a definition missed by Stage 2
that is NOT inside the Schedule of Amendments, to see exactly why
extract_provisions() isn't catching it.
"""

from lxml import etree
from pathlib import Path

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

target_id = "LMS1633706"  # update this to whatever the fresh diagnostic shows

for el in root.iter():
    if el.get("id") == target_id:
        # Walk up to the nearest enclosing <prov> and print the whole thing
        ancestor = el
        while ancestor is not None and ancestor.tag.split("}")[-1] != "prov":
            ancestor = ancestor.getparent()
        if ancestor is not None:
            print(etree.tostring(ancestor, pretty_print=True, encoding="unicode")[:3000])
        break