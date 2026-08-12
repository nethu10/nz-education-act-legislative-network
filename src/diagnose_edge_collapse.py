"""
Check whether the gap between edges "added" (1847) and unique edges in
the final graph (1540) is explained by provisions citing the same
target more than once in their own internal_refs list -- confirming
this is a benign edge-collapse, not a construction error.
"""

import json
from pathlib import Path
from collections import Counter

provisions = json.loads(Path("data/processed/provisions.json").read_text())
extractable = [p for p in provisions if not p.get("is_repealed_or_empty")]

total_ref_mentions = 0
duplicate_within_provision = 0
examples = []

for p in extractable:
    refs = p.get("internal_refs", [])
    total_ref_mentions += len(refs)
    counts = Counter(refs)
    dupes_here = sum(c - 1 for c in counts.values() if c > 1)
    duplicate_within_provision += dupes_here
    if dupes_here > 0 and len(examples) < 5:
        repeated = {href: c for href, c in counts.items() if c > 1}
        examples.append((p["id"], repeated))

print(f"Total internal_refs mentions across extractable provisions: {total_ref_mentions}")
print(f"Of which are same-target repeats within the same provision: {duplicate_within_provision}")
print(f"\nExamples:")
for pid, repeated in examples:
    print(f"  {pid}: {repeated}")
    