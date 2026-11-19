"""
sg4_step10_finalize_sg5.py

Builds the SG5 candidate pool and applies the evidence-based threshold
(>=6, chosen 2026-09-24 from sg4_step07's distribution analysis on the
CLEANED 573-candidate pool -- it lines up with SG5's own natural break
(the decay rate through the threshold sweep bottoms out at 5->6: the
smallest relative drop of the whole descending run, -15.0%, right
before the rate climbs back up at 6->7) AND matches SG1, SG3, and
SG4's precedent, the same dual justification used to finalize SG4:
a natural break in this layer's own distribution, not just a reused
number.

Source: data/processed/sg4_new_candidates_seen.json (573 cleaned
candidates -- everything referenced by an SG4 Act that fell outside
seed+SG1+SG2+SG3+SG4, found by sg4_step06_find_sg4_internal_links.py,
then cleaned of structural pseudo-candidates and cross-layer
duplicates by sg4_step09_clean_sg5_candidates.py).

Writes:
  data/processed/sg5_combined_final_list.json  -- full pre-threshold
    pool (573 candidates), same role as sg4_combined_final_list.json
  data/processed/sg5_final_list.json           -- candidates with
    combined_score >= 6 (expected 51), same role as sg4_final_list.json

Both preserve every field from the source data (act, combined_score,
linked_from) rather than dropping anything -- linked_from especially
is worth keeping, since it's the provenance record of which SG4 Acts
pulled each SG5 candidate in, useful later for the methodology write-up
and for tracing any given SG5 Act back to why it's in the network.
"""
import json
from pathlib import Path

CANDIDATES_PATH = Path("data/processed/sg4_new_candidates_seen.json")
COMBINED_OUT = Path("data/processed/sg5_combined_final_list.json")
FINAL_OUT = Path("data/processed/sg5_final_list.json")

THRESHOLD = 6

with open(CANDIDATES_PATH, encoding="utf-8") as f:
    raw = json.load(f)

if isinstance(raw, dict):
    entries = [{"act": k, **v} for k, v in raw.items()]
else:
    entries = raw

if not entries:
    raise SystemExit(f"{CANDIDATES_PATH} is empty -- nothing to build SG5 from.")

with open(COMBINED_OUT, "w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2, ensure_ascii=False)
print(f"Saved -> {COMBINED_OUT}  ({len(entries)} candidates, full pre-threshold pool)")

sg5_final = [e for e in entries if e.get("combined_score", 0) >= THRESHOLD]

with open(FINAL_OUT, "w", encoding="utf-8") as f:
    json.dump(sg5_final, f, indent=2, ensure_ascii=False)
print(f"Saved -> {FINAL_OUT}  ({len(sg5_final)} Acts, combined_score >= {THRESHOLD})")

print(
    f"\nSG5 finalized: {len(sg5_final)} Acts "
    f"({100 * len(sg5_final) / len(entries):.1f}% of the {len(entries)}-candidate pool)."
)