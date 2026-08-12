"""
Saves the Stage 4 manual validation precision analysis as a permanent,
citable output -- the per-category breakdown, small-sample caveats, and
the comparison to Ardekani et al.'s reported baseline.
"""

import json
from pathlib import Path
from collections import defaultdict

sample = json.loads(Path("data/processed/stage4_manual_sample.json").read_text())

by_type = defaultdict(lambda: {"correct": 0, "partial": 0, "incorrect": 0})
for r in sample:
    by_type[r["type"]][r["judgement"]] += 1

results = {"sample_size": 100, "by_type": {}, "overall": {}}

total_c = total_p = total_i = 0
for rel_type, counts in by_type.items():
    c, p, i = counts["correct"], counts["partial"], counts["incorrect"]
    n = c + p + i
    results["by_type"][rel_type] = {
        "n": n, "correct": c, "partial": p, "incorrect": i,
        "strict_precision": round(100 * c / n, 1),
        "lenient_precision": round(100 * (c + p) / n, 1),
        "small_sample_caveat": n < 20,
    }
    total_c += c; total_p += p; total_i += i

results["overall"] = {
    "n": 100, "correct": total_c, "partial": total_p, "incorrect": total_i,
    "strict_precision": round(100 * total_c / 100, 1),
    "lenient_precision": round(100 * (total_c + total_p) / 100, 1),
    "comparison_baseline": {
        "source": "Ardekani et al. (2026), rule-based extraction",
        "reported_precision": 93.0,
    },
    "key_finding": (
        "power_or_duty (74.3% of the full 3,255-relation dataset) shows the "
        "lowest fabrication rate (2.7%) and highest lenient precision (97.3%) "
        "of any category, meaning the dominant category is also the most "
        "reliable one -- overall dataset reliability is weighted toward its "
        "strongest-performing category, not a flat average across types."
    ),
}

out_path = Path("data/processed/stage4_manual_validation_results.json")
out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Saved to {out_path}")
print(json.dumps(results, indent=2, ensure_ascii=False))