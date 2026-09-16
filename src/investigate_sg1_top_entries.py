"""
Investigates the top of the combined ranking before trusting it:
confirms which entries are self-referential amendment instruments to
the seed Act itself (not genuine external connections), and checks
what's actually driving the Secondary Legislation Act 2021's high score.
"""

import json
import re
from pathlib import Path

ranking = json.loads(Path("data/processed/sg1_combined_ranking.json").read_text())

print("=== Checking for self-referential 'Education and Training ... Amendment Act' entries ===")
self_amendment_pattern = re.compile(r"Education and Training.*Amendment Act|Education \(Name Change", re.IGNORECASE)
self_refs = [r for r in ranking if self_amendment_pattern.search(r["act"])]
for r in self_refs:
    print(f"  {r['combined_score']:4d}  {r['act']}")
print(f"\nTotal self-referential entries found: {len(self_refs)}")
print(f"Combined score these account for: {sum(r['combined_score'] for r in self_refs)}")

print("\n=== Checking what's driving Secondary Legislation Act 2021's score ===")
incoming = json.loads(Path("data/processed/amendment_relationships_typed.json").read_text())
sla = [r for r in incoming if "secondary legislation act" in r["act"].lower()]
for r in sla:
    print(f"  {r}")

# Look at a few real examples from the raw incoming records to see the actual wording
raw_incoming = json.loads(Path("data/processed/amendment_records.json").read_text())
sla_raw = [r for r in raw_incoming if r.get("amending_act") and "secondary legislation act" in r["amending_act"].lower()]
print(f"\nSample of raw incoming records citing Secondary Legislation Act 2021 ({len(sla_raw)} total):")
for r in sla_raw[:5]:
    print(f"  {r}")