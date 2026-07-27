"""
Final check: confirm every relation across all 1687 records now falls
within the five-type controlled vocabulary, and report the final
distribution — a real number worth including in the thesis write-up.
"""

import json
from pathlib import Path
from collections import Counter
from extraction_utils import ALLOWED_RELATION_TYPES

results = json.loads(Path("data/processed/extractions_full.json").read_text())
counts = Counter()
bad = []

for r in results:
    for rel in r["extraction"].get("relations", []):
        if not isinstance(rel, dict):
            bad.append((r["provision_id"], rel)); continue
        t = rel.get("type")
        counts[t] += 1
        if t not in ALLOWED_RELATION_TYPES:
            bad.append((r["provision_id"], t))

print(f"Final relation type distribution across all {len(results)} records:")
for t, c in counts.most_common():
    print(f"  {t}: {c}")
print(f"\nOutside the five-type vocabulary: {len(bad)}")
if bad:
    print(bad)