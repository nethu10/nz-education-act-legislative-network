"""
Stage 6 completion: document the two-ring expansion boundary with the
evidence that justifies stopping here, and save the full set of
confirmed second-ring connections as stub-level data (name only, not
further expanded).
"""

import json
from pathlib import Path

target_summary = json.loads(Path("data/processed/stage6_target_acts_summary.json").read_text())
outgoing_original = json.loads(Path("data/processed/outgoing_amendments.json").read_text())
original_193 = set(r["target_act"] for r in outgoing_original if r["target_act"])

second_ring = set()
for r in target_summary:
    second_ring.update(r["outgoing_targets"])

summary = {
    "expansion_boundary": "2 rings (seed Act -> 13 selected Acts -> second-ring connections, not expanded further)",
    "ring_1_acts_selected": 13,
    "ring_1_selection_criterion": ">=7 outgoing amendment records from the seed Act (evidence-based cutoff, see stage6_public_act_distribution.py)",
    "ring_2_distinct_acts_discovered": len(second_ring),
    "ring_2_overlap_with_original_193": len(second_ring & original_193),
    "ring_2_genuinely_new": len(second_ring - original_193),
    "growth_rate": f"{len(second_ring) / 13:.1f}x per Act, {len(second_ring)}x from a start of 13",
    "stopping_justification": (
        "A single further hop discovered 546 distinct Acts from just 13 starting points, "
        "a 42x expansion, with only 5% overlap against the original 193 -- confirming rapid, "
        "largely non-overlapping growth. The single largest contributor (Income Tax Act 2007, "
        "342 of 546) demonstrates that continued expansion is dominated by administrative "
        "breadth (tax law touching nearly all legislation) rather than thematic relevance to "
        "education policy. Consistent with the pre-registered 'fixed-depth, 2-3 layer' "
        "expansion boundary in the methodology, expansion stops after this second ring."
    )
}

Path("data/processed/stage6_expansion_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps(summary, indent=2, ensure_ascii=False))