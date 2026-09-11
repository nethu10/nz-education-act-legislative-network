"""
Checks records 241-260 specifically (the batch that produced zero new
citation confirmations) to see whether this was a genuine content
coincidence or something that needs investigating -- plus samples a
handful of the confirmed results overall for a real accuracy spot-check.
"""

import json
from pathlib import Path

extractions = json.loads(Path("data/processed/extractions_full.json").read_text())
candidate_pattern_provisions = []
import re
candidate_pattern = re.compile(r"\b(Act|Regulation|Rule)s?\b", re.IGNORECASE)
for e in extractions:
    for rel in e["extraction"].get("relations", []):
        if isinstance(rel, dict) and candidate_pattern.search(rel.get("description", "")):
            candidate_pattern_provisions.append({"provision_id": e["provision_id"], "description": rel.get("description")})

print("Records 241-260 (the flat batch) -- real content:")
for c in candidate_pattern_provisions[240:260]:
    print(f"  {c['provision_id']}: \"{c['description'][:120]}\"")

print("\n" + "="*60)
print("Sample of 8 CONFIRMED citation relationships, for accuracy spot-check:")
results = json.loads(Path("data/processed/citation_relationships_slm.json").read_text())
for r in results[:8]:
    print(f"\n  {r['provision_id']} (original type: {r['type']})")
    print(f"    description: \"{r['description'][:120]}\"")
    print(f"    AI found: act_name={r['act_name']!r}")