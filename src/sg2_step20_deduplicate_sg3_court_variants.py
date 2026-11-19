"""
sg2_step20_deduplicate_sg3_court_variants.py

Fixes 3 cases where the SG3 candidate pool admitted both the correct
official name and a "Courts" (plural) mis-citation of the same real
document -- found by scanning the 904 finalized SG3 Acts for exact
Courts/Court variant pairs. Unlike the SG2 duplicate-identifier issue
(sg2_step13), this isn't an amendment-side/citation-side name-matching
gap -- all 6 entries have real signal on BOTH sides, meaning some source
Acts' citation/amendment text genuinely uses the (incorrect) plural
"Courts" when cross-referencing these instruments. There is no such
document as "District Courts Rules 2014" or "Family Courts Act 1980" --
only the singular official titles exist -- so this is a straightforward
merge onto the correct name, not a rename-map judgement call.

  Family Court Act 1980     <- Family Courts Act 1980      (64 + 61 = 125)
  District Court Rules 2014 <- District Courts Rules 2014  (25 + 11 = 36)
  Family Court Rules 2002   <- Family Courts Rules 2002    (20 +  6 = 26)

All 6 individual entries already score >= 6 (the SG3 threshold), so this
merge doesn't change which Acts qualify for SG3 -- it just corrects 3
understated combined_scores and drops 904 -> 901 total SG3 Acts (3 fewer
rows, no data lost, since every real reference is folded into its
canonical Act rather than discarded).

Applies the merge to:
  data/processed/sg3_final_list.json           -- combined_score/linked_from merged
  data/processed/sg3_combined_final_list.json  -- same, for the full pre-threshold pool

Does NOT yet touch sg3_act_identifiers.json (need that file to confirm
whether Family Court Act 1980 / Family Courts Act 1980 resolved to the
same (year, number) -- expected confirmation, not yet verified) or
sg3_internal_links.json (doesn't exist yet).
"""
import json
from pathlib import Path

SG3_FINAL_PATH = Path("data/processed/sg3_final_list.json")
SG3_COMBINED_PATH = Path("data/processed/sg3_combined_final_list.json")

MERGE_PAIRS = [
    ("Family Court Act 1980", "Family Courts Act 1980"),
    ("District Court Rules 2014", "District Courts Rules 2014"),
    ("Family Court Rules 2002", "Family Courts Rules 2002"),
]
name_to_canonical = {variant: canonical for canonical, variant in MERGE_PAIRS}


def merge_file(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"{path}: {len(data)} entries before")

    merged = {}
    for c in data:
        name = c["act"]
        canonical = name_to_canonical.get(name, name)
        if canonical not in merged:
            merged[canonical] = {
                "act": canonical,
                "amendment_score": 0,
                "citation_score": 0,
                "combined_score": 0,
                "linked_from": set(),
            }
        merged[canonical]["amendment_score"] += c.get("amendment_score", 0)
        merged[canonical]["citation_score"] += c.get("citation_score", 0)
        merged[canonical]["combined_score"] += c.get("combined_score", 0)
        merged[canonical]["linked_from"].update(c.get("linked_from", []))

    new_data = []
    for d in merged.values():
        d["linked_from"] = sorted(d["linked_from"])
        new_data.append(d)
    new_data.sort(key=lambda c: -c["combined_score"])

    print(f"{path}: {len(new_data)} entries after (merged {len(data) - len(new_data)})")
    for canonical, variant in MERGE_PAIRS:
        c = merged.get(canonical)
        if c:
            print(f"  {canonical!r}: combined_score now {c['combined_score']}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print()
    return new_data


merge_file(SG3_FINAL_PATH)
merge_file(SG3_COMBINED_PATH)

print("Done. Note: sg3_act_identifiers.json was NOT touched by this script --")
print("attach it so the Family Court Act 1980 / Family Courts Act 1980 same-identifier")
print("confirmation can be checked and the identifiers file cleaned up the same way.")