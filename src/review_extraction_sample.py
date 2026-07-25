"""
Quick systematic review of the 20-record extraction sample — checks for
patterns across all of them at once, rather than reading each JSON
blob individually with nothing to compare against.
"""

import json
from collections import Counter
from pathlib import Path

results = json.loads(Path("data/processed/extraction_sample.json").read_text())
provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}

relation_type_counts = Counter()
empty_relations = []
empty_entities = []

for r in results:
    ext = r["extraction"]
    types_here = [rel["type"] for rel in ext.get("relations", [])]
    relation_type_counts.update(types_here)

    if not ext.get("relations"):
        empty_relations.append(r["provision_id"])
    if not ext.get("entities"):
        empty_entities.append(r["provision_id"])

print("Relation type distribution across all 20 records:")
for rel_type, count in relation_type_counts.most_common():
    print(f"  {rel_type}: {count}")

print(f"\nRecords with NO relations found: {len(empty_relations)} -> {empty_relations}")
print(f"Records with NO entities found: {len(empty_entities)} -> {empty_entities}")

# Print full detail for the 3 longest source texts — where mistakes are
# most likely to hide, since there's more for the model to get wrong.
print("\n" + "=" * 60)
print("Full detail: the 3 longest provisions in the sample")
print("=" * 60)
by_length = sorted(results, key=lambda r: len(provisions[r["provision_id"]]["text"]), reverse=True)
for r in by_length[:3]:
    prov = provisions[r["provision_id"]]
    print(f"\n--- {r['provision_id']} ({prov['type']}, heading: {prov['heading']}) ---")
    print("Source text:", prov["text"][:300])
    print("Extraction:", json.dumps(r["extraction"], indent=2, ensure_ascii=False))