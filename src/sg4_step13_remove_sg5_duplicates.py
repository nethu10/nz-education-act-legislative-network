"""
sg4_step13_remove_sg5_duplicates.py

Removes SG5's confirmed cross-layer duplicates -- three real Acts,
found across 4 SG5 entries, that are already in SG2 or SG4 under a
different citation form. Confirmed by re-running the (type, year,
number) identifier audit with "status", "subtype" added to the key
-- step12's audit key was missing "status", which produced one false
positive (Public/Local/Private Acts number sequentially in SEPARATE
series, so "Act No 1 of 2000" legitimately exists more than once).
That false positive (Museum of Transport and Technology Act 2000 vs.
Hauraki Gulf Marine Park Act 2000 vs. Tauranga District Council
(Route K Toll) Empowering Act 2000) is gone once status is included;
the three real duplicates below survive the corrected key.

Confirmed duplicates:
  - "Food Hygiene Regulations 1974, Amendment No 1 (SR 1976/268)"
    == SG4's "Food Hygiene Regulations 1974 (SR 1974/169)"
  - "Geothermal Energy Regulations 1961, Amendment No 6" AND
    "Geothermal Energy Regulations 1961, Amendment No 2"
    == SG4's "Geothermal Energy Regulations 1961 (SR 1961/124)"
    (both SG5 fragments duplicate the same already-known Act)
  - "Te Ture Whenua\nMaori/Maori Land Act 1993"
    == SG2's "Te Ture Whenua Maori Act 1993" (Act 1993 No 4)

Reads / writes:
  data/processed/sg5_final_list.json        -- 4 entries removed
  data/processed/sg5_act_identifiers.json   -- same 4 removed
"""
import json
from pathlib import Path

FINAL_LIST_PATH = Path("data/processed/sg5_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg5_act_identifiers.json")

DUPLICATE_ACT_NAMES = {
    "Food Hygiene Regulations 1974, Amendment No\xa01 (SR 1976/268)",
    "Geothermal Energy Regulations 1961, Amendment No 6",
    "Geothermal Energy Regulations 1961, Amendment No\xa02",
    "Te Ture Whenua\nMaori/Maori Land Act 1993",
}

with open(FINAL_LIST_PATH, encoding="utf-8") as f:
    final_list = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

before_final = len(final_list)
before_ids = len(identifiers)

removed_from_final = [e for e in final_list if e["act"] in DUPLICATE_ACT_NAMES]
final_list = [e for e in final_list if e["act"] not in DUPLICATE_ACT_NAMES]
identifiers = [d for d in identifiers if d["act"] not in DUPLICATE_ACT_NAMES]

print("Removed from sg5_final_list.json:")
for e in removed_from_final:
    print(f"  {e['act']!r}  (combined_score {e.get('combined_score')})")

with open(FINAL_LIST_PATH, "w", encoding="utf-8") as f:
    json.dump(final_list, f, indent=2, ensure_ascii=False)
with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(identifiers, f, indent=2, ensure_ascii=False)

print(f"\nsg5_final_list.json: {before_final} -> {len(final_list)}")
print(f"sg5_act_identifiers.json: {before_ids} -> {len(identifiers)}")
print(f"\nSG5 finalized at {len(final_list)} genuinely new Acts "
      f"({before_final} minus {before_final - len(final_list)} confirmed cross-layer duplicates).")

# ---- corrected duplicate audit, for a clean confirmation pass ----
print("\n--- Re-auditing with the corrected key (type, subtype, status, year, number) ---")


def key_of(d):
    return (d.get("type"), d.get("subtype"), d.get("status"), d.get("year"), str(d.get("number")))


by_key = {}
for d in identifiers:
    if not d.get("resolved"):
        continue
    by_key.setdefault(key_of(d), []).append(d["act"])

remaining_dupes = {k: v for k, v in by_key.items() if len(v) > 1}
if remaining_dupes:
    print("Still-duplicated identifiers within SG5 (unexpected -- investigate):")
    for k, names in remaining_dupes.items():
        print(f"  {k}: {names}")
else:
    print("Clean -- no remaining within-SG5 duplicates after the corrected key.")