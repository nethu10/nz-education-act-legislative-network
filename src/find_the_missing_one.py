"""
69 of the 70 empty-text provisions were confirmed as repealed <prov>
elements. One ID from the original list didn't get matched by that
check at all — find out which, and why, before finalizing the fix.
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
empty_records = [p for p in provisions if len(p.get("text", "").strip()) < 20]
empty_ids = {p["id"] for p in empty_records}

matched_ids = {
    el.get("id") for el in root.iter()
    if local_name(el.tag) == "prov" and el.get("id") in empty_ids
}

missing = empty_ids - matched_ids
print(f"Empty-text records: {len(empty_ids)}")
print(f"Matched as <prov> elements: {len(matched_ids)}")
print(f"Unmatched: {missing}")

for mid in missing:
    record = next(p for p in empty_records if p["id"] == mid)
    print("\nFull provisions.json record:")
    print(json.dumps(record, indent=2, ensure_ascii=False))

    # Search the raw XML for this id under ANY tag, not just <prov>
    for el in root.iter():
        if el.get("id") == mid:
            print("\nFound in raw XML under tag:", local_name(el.tag))
            print(etree.tostring(el, pretty_print=True, encoding="unicode")[:1500])
            break
    else:
        print("\nNot found in raw XML by this id at all.")