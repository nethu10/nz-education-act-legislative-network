"""
sg2_step29_fix_public_registers_rename.py

Second confirmed rename from the same Family Violence Act 2018 reform,
found by hand the same way as step27's fix:

  Family Violence (Public Registers) Regulations 1998
  [Previous title: Domestic Violence (Public Registers) Regulations 1998]

Identifier confirmed by hand:
  https://legislation.govt.nz/secondary-legislation/pco-drafted/1998/342/en/latest/
  -> secondary-legislation / pco-drafted / 1998 / 342

Same treatment as step27: identifier filled in directly on the existing
SG3 entry (name kept as the historical citation text it was extracted
from). No merge needed -- the sg2_step27 audit already confirmed no
"Family Violence (Public Registers) Regulations 1998" entry exists
anywhere else in the SG-layer lists, so this isn't a hidden duplicate.
"""
import json
from pathlib import Path

SG3_PATH = Path("data/processed/sg3_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")

CONFIRMED_FIX = {
    "act": "Domestic Violence (Public Registers) Regulations 1998",
    "type": "secondary-legislation",
    "subtype": "pco-drafted",
    "status": None,
    "year": 1998,
    "number": 342,
}
CONFIRMED_FIX["url"] = (
    f"https://www.legislation.govt.nz/secondary-legislation/pco-drafted/"
    f"{CONFIRMED_FIX['year']}/{CONFIRMED_FIX['number']}/en/latest/"
)
CONFIRMED_FIX["xml_url"] = (
    f"https://legislation.govt.nz/secondary-legislation/pco-drafted/"
    f"{CONFIRMED_FIX['year']}/{CONFIRMED_FIX['number']}/en/latest.xml"
)

with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

by_act = {d["act"]: d for d in identifiers}
target = CONFIRMED_FIX["act"]

if target not in by_act:
    raise SystemExit(f"WARNING: {target!r} not found in {IDENTIFIERS_PATH} -- nothing to fix.")

entry = by_act[target]
entry.update({k: v for k, v in CONFIRMED_FIX.items() if k != "act"})
entry["resolved"] = True
entry["resolved_via"] = "manual_confirmed_rename"
entry["note"] = (
    "Confirmed by hand via legislation.govt.nz search: current title is "
    "'Family Violence (Public Registers) Regulations 1998' (Family Violence Act 2018 "
    "reform). SG3 entry name kept as the historical citation text; identifier "
    "filled in directly (sg2_step29)."
)

with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(identifiers, f, indent=2, ensure_ascii=False)

n_resolved = sum(1 for d in identifiers if d.get("resolved"))
print(f"FIXED: {target!r} -> secondary-legislation/pco-drafted/1998/342")
print(f"Saved -> {IDENTIFIERS_PATH}")
print(f"Overall: {n_resolved}/{len(sg3)} resolved")