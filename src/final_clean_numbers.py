"""
Recompute final headline numbers now that the 70 contaminated
repealed/empty records have been removed from extractions_full.json.
"""

import json
from pathlib import Path
from collections import Counter

results = json.loads(Path("data/processed/extractions_full.json").read_text())
counts = Counter()
for r in results:
    for rel in r["extraction"].get("relations", []):
        if isinstance(rel, dict):
            counts[rel.get("type")] += 1

total = sum(counts.values())
print(f"Extractable provisions (clean): {len(results)}")
print(f"Total relations (clean): {total}\n")
for t, c in counts.most_common():
    print(f"  {t}: {c} ({100*c/total:.1f}%)")