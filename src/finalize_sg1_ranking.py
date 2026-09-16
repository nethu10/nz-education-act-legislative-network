"""
Final pass: confirms the nature of the two newly-flagged bulk-event
Acts, removes all confirmed bulk-mechanical-event Acts from the SG1
ranking (documented, not silently deleted), and produces the real,
final ranked distribution for choosing SG1's cutoff.
"""

import json
from pathlib import Path
from collections import Counter

raw_incoming = json.loads(Path("data/processed/amendment_records.json").read_text())

print("=== Sample of what Public Service Act 2020 actually changed ===")
psa_samples = [r for r in raw_incoming if r.get("amending_act") == "Public Service Act 2020"][:5]
for r in psa_samples:
    print(f"  {r.get('full_text', '')}")

print("\n=== Sample of Employment Relations (Pay Deductions for Partial Strikes) Amendment Act 2025 ===")
erpd_samples = [r for r in raw_incoming if r.get("amending_act") == "Employment Relations (Pay Deductions for Partial Strikes) Amendment Act 2025"][:5]
for r in erpd_samples:
    print(f"  {r.get('full_text', '')}")

# Confirmed bulk-mechanical-event Acts: single-date, system-wide administrative
# sweeps that don't reflect an ongoing, substantive relationship with education
# policy -- documented and excluded from SG1 ranking, not silently discarded.
BULK_EVENT_ACTS = {
    "Secondary Legislation Act 2021",
    "Public Service Act 2020",
    "Employment Relations (Pay Deductions for Partial Strikes) Amendment Act 2025",
}

cleaned = json.loads(Path("data/processed/sg1_ranking_cleaned.json").read_text())
final = [r for r in cleaned if r["act"] not in BULK_EVENT_ACTS]
excluded = [r for r in cleaned if r["act"] in BULK_EVENT_ACTS]

print(f"\n\nExcluded as bulk mechanical events (documented, not deleted):")
for r in excluded:
    print(f"  {r['combined_score']:4d}  {r['act']}")

print(f"\nFinal SG1 candidate pool: {len(final)} Acts (down from {len(cleaned)})")

print(f"\n--- Top 30 of the final, cleaned ranking ---")
for i, r in enumerate(final[:30], 1):
    print(f"{i:3d}. {r['combined_score']:3d}  (out:{r['outgoing_amendments']}, in:{r['incoming_amendments']}, cite:{r['citations']})  {r['act']}")

score_counts = Counter(r["combined_score"] for r in final)
print(f"\nHow many Acts have exactly N combined connections (top of distribution):")
for score in sorted(score_counts.keys(), reverse=True)[:20]:
    print(f"  {score}: {score_counts[score]} Act(s)")

Path("data/processed/sg1_ranking_final.json").write_text(
    json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8"
)
Path("data/processed/sg1_excluded_bulk_events.json").write_text(
    json.dumps(excluded, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved final ranking and excluded-list separately -- both kept, nothing silently lost.")