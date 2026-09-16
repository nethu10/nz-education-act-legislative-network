"""
Systematically checks for other shorthand/full-name duplicates like
"1989 Act" = "Education Act 1989", by searching every citation
description for an explicit "defines 'X' as 'Y'" pattern -- your own
Act's text is the most reliable source for confirming these, since it
states the equivalence directly rather than requiring guesswork.
"""

import json
import re
from pathlib import Path

citations_raw = json.loads(Path("data/processed/citation_relationships_final.json").read_text())

DEFINES_PATTERN = re.compile(r"defines\s+'([^']+)'\s+as\s+'([^']+)'", re.IGNORECASE)

print("Explicit shorthand definitions found in your Act's own text:")
found_pairs = []
for r in citations_raw:
    m = DEFINES_PATTERN.search(r["description"])
    if m:
        shorthand, full_name = m.group(1), m.group(2)
        found_pairs.append((shorthand, full_name, r["provision_id"]))
        print(f"  '{shorthand}' = '{full_name}'  (from {r['provision_id']})")

print(f"\nTotal explicit shorthand pairs found: {len(found_pairs)}")

# Now merge these into the ranking
final = json.loads(Path("data/processed/sg1_ranking_cleaned.json").read_text())
by_name = {r["act"]: r for r in final}

merged_any = False
for shorthand, full_name, _ in set((s, f, "") for s, f, p in found_pairs):
    if shorthand in by_name and full_name in by_name:
        merged_any = True
        combined = by_name[full_name]
        short_entry = by_name[shorthand]
        combined["outgoing_amendments"] += short_entry["outgoing_amendments"]
        combined["incoming_amendments"] += short_entry["incoming_amendments"]
        combined["citations"] += short_entry["citations"]
        combined["combined_score"] += short_entry["combined_score"]
        print(f"\nMerged '{shorthand}' into '{full_name}': new combined_score = {combined['combined_score']}")
        del by_name[shorthand]

result = sorted(by_name.values(), key=lambda x: -x["combined_score"])
Path("data/processed/sg1_ranking_deduplicated.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\n{'Merges applied.' if merged_any else 'No mergeable duplicates found.'}")
print(f"Total distinct Acts after deduplication: {len(result)}")

candidates = [r for r in result if r["combined_score"] >= 6]
print(f"\nSG1 candidates at score >= 6 after deduplication: {len(candidates)}")
for i, r in enumerate(candidates, 1):
    print(f"{i:3d}. {r['combined_score']:3d}  {r['act']}")