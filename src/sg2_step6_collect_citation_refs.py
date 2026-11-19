"""
sg2_step6_collect_citation_refs.py

Collects all extref (cross-Act citation) hrefs across the 35 SG1 source
Acts, excluding the two confirmed hub Acts (Income Tax Act 2007, Tax
Administration Act 1994) on the same hub-dominance grounds already
established for amendment relationships.

Reuses the extract_refs() logic from the Stage 2 segmentation script,
applied directly to each target Act's raw XML (no need for a full
provisions.json per Act -- extref hrefs live at the element level
regardless of how provisions are segmented).

Outputs:
  - data/processed/sg2_citation_refs_by_source.json  -- {source_act: [ids]}
  - data/processed/sg2_unique_citation_ids.json       -- unique ids + frequency,
                                                          most-referenced first
"""
import json
import re
from pathlib import Path
from collections import Counter
from lxml import etree

TARGETS_DIR = Path("data/raw/sg2_targets")
SG1_PATH = Path("data/processed/sg1_final_list.json")
OUT_BY_SOURCE = Path("data/processed/sg2_citation_refs_by_source.json")
OUT_UNIQUE = Path("data/processed/sg2_unique_citation_ids.json")

HUB_ACTS_EXCLUDED = {
    "Income Tax Act 2007",
    "Tax Administration Act 1994",
}

def local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag

def extract_refs(el, tag_name):
    return [
        child.get("href") for child in el.iter()
        if local_name(child.tag) == tag_name and child.get("href")
    ]

with open(SG1_PATH) as f:
    sg1_acts = json.load(f)

def build_act_lookup():
    lookup = {}
    for a in sg1_acts:
        cite = a.get("cite", "")
        m = re.match(r"(\d{4})\s+No\s+(\d+)", cite) or re.match(r"(?:SR|LI)\s+(\d{4})/(\d+)", cite)
        if m:
            year, number = m.groups()
            lookup[(year, number)] = a["act"]
    return lookup

lookup = build_act_lookup()

refs_by_source = {}
all_ids = Counter()

xml_files = sorted(TARGETS_DIR.glob("*.xml"))
print(f"Found {len(xml_files)} target XML files")

for xml_path in xml_files:
    m = re.search(r"_(\d{4})_(\d+)\.xml$", xml_path.name)
    if not m:
        print(f"  skip (unrecognized filename): {xml_path.name}")
        continue
    year, number = m.groups()
    source_act = lookup.get((year, number), xml_path.stem)

    if source_act in HUB_ACTS_EXCLUDED:
        print(f"  skipping hub Act: {source_act}")
        continue

    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    ext_ids = extract_refs(root, "extref")

    refs_by_source[source_act] = ext_ids
    all_ids.update(ext_ids)
    print(f"  {source_act}: {len(ext_ids)} extref hrefs ({len(set(ext_ids))} unique)")

print()
print(f"Total source Acts processed: {len(refs_by_source)}")
print(f"Total extref occurrences: {sum(all_ids.values())}")
print(f"Total UNIQUE extref ids: {len(all_ids)}")
print()
print("Top 20 most-referenced ids:")
for id_, count in all_ids.most_common(20):
    print(f"  {id_}: referenced {count} times")

with open(OUT_BY_SOURCE, "w") as f:
    json.dump(refs_by_source, f, indent=2)
with open(OUT_UNIQUE, "w") as f:
    json.dump([{"id": id_, "count": count} for id_, count in all_ids.most_common()], f, indent=2)

print(f"\nSaved -> {OUT_BY_SOURCE}")
print(f"Saved -> {OUT_UNIQUE}")