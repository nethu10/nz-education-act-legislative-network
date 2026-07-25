"""
Look at how the Interpretation section (many definitions) is actually
nested, so Stage 2 can segment at the right level instead of flattening
an entire definitions list into one blob.
"""

from lxml import etree
from pathlib import Path

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()


def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag


# Find the "Interpretation" provision specifically (section 10)
for prov in root.iter():
    if local_name(prov.tag) != "prov":
        continue
    heading = prov.find("heading")
    if heading is not None and heading.text == "Interpretation":
        xml_str = etree.tostring(prov, pretty_print=True, encoding="unicode")
        print(xml_str[:3000])
        print("...\n[truncated]")
        break