"""
sg4_step05_remove_bad_sg4_candidates.py

Removes two confirmed classes of bad SG4 candidates found by
sg4_step04_audit_unresolved.py:

1. Stray section/clause pseudo-candidates (25 total: "Section 9",
   "Clause 42", etc.) -- internal cross-references mis-captured as
   standalone citation targets during upstream citation extraction.
   9 of these had actually RESOLVED to unrelated real
   legislation.govt.nz URLs (false-positive text match), which would
   have planted bogus nodes with fake outgoing citations into
   SG4-internal-link-finding if left in.

2. "Crimes Act 1961 (1961 No 43) (RS Vol 1, p 635)" -- an already-
   known Act (present in SG1/SG2/SG3 as "Crimes Act 1961") that
   slipped through as a false "new" SG4 candidate because its
   double-stacked citation suffix broke the CITE_PATTERN regex used
   during exclusion checking. Same bug family as the NBSP/macron
   cross-layer duplicates already fixed in SG3.

Removes from:
  data/processed/sg4_final_list.json
  data/processed/sg4_combined_final_list.json   (if present)
  data/processed/sg4_act_identifiers.json
"""
import json
import re
from pathlib import Path

SG4_FINAL = Path("data/processed/sg4_final_list.json")
SG4_COMBINED = Path("data/processed/sg4_combined_final_list.json")
SG4_IDENTIFIERS = Path("data/processed/sg4_act_identifiers.json")

SECTION_CLAUSE_RE = re.compile(r"^(section|clause)\s+\d+[a-z]*$", re.IGNORECASE)
CRIMES_ACT_DUPLICATE = "Crimes Act 1961 (1961 No 43) (RS Vol 1, p 635)"


def is_bad(act_name):
    name = (act_name or "").strip()
    if SECTION_CLAUSE_RE.match(name):
        return True
    if name == CRIMES_ACT_DUPLICATE:
        return True
    return False


def remove_from(path, key="act"):
    if not path.exists():
        print(f"{path}: not found, skipped")
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    before = len(data)
    matched = [d.get(key) for d in data if is_bad(d.get(key))]
    new_data = [d for d in data if not is_bad(d.get(key))]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print(f"{path}: {before} -> {len(new_data)} ({before - len(new_data)} removed)")
    for m in matched:
        print(f"    removed: {m!r}")
    return new_data


final_after = remove_from(SG4_FINAL)
remove_from(SG4_COMBINED)
identifiers_after = remove_from(SG4_IDENTIFIERS)

if final_after is not None:
    print(f"\nSG4 now {len(final_after)} Acts.")
if identifiers_after is not None:
    n_resolved = sum(1 for d in identifiers_after if d.get("resolved"))
    print(f"Identifiers: {n_resolved}/{len(identifiers_after)} resolved")

print(
    "\nExpected: SG4 1161 -> 1135 (26 removed: 25 pseudo-candidates + "
    "1 already-known duplicate). Resolved should drop 1104 -> ~1095 "
    "(the 9 falsely-resolved pseudo-candidates are gone). Unresolved "
    "should drop 57 -> ~40 (16 unresolved pseudo-candidates + the "
    "Crimes Act duplicate removed), leaving genuine corpus-"
    "availability gaps plus a handful worth a manual retry "
    "(trailing-period, wrong-year, circumflex cases)."
)