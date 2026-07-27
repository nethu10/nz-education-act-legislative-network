"""
Look at the current saved extraction for LMS272870 in full, to see
whether it's a good record with one stray junk element, or something
that needs a full regeneration like LMS267770 did.
"""

import json
from pathlib import Path

results = json.loads(Path("data/processed/extractions_full.json").read_text())
record = next(r for r in results if r["provision_id"] == "LMS272870")
print(json.dumps(record, indent=2, ensure_ascii=False))