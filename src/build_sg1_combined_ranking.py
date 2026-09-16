"""
Builds one combined connection-strength ranking per external Act,
merging outgoing amendments, incoming amendments, and validated
citations -- normalizing names across the two different data sources
first, since they were extracted in different formats. This replaces
the earlier amendment-only ranking with a fuller, more defensible
picture before choosing SG1's cutoff.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def normalize_name(name):
    """Strips '(2004 No 115)'-style suffixes, leading 'the', and
    lowercases, so names from different sources can be matched."""
    n = name.strip()
    n = re.sub(r"^(the)\s+", "", n, flags=re.IGNORECASE)
    n = re.sub(r"\s*\(\d{4}\s*No\s*\d+\)\s*$", "", n, flags=re.IGNORECASE)
    n = re.sub(r"\s*\((SR|LI)\s*\d{4}/\d+\)\s*$", "", n, flags=re.IGNORECASE)
    return n.strip().lower()

amendments = json.loads(Path("data/processed/amendment_relationships_typed.json").read_text())
citations = json.loads(Path("data/processed/citation_relationships_final.json").read_text())

combined = defaultdict(lambda: {"display_name": None, "outgoing": 0, "incoming": 0, "citations": 0})

for r in amendments:
    key = normalize_name(r["act"])
    entry = combined[key]
    if entry["display_name"] is None:
        entry["display_name"] = r["act"]
    if r["direction"] == "this Act amends them":
        entry["outgoing"] = r["total"]
    else:
        entry["incoming"] = r["total"]

# Citation records need their own per-Act tally, since citation_relationships_final.json
# is a flat list of individual mentions, not pre-aggregated like the amendment data
citation_counts = defaultdict(int)
for r in citations:
    key = normalize_name(r["act_name"])
    citation_counts[key] += 1

for key, count in citation_counts.items():
    entry = combined[key]
    if entry["display_name"] is None:
        entry["display_name"] = key.title()
    entry["citations"] = count

results = []
for key, entry in combined.items():
    total = entry["outgoing"] + entry["incoming"] + entry["citations"]
    results.append({
        "act": entry["display_name"], "outgoing_amendments": entry["outgoing"],
        "incoming_amendments": entry["incoming"], "citations": entry["citations"],
        "combined_score": total,
    })

results.sort(key=lambda x: -x["combined_score"])

print(f"Total distinct Acts across all three relationship types: {len(results)}")
print(f"\nFull ranked list:")
for i, r in enumerate(results, 1):
    print(f"{i:3d}. {r['combined_score']:3d}  (out:{r['outgoing_amendments']}, in:{r['incoming_amendments']}, cite:{r['citations']})  {r['act']}")

from collections import Counter
score_counts = Counter(r["combined_score"] for r in results)
print(f"\nHow many Acts have exactly N combined connections:")
for score in sorted(score_counts.keys(), reverse=True):
    print(f"  {score}: {score_counts[score]} Act(s)")

Path("data/processed/sg1_combined_ranking.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved to data/processed/sg1_combined_ranking.json")