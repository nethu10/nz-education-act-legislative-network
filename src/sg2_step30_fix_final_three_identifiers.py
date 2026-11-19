"""
sg2_step30_fix_final_three_identifiers.py

Three more manually confirmed identifiers, found the same way as
step27/step29 (legislation.govt.nz search box, checked by hand):

  Housing Restructuring and Tenancy Matters (Appeals) Regulations 2000
    -> now "Public and Community Housing Management (Appeals)
       Regulations 2000" -- the SAME Housing Restructuring and Tenancy
       Matters -> Public and Community Housing Management reform already
       known from the RENAME_MAP (it renamed the parent Act; this
       confirms it renamed the Regulations too).
    -> secondary-legislation/pco-drafted/2000/212

  United Nations Sanctions (Cote d'Ivoire) Regulations 2005
    -> same name, no rename -- just a URL the automated search couldn't
       surface (most likely the apostrophe/accented-character combination
       again, same root cause as the Children's Commissioner Act fix).
    -> secondary-legislation/pco-drafted/2005/339

  Resource Management (Approval of Transit New Zealand as Requiring
  Authority) Order 1992
    -> now "Resource Management (Approval of New Zealand Transport
       Agency as Requiring Authority) Order 1992" -- Transit New Zealand
       was renamed/reorganised into the NZ Transport Agency in 2008.
    -> secondary-legislation/pco-drafted/1992/348

Same treatment as step27/step29: identifier filled in directly on each
existing SG3 entry (name kept as the historical citation text it was
extracted from). No merge needed for the two renames -- neither
"Public and Community Housing Management (Appeals) Regulations 2000" nor
"Resource Management (Approval of New Zealand Transport Agency as
Requiring Authority) Order 1992" appeared in the sg2_step27 'violence'-
style audit scope, but their parent-Act renames are already long-
established in the pipeline's RENAME_MAP with no duplicate-entry issues,
so the same is assumed to hold here.

After this: only 2 of the original 7 unresolved Acts remain --
Health Reforms (Transitional Provisions) Act 1993 and
Transport (Driving Hours Logbook Exemption) Notice 2003.
"""
import json
from pathlib import Path

SG3_PATH = Path("data/processed/sg3_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")

CONFIRMED_FIXES = [
    {
        "act": "Housing Restructuring and Tenancy Matters (Appeals) Regulations 2000",
        "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
        "year": 2000, "number": 212,
        "note": (
            "Confirmed by hand: current title is 'Public and Community Housing "
            "Management (Appeals) Regulations 2000' -- same reform that renamed the "
            "parent Act (already in RENAME_MAP). SG3 entry name kept as the "
            "historical citation text; identifier filled in directly (sg2_step30)."
        ),
    },
    {
        "act": "United Nations Sanctions (Côte d'Ivoire) Regulations 2005",
        "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
        "year": 2005, "number": 339,
        "note": (
            "Confirmed by hand -- same name, no rename; automated search couldn't "
            "surface the URL (accented character / apostrophe combination). "
            "Identifier filled in directly (sg2_step30)."
        ),
    },
    {
        "act": "Resource Management (Approval of Transit New Zealand as Requiring Authority) Order 1992",
        "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
        "year": 1992, "number": 348,
        "note": (
            "Confirmed by hand: current title is 'Resource Management (Approval of "
            "New Zealand Transport Agency as Requiring Authority) Order 1992' -- "
            "Transit New Zealand was renamed/reorganised into NZTA in 2008. SG3 "
            "entry name kept as the historical citation text; identifier filled in "
            "directly (sg2_step30)."
        ),
    },
]

with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

by_act = {d["act"]: d for d in identifiers}

for fix in CONFIRMED_FIXES:
    target = fix["act"]
    if target not in by_act:
        print(f"WARNING: {target!r} not found in {IDENTIFIERS_PATH} -- skipping.")
        continue

    entry = by_act[target]
    year, number = fix["year"], fix["number"]
    entry.update({
        "type": fix["type"],
        "subtype": fix["subtype"],
        "status": fix["status"],
        "year": year,
        "number": number,
        "url": f"https://www.legislation.govt.nz/secondary-legislation/pco-drafted/{year}/{number}/en/latest/",
        "xml_url": f"https://legislation.govt.nz/secondary-legislation/pco-drafted/{year}/{number}/en/latest.xml",
    })
    entry["resolved"] = True
    entry["resolved_via"] = "manual_confirmed"
    entry["note"] = fix["note"]
    print(f"FIXED: {target!r} -> secondary-legislation/pco-drafted/{year}/{number}")

with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(identifiers, f, indent=2, ensure_ascii=False)

n_resolved = sum(1 for d in identifiers if d.get("resolved"))
print(f"\nSaved -> {IDENTIFIERS_PATH}")
print(f"Overall: {n_resolved}/{len(sg3)} resolved ({n_resolved/len(sg3):.1%})")