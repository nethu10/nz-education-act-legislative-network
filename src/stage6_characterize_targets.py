"""
Stage 6, pre-check: characterize the 193 confirmed connected Acts before
designing the expansion approach -- how many are genuine Public Acts
(fetchable the same way as the seed Act) versus secondary legislation
(Regulations, Legislative Instruments), and which Acts are touched by
the most outgoing amendment records -- a natural, evidence-based
priority signal for a depth-limited expansion, rather than treating
all 193 as equally important.
"""

import json
import re
from pathlib import Path
from collections import Counter

outgoing = json.loads(Path("data/processed/outgoing_amendments.json").read_text())

target_counts = Counter(r["target_act"] for r in outgoing if r["target_act"])

print(f"Total distinct target Acts/Regulations: {len(target_counts)}")
print(f"Total outgoing amendment records: {len(outgoing)}")


def classify(name):
    if re.search(r"\(SR \d{4}/\d+\)", name):
        return "Regulations (SR)"
    if re.search(r"\(LI \d{4}/\d+\)", name):
        return "Legislative Instrument (LI)"
    if re.search(r"\(\d{4} No \d+\)", name):
        return "Public Act"
    return "Other/Unclassified"


type_counts = Counter(classify(name) for name in target_counts)
print("\nBreakdown by legislation type:")
for t, c in type_counts.most_common():
    print(f"  {t}: {c}")

print("\nTop 20 most-referenced target Acts (by number of outgoing amendment records):")
for name, count in target_counts.most_common(20):
    print(f"  {count:3d}  {name}")