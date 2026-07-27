"""
Show the full extraction content for the 3 records that used a relation
type outside the controlled vocabulary, so we can decide the correct
fix for each based on real content, not guesswork.
"""

import json
from pathlib import Path

results = {r["provision_id"]: r["extraction"] for r in json.loads(Path("data/processed/extractions_full.json").read_text())}
warning_ids = ["LMS170678", "LMS172572", "LMS177893"]

for wid in warning_ids:
    print("=" * 60)
    print(wid)
    print("=" * 60)
    print(json.dumps(results.get(wid, "NOT FOUND"), indent=2, ensure_ascii=False))
    print()