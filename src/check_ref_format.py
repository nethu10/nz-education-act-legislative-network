"""
Quick diagnostic: shows what the intref/extref href values in
provisions.json actually look like, so we know whether they can be used
directly for SG2 citation extraction or need a translation/lookup step
first.
"""
import json
from pathlib import Path

PROVISIONS_PATH = Path("data/processed/provisions.json")

provisions = json.loads(PROVISIONS_PATH.read_text())

print("=== Sample external_refs (extref) ===")
ext_samples = [p for p in provisions if p.get("external_refs")][:8]
for p in ext_samples:
    print(f"{p['id']} -> {p['external_refs']}")

print()
print("=== Sample internal_refs (intref) ===")
int_samples = [p for p in provisions if p.get("internal_refs")][:5]
for p in int_samples:
    print(f"{p['id']} -> {p['internal_refs']}")

print()
print(f"Total provisions: {len(provisions)}")
print(f"Provisions with external_refs: {sum(1 for p in provisions if p.get('external_refs'))}")
print(f"Provisions with internal_refs: {sum(1 for p in provisions if p.get('internal_refs'))}")