"""
Look at the 2 records that failed extraction even after retries, and the
3 that produced validation warnings, before deciding whether to manually
recover them or document them as a small, explained exclusion.
"""

import json
from pathlib import Path

provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}

print("=" * 60)
print("THE 2 FAILED RECORDS")
print("=" * 60)
for failed_id in ["LMS267770", "LMS272870"]:
    p = provisions.get(failed_id)
    if p:
        print(f"\n{failed_id} ({p['type']}, heading: {p['heading']})")
        print("Text:", p["text"][:500])
    else:
        print(f"\n{failed_id}: not found in provisions.json")

print("\n" + "=" * 60)
print("THE 3 VALIDATION WARNINGS")
print("=" * 60)
warnings = json.loads(Path("data/processed/extraction_warnings.json").read_text())
for w in warnings:
    print(f"\n{w['provision_id']}: {w['warnings']}")