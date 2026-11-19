"""
audit_fix_01_merge_duplicates.py

Fixes the encoding/macron duplicates and the cross-layer duplicate
found by audit_sg1_sg2_sg3_completeness.py (2026-09-23), before any of
this propagates further into SG4.

THREE DISTINCT ISSUES, THREE DISTINCT FIXES:

1. Non-breaking-space duplicates (extraction artifact, not a real
   naming difference) -- the same Act got inserted twice because one
   occurrence had a regular space and the other had U+00A0 (NBSP,
   likely from an HTML &nbsp; that didn't collapse to a normal space):
     SG2: "COVID-19 Response (Further Management Measures) Legislation
          Act (No 2) 2020"
     SG3: "Maori Trustee Amendment Act 2009"  <- this is SG3's #1 hub
          "Infrastructure (Amendments Relating to Utilities Access)
          Act 2010"
   Fix: merge into ONE row (regular-space spelling), SUMMING
   combined_score -- both rows were tracking the same real citations,
   split across two duplicate entries, so summing recovers the true
   total instead of leaving it artificially undercounted on each half.

2. Genuine macron-encoding duplicates -- same Act, one copy missing
   its macron(s):
     SG3: "Maori Trustee Act 1953" / "Māori Trustee Act 1953"
          "Ngai Tahu Claims Settlement Act 1998" / "Ngāi Tahu Claims
          Settlement Act 1998"
   Fix: same merge approach, keeping the WITH-MACRON spelling as
   canonical (the correct official form), summing combined_score.

3. Cross-layer duplicates -- two Acts that are already SG2 members
   also got independently picked up and promoted into SG3:
     "Pae Ora (Disestablishment of Maori Health Authority) Amendment
     Act 2024"
     "Employment Services and Income Support (Integrated
     Administration) Act 1998"
   These shouldn't exist as SG3 rows at all -- by construction, SG3
   candidates are supposed to be NEW (outside seed+SG1+SG2). Fix:
   REMOVE the SG3 copy entirely (SG2's row and score stand as the
   correct, single record) rather than merge, since merging would
   incorrectly inflate SG2's score with SG3-stage citation weight for
   something that was never really an SG3-stage discovery.

Before merging/removing anything, prints each pair's resolved
identifier (type/year/number) side by side as a sanity check that
they really are the same underlying document -- same diligence as
step25's Court/Courts merge.

Writes updated:
  data/processed/sg2_final_list.json
  data/processed/sg2_act_identifiers.json
  data/processed/sg3_final_list.json
  data/processed/sg3_combined_final_list.json   (if present)
  data/processed/sg3_act_identifiers.json

IMPORTANT -- this changes SG3's membership (899 -> fewer), so
sg3_internal_links.json / sg3_new_candidates_seen.json (built from the
old 899-Act list) and everything built from them
(sg4_final_list.json, sg4_combined_final_list.json) are now stale.
After this runs, re-run in order:
  1. sg2_step26_find_sg3_internal_links.py   (fresh, against the
     corrected SG3 list -- the XML cache in data/raw/sg3_targets/ is
     still valid and will be reused for anything unaffected, so this
     should be much faster than the first run)
  2. sg4_step02_finalize_sg4.py
  3. sg4_step03_resolve_identifiers.py        (good timing -- this
     hadn't been run yet against the old data, so no wasted work)
"""
import json
from pathlib import Path

SG2_FINAL = Path("data/processed/sg2_final_list.json")
SG2_IDENTIFIERS = Path("data/processed/sg2_act_identifiers.json")
SG3_FINAL = Path("data/processed/sg3_final_list.json")
SG3_COMBINED = Path("data/processed/sg3_combined_final_list.json")
SG3_IDENTIFIERS = Path("data/processed/sg3_act_identifiers.json")

MERGE_PAIRS = [
    ("SG2", "COVID-19 Response (Further Management Measures) Legislation Act (No 2) 2020",
            "COVID-19 Response (Further Management Measures) Legislation Act (No\xa02) 2020"),
    ("SG3", "M\u0101ori Trustee Amendment Act 2009", "M\u0101ori Trustee Amendment Act\xa02009"),
    ("SG3", "Infrastructure (Amendments Relating to Utilities Access) Act 2010",
            "Infrastructure (Amendments Relating to Utilities Access) Act\xa02010"),
    ("SG3", "M\u0101ori Trustee Act 1953", "Maori Trustee Act 1953"),
    ("SG3", "Ng\u0101i Tahu Claims Settlement Act 1998", "Ngai Tahu Claims Settlement Act 1998"),
]

CROSS_LAYER_REMOVE_FROM_SG3 = [
    "Pae Ora (Disestablishment of Maori Health Authority) Amendment Act 2024",
    "Employment Services and Income Support (Integrated Administration) Act 1998",
]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def by_act(entries):
    return {e["act"]: e for e in entries if isinstance(e, dict) and "act" in e}


def identifiers_snapshot(id_by_act, name):
    d = id_by_act.get(name)
    if not d:
        return "no identifier entry found"
    return (f"{d.get('type')}/{d.get('subtype', d.get('status'))}/"
            f"{d.get('year')}/{d.get('number')} (resolved={d.get('resolved')})")


sg2 = load(SG2_FINAL)
sg2_ids = load(SG2_IDENTIFIERS) if SG2_IDENTIFIERS.exists() else []
sg3 = load(SG3_FINAL)
sg3_combined = load(SG3_COMBINED) if SG3_COMBINED.exists() else None
sg3_ids = load(SG3_IDENTIFIERS) if SG3_IDENTIFIERS.exists() else []

layer_final = {"SG2": sg2, "SG3": sg3}
layer_ids = {"SG2": sg2_ids, "SG3": sg3_ids}

print("=" * 70)
print("MERGE PAIRS -- identifier sanity check before merging")
print("=" * 70)
for layer, canonical, dup in MERGE_PAIRS:
    ids_map = by_act(layer_ids[layer])
    print(f"\n[{layer}] {canonical!r}")
    print(f"   canonical -> {identifiers_snapshot(ids_map, canonical)}")
    print(f"   duplicate -> {identifiers_snapshot(ids_map, dup)}  ({dup!r})")

print("\n" + "=" * 70)
print("APPLYING MERGES")
print("=" * 70)

for layer, canonical, dup in MERGE_PAIRS:
    final_list = layer_final[layer]
    fmap = by_act(final_list)
    if canonical not in fmap or dup not in fmap:
        print(f"  !! [{layer}] SKIPPED -- couldn't find both rows for "
              f"{canonical!r} / {dup!r} (already merged, or names shifted)")
        continue
    canon_entry = fmap[canonical]
    dup_entry = fmap[dup]
    old_score = canon_entry.get("combined_score", 0)
    dup_score = dup_entry.get("combined_score", 0)
    canon_entry["combined_score"] = old_score + dup_score
    layer_final[layer] = [e for e in final_list if e.get("act") != dup]
    print(f"  [{layer}] merged {dup!r} into {canonical!r}: "
          f"combined_score {old_score} + {dup_score} = {canon_entry['combined_score']}")

    ids_map = by_act(layer_ids[layer])
    if dup in ids_map:
        layer_ids[layer] = [d for d in layer_ids[layer] if d.get("act") != dup]
        print(f"           also removed duplicate identifier row for {dup!r}")

print("\n" + "=" * 70)
print("REMOVING CROSS-LAYER DUPLICATES FROM SG3 (already counted as SG2 members)")
print("=" * 70)

sg3_current = layer_final["SG3"]
for name in CROSS_LAYER_REMOVE_FROM_SG3:
    before = len(sg3_current)
    sg3_current = [e for e in sg3_current if e.get("act") != name]
    removed = before - len(sg3_current)
    print(f"  {'REMOVED' if removed else 'NOT FOUND'}: {name!r}")
layer_final["SG3"] = sg3_current

sg3_ids_current = layer_ids["SG3"]
for name in CROSS_LAYER_REMOVE_FROM_SG3:
    sg3_ids_current = [d for d in sg3_ids_current if d.get("act") != name]
layer_ids["SG3"] = sg3_ids_current

if sg3_combined is not None:
    before = len(sg3_combined)
    dup_names_sg3 = {dup for layer, canon, dup in MERGE_PAIRS if layer == "SG3"}
    drop_set = dup_names_sg3 | set(CROSS_LAYER_REMOVE_FROM_SG3)
    sg3_combined = [e for e in sg3_combined if e.get("act") not in drop_set]
    print(f"\n  sg3_combined_final_list.json: {before} -> {len(sg3_combined)} "
          f"(dropped the same duplicate/cross-layer rows)")

save(SG2_FINAL, layer_final["SG2"])
save(SG2_IDENTIFIERS, layer_ids["SG2"])
save(SG3_FINAL, layer_final["SG3"])
save(SG3_IDENTIFIERS, layer_ids["SG3"])
if sg3_combined is not None:
    save(SG3_COMBINED, sg3_combined)

print("\n" + "=" * 70)
print("FINAL COUNTS")
print("=" * 70)
print(f"  SG2: {len(sg2)} -> {len(layer_final['SG2'])}")
print(f"  SG3: {len(sg3)} -> {len(layer_final['SG3'])}")

print("\n" + "=" * 70)
print("NEXT STEPS -- SG3's membership changed, so anything built from the old")
print("899-Act list is stale and needs re-running in this order:")
print("  1. sg2_step26_find_sg3_internal_links.py  (fresh, against the corrected list)")
print("  2. sg4_step02_finalize_sg4.py")
print("  3. sg4_step03_resolve_identifiers.py")
print("=" * 70)