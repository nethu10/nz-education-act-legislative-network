"""
sg2_step5_apply_threshold.py

Applies the SG2 threshold (combined_score >= 3), chosen against the
marginal-count evidence: no sharp break between scores 3 and 4, but a
sharp one between 3 and 2 (47 Acts at score 3 vs 111 at score 2, then 433
at score 1) -- same "last point before runaway growth" logic used to
justify SG1's >=6 threshold.

Reads the cleaned pool (self-referential / omnibus-tax / bulk-event /
invalid-name already excluded, duplicates already merged) and writes the
ranked list.

NOTE: this is the amendment-relationship half of SG2 only -- same as SG1,
the amendment-based scores here don't yet include citation-type
relationships (SG1's final scores were amendment count + citation count
combined). The SG2 citation-extraction step is still open, so treat this
as the amendment-based SG2 list pending that decision, not the complete
SG2 the way SG1's 37 were complete.
"""
import json
from pathlib import Path

CLEANED_PATH = Path("data/processed/sg2_cleaned_candidates.json")
OUTPUT_PATH = Path("data/processed/sg2_amendment_final_list.json")

THRESHOLD = 3

with open(CLEANED_PATH) as f:
    cleaned = json.load(f)

final = [c for c in cleaned if c.get("combined_score", 0) >= THRESHOLD]
final.sort(key=lambda c: -c.get("combined_score", 0))

print(f"SG2 threshold: combined_score >= {THRESHOLD}")
print(f"SG2 amendment-based list: {len(final)} Acts")
scores = [c["combined_score"] for c in final]
print(f"Score range: {min(scores)} - {max(scores)}")

with open(OUTPUT_PATH, "w") as f:
    json.dump(final, f, indent=2)

print(f"\nSaved -> {OUTPUT_PATH}")