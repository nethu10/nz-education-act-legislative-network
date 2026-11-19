"""
sg2_check_citation_id_coverage.py

How many of the unique extref ids are needed to cover most of the total
citation volume? This tells us the real resolution workload before
committing to resolving all 4,248 individually.
"""
import json
from pathlib import Path

UNIQUE_IDS_PATH = Path("data/processed/sg2_unique_citation_ids.json")

with open(UNIQUE_IDS_PATH) as f:
    unique_ids = json.load(f)

total = sum(r["count"] for r in unique_ids)
print(f"Total unique ids: {len(unique_ids)}")
print(f"Total occurrences: {total}")
print()

cumulative = 0
milestones = [0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 0.95]
next_milestone_idx = 0

for i, r in enumerate(unique_ids, 1):
    cumulative += r["count"]
    frac = cumulative / total
    while next_milestone_idx < len(milestones) and frac >= milestones[next_milestone_idx]:
        print(f"  {milestones[next_milestone_idx]*100:.0f}% of total occurrences covered by top {i} unique ids")
        next_milestone_idx += 1
    if next_milestone_idx >= len(milestones):
        break

print()
for n in [50, 100, 200, 300, 500, 1000]:
    if n <= len(unique_ids):
        covered = sum(r["count"] for r in unique_ids[:n])
        print(f"  top {n:>4} unique ids cover {covered:>6} / {total} occurrences ({covered/total*100:.1f}%)")