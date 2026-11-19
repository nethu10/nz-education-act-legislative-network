"""
audit_fix_08_cross_layer_duplicates_missed_in_sg4_audit.py

While building the SG4 filename-collision audit (data/processed/
sg4_collision_full_audit.md), the "66 collisions" turned out to have
been computed across the COMBINED SG2+SG3+SG4 identifier sets, not
within SG4 alone. Properly separating them by which layer(s) each name
actually lives in revealed:

  - 14 pairs are genuine intra-SG4 collisions (handled separately by
    sg4_filenames.py's SG4_FILENAME_OVERRIDES).
  - 26 pairs are two different real documents that merely share a
    (year, number) by coincidence ACROSS DIFFERENT LAYERS -- since each
    layer stores its raw XML in its own directory (sg2_targets/,
    sg3_targets/, sg4_targets/), these were never a real collision at
    all. No action needed.
  - 21 pairs are cross-layer DUPLICATES that the earlier SG2<->SG3 audit
    (audit_fix_03/04/05) simply missed, plus one SG3<->SG4 and one
    SG3<->SG4 case -- the same real document independently rediscovered
    under a different name string in a later layer. This script removes
    those 21 duplicate entries.

For 19 of the 21, the earlier layer (SG2 or SG3) has the canonical name
and the later layer's copy is dropped -- consistent with audit_fix_03/
04/05's "earlier-published layer is canonical" rule.

Two cases (2020_40, 1995_31) are the OPPOSITE: the fragment/short-form
string happens to sit in the EARLIER layer (SG3) while the real,
correctly-named parent document sits in the LATER layer (SG4). "Earlier
layer wins" is the wrong rule there -- what actually matters is keeping
the real canonical title, so SG3's fragment/short-form entry is dropped
and SG4's correct entry is kept, even though that means removing from
the earlier layer this time:
  - 2020_40: SG3 has "Schedule 8 of the Public Service Act 2020" (a
    fragment, not a real document) while SG4 independently has the real
    "Public Service Act 2020". Drop SG3's fragment.
  - 1995_31: SG3 has "Agriculture and Fisheries (Restructuring) Act
    1995" (missing the "Ministry of" prefix) while SG4 has the correct
    "Ministry of Agriculture and Fisheries (Restructuring) Act 1995"
    (confirmed canonical via live fetch). Drop SG3's short variant.
"""
import json
from pathlib import Path

# (layer_to_drop_from, exact act name to drop, one-line reason)
REMOVALS = [
    ("sg3", "Schedule 1 of the Financial Markets Authority Act 2011",
     "fragment of SG2's Financial Markets Authority Act 2011"),
    ("sg3", "Schedule 1 of the Resource Management Act 1991",
     "fragment of SG2's Resource Management Act 1991"),
    ("sg3", "Transit New Zealand Act 1989",
     "previous title of SG2's Government Roading Powers Act 1989 (user-confirmed)"),
    ("sg3", "Schedule 7 of the Local Government Act 2002",
     "fragment of SG2's Local Government Act 2002"),
    ("sg3", "Summary Proceedings Act 1957 (1957 No 87) (RS Vol 9, p 583)",
     "citation-suffix variant of SG2's Summary Proceedings Act 1957"),
    ("sg3", "Personal and Property Rights Act 1988",
     "short-form variant of SG2's Protection of Personal and Property Rights Act 1988"),
    ("sg3", "Births, Deaths, and Marriages Registration Act 1995",
     "previous title of SG2's Births, Deaths, Marriages, and Relationships Registration Act 1995"),
    ("sg3", "Local Government Act 1974 (1974 No 66) (RS Vol 25, p 1)",
     "citation-suffix variant of SG2's Local Government Act 1974"),
    ("sg3", "Securities Act 1978 (1978 No 103) (RS Vol 15, p 533)",
     "citation-suffix variant of SG2's Securities Act 1978"),
    ("sg3", "Justice (Restructuring) Act 1995",
     "short-form variant of SG2's Department of Justice (Restructuring) Act 1995"),
    ("sg3", "Ombudsmen Act 1975 (1975 No 9) (RS Vol 21, p 657)",
     "citation-suffix variant of SG2's Ombudsmen Act 1975"),
    ("sg3", "Persons with Disabilities) Act 2008",
     "truncated fragment of SG2's Disability (...Persons with Disabilities) Act 2008 (user-confirmed anchor)"),
    ("sg3", "Parliament) Amendment Act 2002",
     "truncated fragment of SG2's Remuneration Authority (Members of Parliament) Amendment Act 2002"),
    ("sg3", "Support Workers (Pay Equity) Settlements Act 2017 (previously named the "
            "Care and Support Workers (Pay Equity) Settlement Act 2017)",
     "same document as SG2's Care and Support Workers (Pay Equity) Settlement Act 2017 "
     "(user-confirmed rename); kept the clean grammatical SG2 title"),
    ("sg3", "New Zealand Act 2002",
     "truncated fragment of SG2's Sport and Recreation New Zealand Act 2002"),
    ("sg3", "Child, Youth and Family Services Act 1999",
     "short-form variant of SG2's Department of Child, Youth and Family Services Act 1999"),
    ("sg3", "Children Act 2004",
     "truncated fragment of SG2's Care of Children Act 2004"),
    ("sg3", "Reserve Bank of New Zealand Act 1989",
     "previous title of SG2's Banking (Prudential Supervision) Act 1989 (live autocomplete-confirmed)"),
    ("sg4", "Te Ture mō Te Reo Māori 2016",
     "short-form substring of SG3's Te Ture mō Te Reo Māori 2016/the Māori Language Act 2016"),
    ("sg3", "Schedule 8 of the Public Service Act 2020",
     "fragment, not a real document -- SG4 independently has the real Public Service Act 2020"),
    ("sg3", "Agriculture and Fisheries (Restructuring) Act 1995",
     "drops 'Ministry of' prefix -- SG4 has the correct Ministry of Agriculture and "
     "Fisheries (Restructuring) Act 1995 (confirmed canonical via live fetch)"),
]

assert len(REMOVALS) == 21, f"expected 21 removals, got {len(REMOVALS)}"

FILES_BY_LAYER = {
    "sg2": ["sg2_final_list.json", "sg2_combined_final_list.json", "sg2_act_identifiers.json"],
    "sg3": ["sg3_final_list.json", "sg3_combined_final_list.json", "sg3_act_identifiers.json"],
    "sg4": ["sg4_final_list.json", "sg4_combined_final_list.json", "sg4_act_identifiers.json"],
}


def remove_one(path, name, key="act"):
    if not path.exists():
        return None, 0
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    before = len(data)
    new_data = [d for d in data if (d.get(key) if isinstance(d, dict) else d) != name]
    removed = before - len(new_data)
    if removed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
    return len(new_data), removed


for layer, name, reason in REMOVALS:
    print(f"\n[{layer}] DROP {name!r}")
    print(f"  reason: {reason}")
    total_removed = 0
    for fname in FILES_BY_LAYER[layer]:
        path = Path("data/processed") / fname
        new_len, removed = remove_one(path, name)
        if new_len is None:
            print(f"  {fname}: not found, skipped")
        else:
            print(f"  {fname}: removed={removed}, now {new_len} entries")
            total_removed += removed
    if total_removed == 0:
        print(f"  *** WARNING: {name!r} was not found/removed in ANY file for layer {layer}! ***")

print("\nDone -- 21 cross-layer duplicate removals applied.")
