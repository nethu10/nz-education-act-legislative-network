"""
sg4_step02_finalize_sg4.py

Builds the SG4 candidate pool and applies the evidence-based threshold
(>=6, chosen 2026-09-23 from sg4_step01's distribution analysis -- it
lines up with SG4's own top-quartile break (p75=6) AND matches SG1 and
SG3's precedent, the strongest available justification: a natural
break in this layer's own distribution, not just a reused number).

Source: data/processed/sg3_new_candidates_seen.json (4,635 raw
candidates -- everything referenced by an SG3 Act that fell outside
seed+SG1+SG2+SG3, found by sg2_step26_find_sg3_internal_links.py).

Writes:
  data/processed/sg4_combined_final_list.json  -- full pre-threshold
    pool (4,635 candidates), same role as sg3_combined_final_list.json
  data/processed/sg4_final_list.json           -- candidates with
    combined_score >= 6 (expected 1,169), same role as
    sg3_final_list.json

Both preserve every field from the source data (act, combined_score,
linked_from) rather than dropping anything -- linked_from especially
is worth keeping, since it's the provenance record of which SG3 Acts
pulled each SG4 candidate in, useful later for the methodology write-up
and for tracing any given SG4 Act back to why it's in the network.
"""
import json
from pathlib import Path

CANDIDATES_PATH = Path("data/processed/sg3_new_candidates_seen.json")
COMBINED_OUT = Path("data/processed/sg4_combined_final_list.json")
FINAL_OUT = Path("data/processed/sg4_final_list.json")

THRESHOLD = 6

with open(CANDIDATES_PATH, encoding="utf-8") as f:
    raw = json.load(f)

if isinstance(raw, dict):
    entries = [{"act": k, **v} for k, v in raw.items()]
else:
    entries = raw

if not entries:
    raise SystemExit(f"{CANDIDATES_PATH} is empty -- nothing to build SG4 from.")

with open(COMBINED_OUT, "w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2, ensure_ascii=False)
print(f"Saved -> {COMBINED_OUT}  ({len(entries)} candidates, full pre-threshold pool)")

sg4_final = [e for e in entries if e.get("combined_score", 0) >= THRESHOLD]

with open(FINAL_OUT, "w", encoding="utf-8") as f:
    json.dump(sg4_final, f, indent=2, ensure_ascii=False)
print(f"Saved -> {FINAL_OUT}  ({len(sg4_final)} Acts, combined_score >= {THRESHOLD})")

print(
    f"\nSG4 finalized: {len(sg4_final)} Acts "
    f"({100 * len(sg4_final) / len(entries):.1f}% of the {len(entries)}-candidate pool)."
)
