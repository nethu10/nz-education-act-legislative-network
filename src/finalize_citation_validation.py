"""
Final cleaning pass: excludes internal section-reference mistakes
(rules/regulations made under THIS Act's own sections), recovers the
genuinely valid no-year cases, and splits compound entries (two Act
names joined by "and") into their real, separate distinct Acts.
"""

import json
import re
from pathlib import Path

results = json.loads(Path("data/processed/citation_relationships_validated.json").read_text())
all_results = json.loads(Path("data/processed/citation_relationships_slm.json").read_text())

INTERNAL_REF_IDS = {"LMS202444", "LMS262287", "LMS172210"}  # confirmed internal, not external
RECOVER_IDS = {"LMS172553", "LMS894538", "LMS1538273", "LMS1538300"}  # confirmed genuinely valid, just no year

recovered = [r for r in all_results if r["provision_id"] in RECOVER_IDS]
final_records = [r for r in results if r["provision_id"] not in INTERNAL_REF_IDS] + recovered

def split_compound(name):
    name = re.sub(r"^(the|and)\s+", "", name.strip(), flags=re.IGNORECASE)
    parts = re.split(r"\s+and\s+", name)
    cleaned = []
    for p in parts:
        p = p.strip()
        if p and not re.match(r"^(the|and)$", p, re.IGNORECASE):
            cleaned.append(p)
    return cleaned if len(cleaned) > 1 else [name]

distinct_acts = set()
for r in final_records:
    for part in split_compound(r["act_name"]):
        distinct_acts.add(part)

print(f"Final validated citation relationships: {len(final_records)}")
print(f"  (excluded {len(INTERNAL_REF_IDS)} internal section-reference mistakes)")
print(f"  (recovered {len(RECOVER_IDS)} genuinely valid no-year cases)")
print(f"\nFinal distinct external Acts/Regulations (compound entries split): {len(distinct_acts)}")
for name in sorted(distinct_acts):
    print(f"  {name}")

Path("data/processed/citation_relationships_final.json").write_text(
    json.dumps(final_records, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved to data/processed/citation_relationships_final.json")