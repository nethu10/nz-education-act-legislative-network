"""
sg4_step07_analyze_sg5_candidate_scores.py

Diagnostic only -- writes nothing. Mirrors sg4_step01_analyze_candidate_scores.py
one layer up: loads sg4_new_candidates_seen.json (the 1,044 candidates
set aside for SG5) and reports the score distribution, a threshold-sweep
table, and the top candidates, so the SG5 cutoff can be chosen the same
evidence-based way SG1-SG4's were (rather than assumed to also land on 6).
"""
import json
from pathlib import Path

CANDIDATES_PATH = Path("data/processed/sg4_new_candidates_seen.json")

with open(CANDIDATES_PATH, encoding="utf-8") as f:
    candidates = json.load(f)

scores = sorted((c["combined_score"] for c in candidates), reverse=True)
n = len(scores)

def percentile(p):
    idx = min(n - 1, int(round((1 - p / 100) * (n - 1))))
    return scores[idx]

print(f"Total SG5 candidates: {n}")
print(f"Min: {scores[-1]}  Max: {scores[0]}")
print(f"Median (p50): {percentile(50)}")
print(f"p75: {percentile(75)}   p90: {percentile(90)}   p95: {percentile(95)}\n")

print("Threshold sweep -- candidates surviving at each cutoff:")
for cutoff in range(1, 51):
    surviving = sum(1 for s in scores if s >= cutoff)
    marker = "  <-- matches SG1/SG3/SG4 precedent" if cutoff == 6 else ""
    print(f"  >= {cutoff:>3}: {surviving:>5} candidates{marker}")

print("\nTop 20 candidates by score (sanity check):")
for c in sorted(candidates, key=lambda c: -c["combined_score"])[:20]:
    print(f"  {c['act']}  (score {c['combined_score']}, from {len(c['linked_from'])} SG4 Acts)")