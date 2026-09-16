"""
Shows the complete SG1 candidate list at the recommended score >= 6
cutoff, so every Act can be reviewed before finalizing -- not just
the top 30 already seen.
"""

import json
from pathlib import Path

final = json.loads(Path("data/processed/sg1_ranking_final.json").read_text())
candidates = [r for r in final if r["combined_score"] >= 6]

print(f"Full SG1 candidate list at score >= 6: {len(candidates)} Acts\n")
for i, r in enumerate(candidates, 1):
    print(f"{i:3d}. {r['combined_score']:3d}  (out:{r['outgoing_amendments']}, in:{r['incoming_amendments']}, cite:{r['citations']})  {r['act']}")

Path("data/processed/sg1_final_list.json").write_text(
    json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved to data/processed/sg1_final_list.json")