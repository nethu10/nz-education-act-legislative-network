"""
Find exactly why 1,008 distinct second-ring Act names produced only 969
new graph nodes -- most likely because some of those names coincide
with Acts already present in the graph before this merge (the original
193/20 seed-Act connections, or the 13 ring-1 Acts themselves).
"""

import json
import pickle
from pathlib import Path

# Reconstruct the ORIGINAL set of external Act names already in the
# graph before Stage 6's merge (from Stage 2's seed-Act amendment data)
outgoing_original = json.loads(Path("data/processed/outgoing_amendments.json").read_text())
incoming_original = json.loads(Path("data/processed/amendment_records.json").read_text())
original_names = set(r["target_act"] for r in outgoing_original if r["target_act"])
original_names |= set(r["amending_act"] for r in incoming_original if r["amending_act"])
print(f"Original external Act names already in graph before merge: {len(original_names)}")

target_summary = json.loads(Path("data/processed/stage6_target_acts_summary.json").read_text())
ring1_names = set(act["name"] for act in target_summary)

second_ring_union = set()
for act in target_summary:
    second_ring_union.update(act.get("outgoing_targets", []))
    second_ring_union.update(act.get("incoming_sources", []))

overlap_with_original = second_ring_union & original_names
overlap_with_ring1 = second_ring_union & ring1_names
genuinely_new = second_ring_union - original_names - ring1_names

print(f"Second-ring union: {len(second_ring_union)}")
print(f"  Overlap with original 213 seed-Act connections: {len(overlap_with_original)}")
print(f"  Overlap with the 13 ring-1 Acts themselves: {len(overlap_with_ring1)}")
print(f"  Genuinely new nodes (should match the 969 added): {len(genuinely_new)}")