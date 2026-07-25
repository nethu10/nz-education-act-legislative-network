"""
Look at the full structure around a Schedule-of-Amendments <def-para>,
to find where the target Act's name is recorded, before writing
extraction logic for outgoing amendments (this Act amending others).
"""

from lxml import etree
from pathlib import Path

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()


def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag


# Find the specific def-para we already identified as "missing", then
# walk up to its schedule.amendments.group1 ancestor and print that
# whole block, so we can see any heading/title naming the target Act.
target_id = "LMS322518"  # "integrated school has the same meaning as..."

for el in root.iter():
    if el.get("id") == target_id:
        ancestor = el
        while ancestor is not None and local_name(ancestor.tag) != "schedule.amendments.group1":
            ancestor = ancestor.getparent()
        if ancestor is not None:
            xml_str = etree.tostring(ancestor, pretty_print=True, encoding="unicode")
            print(xml_str[:2500])
        break