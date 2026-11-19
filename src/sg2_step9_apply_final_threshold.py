"""
sg2_step9_apply_final_threshold.py

Applies the final SG2 threshold (combined_score >= 3) to the merged
amendment + citation candidate pool, chosen on the same evidence standard
used throughout: last point before the marginal count starts running away
(89 Acts at score 3, then 259 at score 2, then 626 at score 1).

This is SG2, complete: both amendment and citation relationships,
self-referential / omnibus-taxation / invalid-name / bulk-event / hub
exclusions applied on both signal types, apostrophe-normalization fix
applied, threshold chosen the same way SG1's >=6 was.
"""
import json
from pathlib import Path

COMBINED_PATH = Path("data/processed/sg2_combined_final_list.json")
OUTPUT_PATH = Path("data/processed/sg2_final_list.json")

THRESHOLD = 3

with open(COMBINED_PATH) as f:
    combined = json.load(f)

final = [c for c in combined if c.get("combined_score", 0) >= THRESHOLD]
final.sort(key=lambda c: -c["combined_score"])

print(f"SG2 threshold: combined_score >= {THRESHOLD}")
print(f"SG2 final list: {len(final)} Acts")
scores = [c["combined_score"] for c in final]
print(f"Score range: {min(scores)} - {max(scores)}")

amend_only = sum(1 for c in final if c["citation_score"] == 0)
cite_only = sum(1 for c in final if c["amendment_score"] == 0)
both = len(final) - amend_only - cite_only
print(f"Amendment-only signal: {amend_only}")
print(f"Citation-only signal: {cite_only}")
print(f"Both signals: {both}")

with open(OUTPUT_PATH, "w") as f:
    json.dump(final, f, indent=2)

print(f"\nSaved -> {OUTPUT_PATH}")