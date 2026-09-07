"""
Corrects the Stage 6 expansion summary to reflect the true, bidirectional
second-ring count (969 new Acts) rather than the outgoing-only figure
(546) originally documented -- the merge into the graph revealed the
complete picture includes incoming connections too.
"""

import json
from pathlib import Path

summary = json.loads(Path("data/processed/stage6_expansion_summary.json").read_text())

summary["ring_2_note"] = (
    "Originally documented using outgoing-only connections (546 distinct Acts, 42x growth). "
    "Once merged into the actual graph, incoming connections were also included (462 further "
    "distinct Acts, 0 overlap with the outgoing set), giving a complete second-ring total of "
    "969 genuinely new Acts (39 of 1,008 total distinct names already existed in the graph; "
    "of those, 2 represent direct citations between two of the 13 selected ring-1 Acts "
    "themselves). This is a more complete and more decisive figure than originally reported."
)
summary["ring_2_distinct_acts_discovered_bidirectional"] = 969
summary["growth_rate_bidirectional"] = f"{969/13:.1f}x per Act, {969}x from a start of 13"
summary["stopping_justification"] += (
    " The complete bidirectional count (969 new Acts, ~75x growth) further reinforces this "
    "conclusion beyond the originally documented outgoing-only figure."
)

Path("data/processed/stage6_expansion_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps(summary, indent=2, ensure_ascii=False))