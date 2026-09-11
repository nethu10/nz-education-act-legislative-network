"""
Builds a complete, correctly-typed amendment relationship list, using
only the government's own official structured records -- no SLM
needed, since operation type is either already labelled (incoming)
or reliably detectable from the real amendment wording (outgoing).
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def classify_operation(text):
    t = text.lower()
    if re.search(r"\brepeal(s|ed|ing)?\b", t):
        return "repeal"
    if re.search(r"\binsert(s|ed|ing)?\b", t):
        return "insert"
    if re.search(r"\breplace(s|d|ing)?\b", t):
        return "replace"
    if re.search(r"\bomit(s|ted|ting)?\b", t):
        return "omit"
    return "amend (other)"

outgoing = json.loads(Path("data/processed/outgoing_amendments.json").read_text())
incoming = json.loads(Path("data/processed/amendment_records.json").read_text())

outgoing_by_act = defaultdict(lambda: defaultdict(int))
for r in outgoing:
    act = r.get("target_act")
    if act:
        outgoing_by_act[act][classify_operation(r.get("text", ""))] += 1

incoming_by_act = defaultdict(lambda: defaultdict(int))
for r in incoming:
    act = r.get("amending_act")
    if act:
        incoming_by_act[act][(r.get("operation") or "unspecified").lower()] += 1

records = []
for act, ops in outgoing_by_act.items():
    records.append({"act": act, "direction": "this Act amends them", "operations": dict(ops), "total": sum(ops.values())})
for act, ops in incoming_by_act.items():
    records.append({"act": act, "direction": "they amend this Act", "operations": dict(ops), "total": sum(ops.values())})

records.sort(key=lambda x: -x["total"])
Path("data/processed/amendment_relationships_typed.json").write_text(
    json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Total amendment-type connections: {len(records)}")
op_totals = defaultdict(int)
for r in records:
    for op, count in r["operations"].items():
        op_totals[op] += count
print("\nBreakdown by operation type (across all connections):")
for op, count in sorted(op_totals.items(), key=lambda x: -x[1]):
    print(f"  {op}: {count}")