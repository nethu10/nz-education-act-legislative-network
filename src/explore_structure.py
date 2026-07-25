"""
Look at the real nested structure of one provision and one amendment
record, so Stage 2 and Stage 4 are built on how the XML is actually
assembled, not just which tags exist.
"""

from lxml import etree
from pathlib import Path

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()


def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def first_with_tag(tag_name):
    for el in root.iter():
        if local_name(el.tag) == tag_name:
            return el
    return None


def show(tag_name, max_chars=2500):
    el = first_with_tag(tag_name)
    print("=" * 60)
    print(f"FIRST <{tag_name}>")
    print("=" * 60)
    if el is None:
        print(f"No <{tag_name}> found.")
    else:
        xml_str = etree.tostring(el, pretty_print=True, encoding="unicode")
        print(xml_str[:max_chars])
    print()


show("prov")
show("amending-leg", 1500)
show("history-note", 1500)
show("citation", 500)