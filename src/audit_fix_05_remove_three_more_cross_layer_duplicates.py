"""
audit_fix_05_remove_three_more_cross_layer_duplicates.py

Removes 3 more confirmed cross-layer duplicates from SG3, found 2026-10-04
via a systematic normalized-name audit across all layer pairs (SG1<->SG2,
SG1<->SG3, SG2<->SG3) while writing sg3_step02_build_typed_edges.py --
the correctness check against published sg1_typed_*/sg2_typed_* surfaced
~97 missing pairs, traced to these 3 names resolving into the wrong group
(whichever layer was processed last in the member-building loop silently
overwrote name_norm_to_group for the shared name).

All 3 are confirmed the SAME real document as their SG1/SG2 counterpart --
not just matching URL/year/number (as previously checked for the Frontal
Impact case, audit_fix_04), but this time MD5-identical raw XML content
in both layers' targets/ directories:

  SG1 "Legislation Act 2019 (2019 No 58)" == SG3 "Legislation Act 2019"
    data/raw/sg1_targets/2019_58.xml == data/raw/sg3_targets/2019_58.xml
    (md5 054bbe2663907ecdedddb8461db744f9, both)

  SG2 "Financial Markets Conduct Act 2013" == SG3 "Financial Markets Conduct Act 2013"
    data/raw/sg2_targets/2013_69.xml == data/raw/sg3_targets/2013_69.xml
    (md5 45abfd8a434561538fb1f2535237af8f, both)

  SG2 "Territorial Sea, Contiguous Zone, and Exclusive Economic Zone Act 1977"
  == SG3 "Territorial Sea, Contiguous Zone, and Exclusive Economic Zone Act 1977"
    data/raw/sg2_targets/1977_28.xml == data/raw/sg3_targets/1977_28.xml
    (md5 d43fad9f34975c3c27a234f427b0c0fb, both)

All 3 SG3 identifier entries share resolved_via="schedule_of_parent" --
unlike audit_fix_03's 2 NBSP-variant dupes (which slipped through sg2_
step26's "already in SG2" normalize() check due to an unstripped NBSP) and
audit_fix_04's 1 word-order-variant dupe, these 3 bypassed that dedup check
entirely by entering sg3_act_identifiers.json through a LATER resolution
path (schedule-of-parent-Act backward lookup, likely added while resolving
SG4 candidates) that never re-checked against the already-finalized SG1/
SG2 name sets. Worth building that re-check into the SG4 pipeline before
it's built, same note audit_fix_03 already left for this exact scenario.

The upper-layer (SG1/SG2) entry is kept as canonical in every case; the
SG3 copy is dropped entirely, not merged.

Removes from:
  data/processed/sg3_final_list.json
  data/processed/sg3_combined_final_list.json   (if present)
  data/processed/sg3_act_identifiers.json

Does NOT delete the now-orphaned duplicate XML files in data/raw/
sg3_targets/ (2019_58.xml, 2013_69.xml, 1977_28.xml) -- those are exact
byte-for-byte duplicates of files already in sg1_targets/ or sg2_targets/,
same situation as the 2 stray files found earlier this session, which
Nethmi deleted from the Mac herself. Flagging their exact paths for the
same treatment rather than deleting them here.
"""
import json
from pathlib import Path

SG3_FINAL = Path("data/processed/sg3_final_list.json")
SG3_COMBINED = Path("data/processed/sg3_combined_final_list.json")
SG3_IDENTIFIERS = Path("data/processed/sg3_act_identifiers.json")

TARGETS = [
    "Legislation Act 2019",
    "Financial Markets Conduct Act 2013",
    "Territorial Sea, Contiguous Zone, and Exclusive Economic Zone Act 1977",
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

print(
    "\nSG3 cross-layer duplicate count is now 6 found/removed total across this "
    "project (audit_fix_03's 2 NBSP-variant + audit_fix_04's 1 word-order-variant "
    "+ this script's 3 exact/bare-name-variant dupes).\n"
    "ORPHANED XML FILES TO DELETE FROM THE MAC (exact duplicates, safe to delete, "
    "same as the earlier 2 stray files):\n"
    "  data/raw/sg3_targets/2019_58.xml\n"
    "  data/raw/sg3_targets/2013_69.xml\n"
    "  data/raw/sg3_targets/1977_28.xml"
)
