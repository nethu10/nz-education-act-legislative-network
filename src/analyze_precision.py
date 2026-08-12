"""
Stage 4, Part 2 analysis: breaks the manual validation results down by
relation type (since the sample was stratified), and reports precision
under both a strict (correct only) and lenient (correct + partial)
framing -- rather than collapsing three genuinely different outcomes
into one blended number.
"""

import json
from pathlib import Path
from collections import defaultdict

sample = json.loads(Path("data/processed/stage4_manual_sample.json").read_text())

by_type = defaultdict(lambda: {"correct": 0, "partial": 0, "incorrect": 0})
for r in sample:
    by_type[r["type"]][r["judgement"]] += 1

print("=" * 70)
print("PRECISION BY RELATION TYPE")
print("=" * 70)
print(f"{'Type':<22}{'n':>4}{'Correct':>10}{'Partial':>10}{'Incorrect':>11}{'Strict %':>10}{'Lenient %':>11}")

total_c = total_p = total_i = 0
for rel_type, counts in sorted(by_type.items(), key=lambda x: -(x[1]['correct']+x[1]['partial']+x[1]['incorrect'])):
    c, p, i = counts["correct"], counts["partial"], counts["incorrect"]
    n = c + p + i
    strict = 100 * c / n if n else 0
    lenient = 100 * (c + p) / n if n else 0
    print(f"{rel_type:<22}{n:>4}{c:>10}{p:>10}{i:>11}{strict:>9.1f}%{lenient:>10.1f}%")
    total_c += c; total_p += p; total_i += i

n_total = total_c + total_p + total_i
print("-" * 70)
strict_overall = 100 * total_c / n_total
lenient_overall = 100 * (total_c + total_p) / n_total
print(f"{'OVERALL':<22}{n_total:>4}{total_c:>10}{total_p:>10}{total_i:>11}{strict_overall:>9.1f}%{lenient_overall:>10.1f}%")

print("\n" + "=" * 70)
print("FOR COMPARISON: Ardekani et al. (2026) reported rule-based precision: 93%")
print("=" * 70)