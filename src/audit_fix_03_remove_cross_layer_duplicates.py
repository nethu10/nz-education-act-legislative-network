"""
audit_fix_03_remove_cross_layer_duplicates.py

Removes the 2 confirmed cross-layer duplicates from SG3, using the
exact raw strings found by audit_fix_02 (both carry the same
NBSP-before-year artifact seen elsewhere: "Act\xa02024" / "Act\xa01998"
instead of a normal space):

  "Pae Ora (Disestablishment of Maori Health Authority) Amendment
  Act\xa02024" -- already an SG2 member (act/public/2024/..., combined_score
  19 there); the SG3 copy (combined_score 7, from 3 SG3 Acts citing it)
  is dropped entirely, not merged -- SG2's score is the correct, single
  record, since this was never really an SG3-stage discovery.

  "Employment Services and Income Support (Integrated Administration)
  Act\xa01998" -- same situation, SG2 combined_score 13 stands, SG3 copy
  (combined_score 30, from 1 SG3 Act) dropped.

Root cause (confirmed via reading sg2_step26's source): the exclusion
check at line 243 ("cand_norm in sg2_names_norm: continue") is correct
in principle, but normalize() never handled NBSP or macrons, so a
citation using the NBSP-variant spelling didn't match against
sg2_names_norm when SG3's candidate pool was first being built, and
slipped through as "new" when it should have been recognized as
already-SG2. This removal is the fix for the 2 instances that actually
happened; sg2_names_norm/normalize() itself doesn't need patching
retroactively since this script removes the bad rows directly, but the
same robustness (macron + NBSP stripping) should go into the
SG4-internal-link-finding script when it's built, to prevent a repeat
at the SG4/SG5 boundary.

Removes from:
  data/processed/sg3_final_list.json
  data/processed/sg3_combined_final_list.json   (if present)
  data/processed/sg3_act_identifiers.json
"""
import json
from pathlib import Path

SG3_FINAL = Path("data/processed/sg3_final_list.json")
SG3_COMBINED = Path("data/processed/sg3_combined_final_list.json")
SG3_IDENTIFIERS = Path("data/processed/sg3_act_identifiers.json")

TARGETS = [
    "Pae Ora (Disestablishment of M\u0101ori Health Authority) Amendment Act\xa02024",
    "Employment Services and Income Support (Integrated Administration) Act\xa01998",
]


def remove_from(path, key="act"):
    if not path.exists():
        print(f"{path}: not found, skipped")
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    before = len(data)
    matched = [d.get(key) for d in data if d.get(key) in TARGETS]
    new_data = [d for d in data if d.get(key) not in TARGETS]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print(f"{path}: {before} -> {len(new_data)} ({before - len(new_data)} removed)")
    for m in matched:
        print(f"    removed: {m!r}")
    return new_data


sg3_after = remove_from(SG3_FINAL)
remove_from(SG3_COMBINED)
identifiers_after = remove_from(SG3_IDENTIFIERS)

if sg3_after is not None:
    print(f"\nSG3 now {len(sg3_after)} Acts.")
if identifiers_after is not None:
    n_resolved = sum(1 for d in identifiers_after if d.get("resolved"))
    print(f"Identifiers: {n_resolved}/{len(identifiers_after)} resolved")
