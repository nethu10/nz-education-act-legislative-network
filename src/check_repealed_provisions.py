"""
Confirm how many of the 70 empty-text provisions are formally repealed
(deletion-status="repealed") versus something else, before deciding
on a fix.
"""

from lxml import etree
from pathlib import Path
import json

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

provisions = json.loads(Path("data/processed/provisions.json").read_text())
empty_ids = {p["id"] for p in provisions if len(p.get("text", "").strip()) < 20}

repealed_count = 0
other_count = 0
other_examples = []

for el in root.iter():
    if local_name(el.tag) == "prov" and el.get("id") in empty_ids:
        status = el.get("deletion-status")
        if status == "repealed":
            repealed_count += 1
        else:
            other_count += 1
            if len(other_examples) < 5:
                other_examples.append((el.get("id"), status))

print(f"Empty-text provisions confirmed as deletion-status='repealed': {repealed_count}")
print(f"Empty-text provisions with some OTHER status: {other_count}")
print(f"Examples of 'other': {other_examples}")