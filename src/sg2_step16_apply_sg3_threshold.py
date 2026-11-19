"""
sg2_step16_apply_sg3_threshold.py

Applies the chosen SG3 threshold (score >= 6, picked on the same
elbow-in-the-distribution evidence used for SG1) to
sg3_combined_final_list.json (sg2_step15's output), producing the
finalized SG3 layer -- same shape/role as sg1_final_list.json and
sg2_final_list.json.
"""
import json
from pathlib import Path

INPUT_PATH = Path("data/processed/sg3_combined_final_list.json")
OUTPUT_PATH = Path("data/processed/sg3_final_list.json")
THRESHOLD = 6

with open(INPUT_PATH) as f:
    candidates = json.load(f)

final = [c for c in candidates if c["combined_score"] >= THRESHOLD]
final.sort(key=lambda c: -c["combined_score"])

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(final, f, indent=2, ensure_ascii=False)

print(f"SG3 final list (score >= {THRESHOLD}): {len(final)} Acts")
print(f"Score range: {final[-1]['combined_score']} - {final[0]['combined_score']}")
print()
print("Bottom 5 (right at the cutoff):")
for c in final[-5:]:
    print(f"  {c['act']}  (score {c['combined_score']})")
print()
print(f"Saved -> {OUTPUT_PATH}")