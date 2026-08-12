"""
Find any judgement values that aren't the expected single letters c/i/p
-- likely introduced during direct manual edits to the JSON file that
bypassed the annotator script's built-in validation.
"""

import json
from pathlib import Path

sample = json.loads(Path("data/processed/stage4_manual_sample.json").read_text())

VALID = {"c", "i", "p"}
bad = [r for r in sample if r["judgement"] not in VALID]

print(f"Total records: {len(sample)}")
print(f"Records with non-standard judgement values: {len(bad)}")
for r in bad:
    print(f"  {r['provision_id']}: judgement={r['judgement']!r}")