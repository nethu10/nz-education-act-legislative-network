"""
Corrected final pass: abandons blind 'and'-splitting (which incorrectly
broke apart real Act names that legitimately contain "and" in their own
title, e.g. "Estate and Gift Duties Act"). Only the confirmed, genuine
two-Act compounds are manually split; everything else is kept as
originally extracted.
"""

import json
from pathlib import Path

results = json.loads(Path("data/processed/citation_relationships_validated.json").read_text())
all_results = json.loads(Path("data/processed/citation_relationships_slm.json").read_text())

INTERNAL_REF_IDS = {"LMS202444", "LMS262287", "LMS172210"}
RECOVER_IDS = {"LMS172553", "LMS894538", "LMS1538273", "LMS1538300"}

recovered = [r for r in all_results if r["provision_id"] in RECOVER_IDS]
final_records = [r for r in results if r["provision_id"] not in INTERNAL_REF_IDS] + recovered

# Manually verified: these are the ONLY entries that are genuinely two
# separate Acts joined by "and" -- confirmed by inspection, not a blind rule
CONFIRMED_COMPOUNDS = {
    "the Cadastral Survey Act 2002 and the Land Act 1948": ["Cadastral Survey Act 2002", "Land Act 1948"],
    "the Civil Defence Emergency Management Act 2002 and Epidemic Preparedness Act 2006": ["Civil Defence Emergency Management Act 2002", "Epidemic Preparedness Act 2006"],
    "the Crown Entities Act 2004 and Public Finance Act 1989": ["Crown Entities Act 2004", "Public Finance Act 1989"],
    "the Social Security Act 2018 and Public and Community Housing Management Act 1992": ["Social Security Act 2018", "Public and Community Housing Management Act 1992"],
    "the Privacy Act 1993 and 2020": ["Privacy Act 1993", "Privacy Act 2020"],
}

def clean_name(name):
    n = name.strip()
    if n.lower().startswith("the "):
        n = n[4:]
    return n.strip()

distinct_acts = set()
for r in final_records:
    raw = r["act_name"].strip()
    if raw in CONFIRMED_COMPOUNDS:
        for part in CONFIRMED_COMPOUNDS[raw]:
            distinct_acts.add(part)
    else:
        distinct_acts.add(clean_name(raw))

print(f"Final validated citation relationships: {len(final_records)}")
print(f"Final distinct external Acts/Regulations (manually verified compounds only): {len(distinct_acts)}")
for name in sorted(distinct_acts):
    print(f"  {name}")

Path("data/processed/citation_relationships_final.json").write_text(
    json.dumps(final_records, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved to data/processed/citation_relationships_final.json")