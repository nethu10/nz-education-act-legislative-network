"""
Stage 4, Part 2: draws a stratified manual-validation sample across all
five relation types, proportional to their share of the dataset, for
manual precision checking against the source text.

Sample size: 100 relations, allocated proportionally to each type's
share of the 3,255 total \u2014 large enough for a defensible confidence
interval, small enough to hand-check in one sitting.
"""

import json
import random
from pathlib import Path
from collections import defaultdict

random.seed(42)  # reproducible sample, matching the Stage 3 sample convention

extractions = json.loads(Path("data/processed/extractions_full.json").read_text())
provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}

# Flatten to one row per (provision_id, relation) pair
all_relations = []
for e in extractions:
    pid = e["provision_id"]
    for rel in e["extraction"].get("relations", []):
        if isinstance(rel, dict) and rel.get("type"):
            all_relations.append({"provision_id": pid, "type": rel["type"], "description": rel.get("description", "")})

by_type = defaultdict(list)
for r in all_relations:
    by_type[r["type"]].append(r)

TOTAL_SAMPLE = 100
total_relations = len(all_relations)
print(f"Total relations: {total_relations}\n")

sample = []
for rel_type, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
    share = len(items) / total_relations
    n = max(1, round(share * TOTAL_SAMPLE))
    n = min(n, len(items))
    picked = random.sample(items, n)
    sample.extend(picked)
    print(f"{rel_type}: {len(items)} total ({share*100:.1f}%) -> {n} sampled")

print(f"\nTotal sample size: {len(sample)}")

# Attach the real provision text for manual review
output = []
for r in sample:
    prov = provisions.get(r["provision_id"], {})
    output.append({
        "provision_id": r["provision_id"],
        "heading": prov.get("heading"),
        "type": r["type"],
        "slm_description": r["description"],
        "source_text": prov.get("text", ""),
        "judgement": "",       # to be filled in manually: correct / incorrect / partial
        "notes": "",           # to be filled in manually
    })

out_path = Path("data/processed/stage4_manual_sample.json")
out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nSaved to {out_path} \u2014 ready for manual annotation.")