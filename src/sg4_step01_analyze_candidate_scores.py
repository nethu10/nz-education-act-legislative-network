"""
sg4_step01_analyze_candidate_scores.py

First step of building SG4, mirroring how SG1/SG2/SG3's own thresholds
(>=6, >=3, >=6 respectively) were each chosen: an evidence-based look at
the combined_score distribution across the SG4 candidate pool, not a
threshold picked in advance. Source: data/processed/sg3_new_candidates_seen.json
(4,635 raw candidates spotted while extracting SG3-internal links --
every reference target that fell OUTSIDE seed+SG1+SG2+SG3, set aside
untouched at the time by sg2_step26).

Uses the same field-name auto-detection as make_sg3_internal_diagram.py
(I don't have direct visibility into this file's exact structure) --
if the guessed key names are wrong it prints the real structure and
stops, so we can fix it in one pass, same as before.

This is diagnostic only -- it writes nothing. It reports:
  - total raw candidate count
  - combined_score distribution (percentiles)
  - a threshold-sweep table: how many candidates survive at each cutoff
  - the top 20 candidates by score, as a sanity check that high scorers
    look like real, substantive Acts rather than extraction noise

That's the evidence to have on hand -- and to show your supervisor if
useful -- when picking SG4's cutoff, the same way SG1/SG2/SG3's cutoffs
were each justified from their own layer's distribution rather than
reused from the previous layer.
"""
import json
from pathlib import Path

CANDIDATES_PATH = Path("data/processed/sg3_new_candidates_seen.json")

with open(CANDIDATES_PATH, encoding="utf-8") as f:
    raw = json.load(f)

if isinstance(raw, dict):
    entries = [{"act": k, **v} for k, v in raw.items()]
else:
    entries = raw

if not entries:
    raise SystemExit(f"{CANDIDATES_PATH} is empty -- nothing to analyze.")

sample = entries[0]
name_key = next((k for k in ("act", "name", "target", "title") if k in sample), None)
score_key = next((k for k in ("combined_score", "score", "total_score", "weight") if k in sample), None)
from_key = next((k for k in ("linked_from", "from_acts", "sources", "citing_acts", "from") if k in sample), None)

if not (name_key and score_key):
    raise SystemExit(
        "Couldn't recognize the field names in sg3_new_candidates_seen.json.\n"
        f"First entry looks like:\n{json.dumps(sample, indent=2, ensure_ascii=False)[:800]}\n\n"
        "Paste this back and I'll fix the key names above."
    )

print(
    f"Using fields: name={name_key!r}, score={score_key!r}"
    + (f", from={from_key!r}" if from_key else " (no 'linked_from'-style field found -- ok, not needed here)")
)
print(f"\n{len(entries)} total SG4 candidates (raw, pre-threshold)\n")

scores = [e.get(score_key, 0) for e in entries]
scores_sorted = sorted(scores, reverse=True)


def pct(p):
    idx = min(len(scores_sorted) - 1, int(len(scores_sorted) * p))
    return scores_sorted[idx]


print("Score distribution:")
print(f"  max:            {scores_sorted[0]}")
print(f"  top 10% (p90):  {pct(0.10)}")
print(f"  top 25% (p75):  {pct(0.25)}")
print(f"  median:         {pct(0.50)}")
print(f"  bottom 25%:     {pct(0.75)}")
print(f"  min:            {scores_sorted[-1]}")

print(
    "\nThreshold sweep -- candidates surviving at each cutoff "
    "(for comparison: SG1 used >=6, SG2 used >=3, SG3 used >=6):"
)
for cutoff in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30, 40, 50]:
    n = sum(1 for s in scores if s >= cutoff)
    pct_of_total = 100 * n / len(scores)
    print(f"  >= {cutoff:>3}: {n:>5} candidates ({pct_of_total:5.1f}% of pool)")

print(
    "\nTop 20 candidates by score (sanity check -- do these look like "
    "real, substantive Acts relevant to the network, or extraction noise?):"
)
for e in sorted(entries, key=lambda e: e.get(score_key, 0), reverse=True)[:20]:
    print(f"  {e[name_key]}  (score {e.get(score_key, 0)})")
