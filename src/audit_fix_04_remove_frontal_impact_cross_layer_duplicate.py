"""
audit_fix_04_remove_frontal_impact_cross_layer_duplicate.py

Removes a 3rd confirmed cross-layer duplicate from SG3 -- same bug class
as audit_fix_03's 2 NBSP-variant duplicates, this time caused by word-order
instead of a stripped character:

  SG2 entry (sg2_act_identifiers.json, resolved_via="manual_lookup"):
    "Land Transport Rule 32006/1: Frontal Impact 2001"
  SG3 entry (sg3_act_identifiers.json, resolved_via="land_transport_rule_v2"):
    "Land Transport Rule: Frontal Impact 2001 (32006/1)"

Confirmed same real document (2026-10-04, found while re-investigating the
SG2 "420/421" XML gap -- see data/processed/sg2_no_xml_gap_investigation_
findings.md): both entries resolve to year=2025, number=275499, and the
identical legislation.govt.nz URL path
(.../secondary-legislation/agency-drafted/~2025/~275499/en/latest/, module
only the "www." prefix and tilde-formatting differ). Independently
discovered twice via two different code paths (SG2's manual lookup vs
SG3's automated land_transport_rule_v2 resolver), landing under two
different name strings -- exactly the mechanism that produced audit_fix_03's
2 duplicates, just a different normalization gap.

The SG2 entry is kept as canonical: it is the one correctly carrying both
recovered incoming edges (Immigration Act 2009 -> this Rule; Land Transport
Management Amendment Act 2008 -> this Rule; see sg2_step36_build_typed_
edges_v2.py). The SG3 copy is dropped entirely, not merged, same approach
as audit_fix_03.

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
    "Land Transport Rule: Frontal Impact 2001 (32006/1)",
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
    "\nSG3 cross-layer duplicate count is now 3 found/removed total "
    "(audit_fix_03's 2 NBSP-variant dupes + this 1 word-order-variant dupe). "
    "No local XML file needs deleting for this one -- it never had any "
    "(xml_available=False, agency-drafted gap), so there is no orphaned "
    "sg3_targets/ file left behind this time."
)
