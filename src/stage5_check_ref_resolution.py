"""
Stage 5, pre-check: verify how many internal_refs hrefs actually resolve
to a real provision/definition ID in provisions.json, before building
the graph's structural edges on top of this assumption.
"""

import json
from pathlib import Path

provisions = json.loads(Path("data/processed/provisions.json").read_text())
extractable = [p for p in provisions if not p.get("is_repealed_or_empty")]
all_ids = {p["id"] for p in provisions}
extractable_ids = {p["id"] for p in extractable}

total_refs = 0
resolved_extractable = 0
resolved_repealed_only = 0
unresolved = 0
unresolved_examples = []

for p in extractable:
    for href in p.get("internal_refs", []):
        total_refs += 1
        if href in extractable_ids:
            resolved_extractable += 1
        elif href in all_ids:
            resolved_repealed_only += 1
        else:
            unresolved += 1
            if len(unresolved_examples) < 10:
                unresolved_examples.append((p["id"], href))

print(f"Total internal_refs across {len(extractable)} extractable provisions: {total_refs}")
print(f"Resolved to an extractable provision/definition: {resolved_extractable} ({100*resolved_extractable/total_refs:.1f}%)")
print(f"Resolved but target is repealed/empty: {resolved_repealed_only} ({100*resolved_repealed_only/total_refs:.1f}%)")
print(f"Unresolved entirely: {unresolved} ({100*unresolved/total_refs:.1f}%)")
print(f"\nExample unresolved hrefs: {unresolved_examples}")