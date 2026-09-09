"""
Confirm the heading fix worked by re-checking the same mismatch test,
expecting the full, correct headings instead of the truncated versions.
"""
import json
from pathlib import Path

provisions = json.loads(Path("data/processed/provisions.json").read_text())
sample_ids = ["LMS171365", "LMS262280", "LMS172277"]
for p in provisions:
    if p["id"] in sample_ids:
        print(f"{p['id']}: heading={p['heading']!r}")