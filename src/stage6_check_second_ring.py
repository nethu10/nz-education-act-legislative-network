"""
Two checks before deciding how to handle the second ring: (1) confirm
the 7 zero-outgoing Acts genuinely have no <schedule.amendments.group2>
section rather than a parsing miss, and (2) how much of the 546
second-ring Acts overlap with the original 193 from Stage 2.
"""

from lxml import etree
from pathlib import Path
import json

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

zero_outgoing_files = [
    ("1975_114", "Treaty of Waitangi Act 1975"),
    ("1961_52", "Lincoln University Act 1961"),
    ("1963_7", "Massey University Act 1963"),
    ("1961_50", "University of Auckland Act 1961"),
    ("1961_49", "University of Canterbury Act 1961"),
    ("1963_8", "University of Waikato Act 1963"),
    ("1961_51", "Victoria University of Wellington Act 1961"),
]

print("Checking for <schedule.amendments.group2> presence:")
for file_stub, name in zero_outgoing_files:
    xml_path = Path(f"data/raw/stage6_targets/{file_stub}.xml")
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    has_schedule_group2 = any(local_name(el.tag) == "schedule.amendments.group2" for el in root.iter())
    has_any_schedule = any(local_name(el.tag) == "schedule" for el in root.iter())
    print(f"  {name}: has group2={has_schedule_group2}, has any schedule={has_any_schedule}")

# Overlap check
outgoing_original = json.loads(Path("data/processed/outgoing_amendments.json").read_text())
original_193 = set(r["target_act"] for r in outgoing_original if r["target_act"])

target_summary = json.loads(Path("data/processed/stage6_target_acts_summary.json").read_text())
second_ring = set()
for r in target_summary:
    second_ring.update(r["outgoing_targets"])

overlap = second_ring & original_193
new_only = second_ring - original_193

print(f"\nOriginal 193 (Stage 2): {len(original_193)}")
print(f"Second-ring discovered (Stage 6): {len(second_ring)}")
print(f"Overlap (already known from Stage 2): {len(overlap)}")
print(f"Genuinely new Acts: {len(new_only)}")
print(f"\nSample of genuinely new Acts:")
for name in sorted(new_only)[:15]:
    print(f"  {name}")