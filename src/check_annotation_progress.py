import json
from collections import Counter
from pathlib import Path

sample = json.loads(Path("data/processed/stage4_manual_sample.json").read_text())
judged = [r for r in sample if r["judgement"]]

counts = Counter(r["judgement"] for r in judged)
print(f"Judged so far: {len(judged)} / {len(sample)}")
for label, count in counts.most_common():
    print(f"  {label}: {count} ({100*count/len(judged):.1f}%)")