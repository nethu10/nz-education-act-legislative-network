"""
sg2_diagnose_step12_coverage.py

One-off check: sg2_step12 found 459 XML files where 436 (SG2) + 37 (SG1)
= 473 were expected, and only scanned 421 as SG2 sources. This pinpoints
exactly which of the 436 fetchable SG2 Acts have no cached XML in
data/raw/sg2_targets/, so we know precisely what the citation pool is
missing before merging it with the amendment-side pool.
"""
import json
import re
from pathlib import Path

TARGETS_DIR = Path("data/raw/sg2_targets")
IDENTIFIERS_PATH = Path("data/processed/sg2_act_identifiers.json")

with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

fetchable = [d for d in identifiers if d.get("resolved") and d.get("xml_url")]
expected = {(str(d["year"]), str(d["number"])): d["act"] for d in fetchable}
print(f"Expected fetchable SG2 Acts: {len(expected)}")

found_ids = set()
for xml_path in sorted(TARGETS_DIR.glob("*.xml")):
    m = re.search(r"_?(~?\d{4})_(~?\d+)\.xml$", xml_path.name)
    if m:
        found_ids.add(m.groups())

print(f"Total XML files in folder: {len(list(TARGETS_DIR.glob('*.xml')))}")
print(f"Distinct (year, number) identifiers found in folder: {len(found_ids)}")

missing = [(yr, no, name) for (yr, no), name in expected.items() if (yr, no) not in found_ids]
print(f"\nSG2 Acts with NO cached XML file at all: {len(missing)}")
for yr, no, name in missing:
    print(f"  {yr}/{no}  {name}")

extra = found_ids - set(expected.keys())
print(f"\n(year, number) identifiers present in the folder but NOT a fetchable SG2 Act "
      f"(expected: these should mostly be the 37 SG1 Acts): {len(extra)}")
for yr, no in sorted(extra):
    print(f"  {yr}/{no}")