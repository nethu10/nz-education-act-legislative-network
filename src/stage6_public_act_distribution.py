"""
Stage 6, pre-check part 2: full distribution of outgoing amendment
counts among genuine Public Acts only, to find a natural, evidence-based
cutoff point for depth-limited expansion, rather than picking an
arbitrary number.
"""

import json
import re
from pathlib import Path
from collections import Counter

outgoing = json.loads(Path("data/processed/outgoing_amendments.json").read_text())
target_counts = Counter(r["target_act"] for r in outgoing if r["target_act"])


def is_public_act(name):
    return bool(re.search(r"\(\d{4} No \d+\)", name)) and not re.search(r"\(SR \d{4}/\d+\)|\(LI \d{4}/\d+\)", name)


public_acts = {name: c for name, c in target_counts.items() if is_public_act(name)}
print(f"Total genuine Public Acts: {len(public_acts)}")

sorted_acts = sorted(public_acts.items(), key=lambda x: -x[1])
print("\nFull ranked list:")
for i, (name, count) in enumerate(sorted_acts, 1):
    print(f"{i:3d}. {count:3d}  {name}")

# Distribution summary
counter_of_counts = Counter(public_acts.values())
print("\nHow many Public Acts have exactly N references:")
for n in sorted(counter_of_counts.keys(), reverse=True):
    print(f"  {n} reference(s): {counter_of_counts[n]} Acts")