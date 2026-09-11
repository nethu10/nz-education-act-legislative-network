"""
Normalizes amendment operation labels to one consistent set, fixing
the duplication caused by outgoing data using present-tense keyword
detection while incoming data uses the government's own past-tense
field directly -- same real operations, previously split into two
different-looking labels.
"""

import json
from pathlib import Path
from collections import defaultdict

CANONICAL = {
    "amended": "amend", "amend (other)": "amend",
    "replaced": "replace", "replace": "replace",
    "repealed": "repeal", "repeal": "repeal",
    "inserted": "insert", "insert": "insert",
    "omitted": "omit", "omit": "omit",
    "renumbered": "renumber",
}

records = json.loads(Path("data/processed/amendment_relationships_typed.json").read_text())

for r in records:
    new_ops = defaultdict(int)
    for op, count in r["operations"].items():
        canon = CANONICAL.get(op, op)
        new_ops[canon] += count
    r["operations"] = dict(new_ops)

Path("data/processed/amendment_relationships_typed.json").write_text(
    json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
)

print(f"Distinct Acts (connections): {len(records)}")

op_totals = defaultdict(int)
for r in records:
    for op, count in r["operations"].items():
        op_totals[op] += count
total_instances = sum(op_totals.values())

print(f"Total individual amendment instances across all connections: {total_instances}")
print("\nCorrected breakdown by operation type:")
for op, count in sorted(op_totals.items(), key=lambda x: -x[1]):
    print(f"  {op}: {count} ({100*count/total_instances:.1f}%)")