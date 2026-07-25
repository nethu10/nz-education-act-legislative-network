"""
Diagnostic: categorize ALL <def-para> elements Stage 2 did not capture,
not just a sample, to confirm none are being silently dropped from the
Act's own body text.
"""

import json
from pathlib import Path
from lxml import etree

RAW_PATH = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(RAW_PATH))
root = tree.getroot()


def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag


all_def_paras = {
    el.get("id"): el for el in root.iter()
    if local_name(el.tag) == "def-para" and el.get("id")
}

captured = json.loads(Path("data/processed/provisions.json").read_text())
captured_ids = {r["id"] for r in captured if r["type"] == "definition"}

missing_ids = set(all_def_paras) - captured_ids
print(f"Total missing: {len(missing_ids)}")

in_schedule = []
not_in_schedule = []

for missing_id in missing_ids:
    el = all_def_paras[missing_id]
    ancestors = []
    parent = el.getparent()
    while parent is not None:
        ancestors.append(local_name(parent.tag))
        parent = parent.getparent()

    if "schedule" in ancestors:
        in_schedule.append(missing_id)
    else:
        not_in_schedule.append((missing_id, ancestors[:6], " ".join(el.itertext())[:150]))

print(f"In Schedule of Amendments (expected, correctly excluded): {len(in_schedule)}")
print(f"NOT in a schedule (needs investigation): {len(not_in_schedule)}")

for mid, ancestors, text in not_in_schedule:
    print(f"\n{mid}")
    print("  Ancestor chain:", ancestors)
    print("  Text:", text)