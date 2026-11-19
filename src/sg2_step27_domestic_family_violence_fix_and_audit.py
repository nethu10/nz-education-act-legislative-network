"""
sg2_step27_domestic_family_violence_fix_and_audit.py

Nethmi manually confirmed via the legislation.govt.nz search box that
"Domestic Violence (General) Regulations 1996" is not a search-ranking
miss -- it's a genuine RENAME. The site's own autocomplete shows:

  Family Violence (General) Regulations 1996
  [Previous title: Domestic Violence (General) Regulations 1996]

Identifier confirmed by hand:
  https://legislation.govt.nz/secondary-legislation/pco-drafted/1996/150/en/latest/
  -> secondary-legislation / pco-drafted / 1996 / 150

This is the Family Violence Act 2018 reform (which replaced the old
Domestic Violence Act 1995) renaming related subordinate legislation --
the same class of issue as every other RENAME_MAP entry, just never
caught because search-term matching against the OLD name in the SG3
citation text doesn't surface a page now titled under the NEW name.

Two things this script does:

  1. Fixes the one confirmed entry: writes the identifier directly onto
     "Domestic Violence (General) Regulations 1996" in
     sg3_act_identifiers.json (resolved_via="manual_confirmed_rename").
     The SG3 Act NAME is left as-is (matching the historical citation text
     it was extracted from) -- only the identifier is filled in, same
     approach as step24's VDAM fix.

  2. Audits every SG-layer list (SG1, SG2, SG3 final + the pre-threshold
     SG3 pool) for any entry whose name contains "violence" -- catching
     two things we can't otherwise see without looking at the real data:
       a) whether "Family Violence (Public Registers) Regulations 1998"
          (the likely sibling rename) or any other Family-Violence-named
          entry already exists SEPARATELY somewhere in the pool -- which
          would mean the old-name and new-name versions of the same
          document are sitting as two different candidates (a hidden
          duplicate, the same class of problem sg2_step20 fixed for
          Court/Courts), not just a missing identifier
       b) whether "Domestic Violence Act 1995" / "Family Violence Act
          2018" (the parent Acts, not just their regulations) appear
          anywhere and under which name

Nothing is merged automatically here -- this only reports what it finds,
so any real duplicate this surfaces can be reviewed and merged deliberately
(mirroring step20's approach) rather than guessed at.
"""
import json
from pathlib import Path

SG1_PATH = Path("data/processed/sg1_final_list.json")
SG2_PATH = Path("data/processed/sg2_final_list.json")
SG3_PATH = Path("data/processed/sg3_final_list.json")
SG3_COMBINED_PATH = Path("data/processed/sg3_combined_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")

CONFIRMED_FIX = {
    "act": "Domestic Violence (General) Regulations 1996",
    "type": "secondary-legislation",
    "subtype": "pco-drafted",
    "status": None,
    "year": 1996,
    "number": 150,
}
CONFIRMED_FIX["url"] = (
    f"https://www.legislation.govt.nz/secondary-legislation/pco-drafted/"
    f"{CONFIRMED_FIX['year']}/{CONFIRMED_FIX['number']}/en/latest/"
)
CONFIRMED_FIX["xml_url"] = (
    f"https://legislation.govt.nz/secondary-legislation/pco-drafted/"
    f"{CONFIRMED_FIX['year']}/{CONFIRMED_FIX['number']}/en/latest.xml"
)

# ---- Part 1: apply the confirmed fix ----
with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

by_act = {d["act"]: d for d in identifiers}
target = CONFIRMED_FIX["act"]

if target in by_act:
    entry = by_act[target]
    entry.update({k: v for k, v in CONFIRMED_FIX.items() if k != "act"})
    entry["resolved"] = True
    entry["resolved_via"] = "manual_confirmed_rename"
    entry["note"] = (
        "Confirmed by hand via legislation.govt.nz search: current title is "
        "'Family Violence (General) Regulations 1996' (Family Violence Act 2018 "
        "reform). SG3 entry name kept as the historical citation text; identifier "
        "filled in directly (sg2_step27)."
    )
    with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
        json.dump(identifiers, f, indent=2, ensure_ascii=False)
    n_resolved = sum(1 for d in identifiers if d.get("resolved"))
    print(f"FIXED: {target!r} -> secondary-legislation/pco-drafted/1996/150")
    print(f"Saved -> {IDENTIFIERS_PATH}")
    print(f"Overall: {n_resolved}/{len(sg3)} resolved\n")
else:
    print(f"WARNING: {target!r} not found in {IDENTIFIERS_PATH} -- nothing to fix.\n")

# ---- Part 2: audit for the same rename pattern elsewhere ----
print("=" * 70)
print("Auditing all SG-layer lists for 'violence' in the Act name...")
print("=" * 70)

sources = [
    ("SG1 final", SG1_PATH, "combined_score"),
    ("SG2 final", SG2_PATH, "combined_score"),
    ("SG3 final (901, post-threshold)", SG3_PATH, "combined_score"),
    ("SG3 combined pool (pre-threshold, ALL candidates)", SG3_COMBINED_PATH, "combined_score"),
]

for label, path, score_key in sources:
    if not path.exists():
        print(f"\n[{label}] -- file not found, skipping: {path}")
        continue
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    hits = [c for c in data if "violence" in c.get("act", "").lower()]
    print(f"\n[{label}] -- {len(hits)} entr{'y' if len(hits)==1 else 'ies'} matching 'violence':")
    for c in sorted(hits, key=lambda c: -c.get(score_key, 0)):
        print(f"  {c.get(score_key, '?'):>4}  {c['act']!r}")

print("\n" + "=" * 70)
print("If 'Family Violence (...)' and 'Domestic Violence (...)' versions of the")
print("SAME instrument both appear above as separate entries, that's a hidden")
print("duplicate needing a merge (same pattern as sg2_step20's Court/Courts fix) --")
print("paste this whole output back so we can confirm and build that merge properly.")p