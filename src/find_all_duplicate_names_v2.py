"""
Corrected version: runs the same shorthand-duplicate merge as before,
but against sg1_ranking_final.json -- the fully cleaned file with both
self-referential entries AND confirmed bulk-mechanical-event Acts
already removed -- not the intermediate, partially-cleaned file used
by mistake last time.
"""

import json
import re
from pathlib import Path

citations_raw = json.loads(Path("data/processed/citation_relationships_final.json").read_text())
DEFINES_PATTERN = re.compile(r"defines\s+'([^']+)'\s+as\s+'([^']+)'", re.IGNORECASE)

found_pairs = set()
for r in citations_raw:
    m = DEFINES_PATTERN.search(r["description"])
    if m:
        found_pairs.add((m.group(1), m.group(2)))

print("Explicit shorthand definitions found:")
for shorthand, full_name in found_pairs:
    print(f"  '{shorthand}' = '{full_name}'")

# Correct source: the fully cleaned file (self-referential AND bulk-event Acts already removed)
final = json.loads(Path("data/processed/sg1_ranking_final.json").read_text())
by_name = {r["act"]: r for r in final}

for shorthand, full_name in found_pairs:
    if shorthand in by_name and full_name in by_name:
        combined = by_name[full_name]
        short_entry = by_name[shorthand]
        combined["outgoing_amendments"] += short_entry["outgoing_amendments"]
        combined["incoming_amendments"] += short_entry["incoming_amendments"]
        combined["citations"] += short_entry["citations"]
        combined["combined_score"] += short_entry["combined_score"]
        print(f"\nMerged '{shorthand}' into '{full_name}': new combined_score = {combined['combined_score']}")
        del by_name[shorthand]

result = sorted(by_name.values(), key=lambda x: -x["combined_score"])

# Sanity check -- confirm the 3 bulk-event Acts are genuinely absent this time
BULK_EVENTS = {"Secondary Legislation Act 2021", "Public Service Act 2020",
               "Employment Relations (Pay Deductions for Partial Strikes) Amendment Act 2025"}
still_present = [r["act"] for r in result if r["act"] in BULK_EVENTS]
print(f"\nSanity check -- bulk-event Acts still present (should be empty): {still_present}")

Path("data/processed/sg1_ranking_deduplicated.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
)

candidates = [r for r in result if r["combined_score"] >= 6]
print(f"\nTotal distinct Acts after correct deduplication: {len(result)}")
print(f"SG1 candidates at score >= 6: {len(candidates)}\n")
for i, r in enumerate(candidates, 1):
    print(f"{i:3d}. {r['combined_score']:3d}  {r['act']}")

Path("data/processed/sg1_final_list.json").write_text(
    json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8"
)