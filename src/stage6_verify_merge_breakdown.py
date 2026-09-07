"""
Break down the 969 second-ring Acts by direction (outgoing vs incoming)
to confirm the 546 already-documented figure is a genuine subset, and
to see exactly how much the "incoming" direction added -- before
deciding whether the documented 2-ring stopping justification needs
updating to reflect the full bidirectional picture.
"""

import json
from pathlib import Path

target_summary = json.loads(Path("data/processed/stage6_target_acts_summary.json").read_text())

outgoing_only = set()
incoming_only = set()

for act in target_summary:
    outgoing_only.update(act.get("outgoing_targets", []))
    incoming_only.update(act.get("incoming_sources", []))

both_directions = outgoing_only | incoming_only
overlap = outgoing_only & incoming_only

print(f"Distinct Acts via OUTGOING only: {len(outgoing_only)}  (should match the earlier-documented 546)")
print(f"Distinct Acts via INCOMING only: {len(incoming_only)}")
print(f"Union (both directions): {len(both_directions)}  (should match the graph's 969 new nodes)")
print(f"Overlap (appear in both directions): {len(overlap)}")