"""
Removes the 70 extraction records built from genuinely empty/repealed
provisions \u2014 these were built on no real text and should not remain
in the dataset used for analysis or reporting.
"""

import json
from pathlib import Path

provisions = json.loads(Path("data/processed/provisions.json").read_text())
empty_ids = {p["id"] for p in provisions if len(p.get("text", "").strip()) < 20}

results = json.loads(Path("data/processed/extractions_full.json").read_text())
before = len(results)
clean_results = [r for r in results if r["provision_id"] not in empty_ids]
removed = before - len(clean_results)

Path("data/processed/extractions_full.json").write_text(
    json.dumps(clean_results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"Removed {removed} contaminated records built from empty/repealed provisions.")
print(f"Remaining: {len(clean_results)} (of {before} original)")