"""
Removes the 10 confirmed self-referential entries, then systematically
checks every remaining Act for the same "bulk mechanical event"
fingerprint found in Secondary Legislation Act 2021 -- most of that
Act's amendment instances concentrated on a single date -- rather than
assuming only one Act has this pattern.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

SELF_REFERENTIAL = {
    "Education and Training (Vocational Education and Training System) Amendment Act 2025",
    "Education and Training Amendment Act 2022", "Education and Training Amendment Act 2024",
    "Education and Training Amendment Act 2023", "Education (Name Change for NZIST) Order 2020",
    "Education and Training Amendment Act 2025", "Education and Training Amendment Act 2021",
    "Education and Training (Early Childhood Education Reform) Amendment Act 2025",
    "Education and Training (Teaching Council Fees, Levies, and Costs) Amendment Act 2021",
    "Education and Training (Grants\u2014Budget Measures) Amendment Act 2021",
}

ranking = json.loads(Path("data/processed/sg1_combined_ranking.json").read_text())
cleaned = [r for r in ranking if r["act"] not in SELF_REFERENTIAL]
print(f"Removed {len(ranking) - len(cleaned)} self-referential entries")
print(f"Remaining: {len(cleaned)} Acts")

# Check every remaining Act's incoming amendments for single-date concentration
raw_incoming = json.loads(Path("data/processed/amendment_records.json").read_text())
by_act_dates = defaultdict(list)
for r in raw_incoming:
    act = r.get("amending_act")
    date = r.get("date")
    if act and date:
        by_act_dates[act].append(date)

print("\nChecking all Acts with 5+ incoming instances for single-date concentration:")
bulk_event_acts = []
for act, dates in by_act_dates.items():
    if len(dates) < 5:
        continue
    date_counts = Counter(dates)
    top_date, top_count = date_counts.most_common(1)[0]
    concentration = top_count / len(dates)
    if concentration >= 0.8:
        bulk_event_acts.append((act, len(dates), top_date, concentration))
        print(f"  {act}: {len(dates)} instances, {concentration*100:.0f}% on {top_date}")

print(f"\nTotal Acts showing this bulk-event fingerprint: {len(bulk_event_acts)}")

Path("data/processed/sg1_ranking_cleaned.json").write_text(
    json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nCleaned ranking (self-referential removed) saved to data/processed/sg1_ranking_cleaned.json")
print("Bulk-event Acts NOT yet removed from this file -- reviewing them together first.")