"""
sg4_step12_fix_sg5_unresolved.py

Resolves SG5's 6 previously-unresolved candidates using identifiers
confirmed directly against legislation.govt.nz -- three via a live
WebSearch investigation, three via your own manual check of the
site's Advanced Search "Title contains" box -- then runs an
identifier-level duplicate audit: grouping every resolved SG5 Act by
its real-world (type, year, number) tuple rather than by name-string
similarity, since two very differently-worded citations of the same
Act resolve to the identical tuple once looked up. That catches
duplicates no amount of text normalization would.

Confirmed identifiers for the 6:

  1. "Biosecurity (...Pest Management STRATEGY) Order 1998" (SR
     1998/179, score 90) -- confirmed renamed to "...PLAN) Order
     1998". Your own check of the Advanced Search box shows it
     directly: "...Plan) Order 1998 [Previous title: ...Strategy)
     Order 1998]".
  2. "Biosecurity (...American Foulbrood...STRATEGY) Order 1998" (SR
     1998/260, score 70) -- same rename pattern, same confirmation.
  3. "Biosecurity (American Foulbrood-Apiary and Beekeeper Levy)
     Order 2003" (SR 2003/283, score 6) -- ALSO a confirmed previous
     title (correcting my own first guess that this was an
     extraction error): "...Beekeeper Levy) Order 2003 [Previous
     title: ...-Apiary and Beekeeper Levy) Order 2003]".
  4. "Food Hygiene Regulations 1974, Amendment No 1 (SR 1976/268)"
     (score 33) -- you confirmed this resolves to the SAME page as
     the principal Food Hygiene Regulations 1974 (SR 1974/169), an
     anchor within it (#DLM42658). Not a separate instrument.
  5 & 6. "Geothermal Energy Regulations 1961, Amendment No 6" (score
     30) and "...Amendment No 2" (score 13) -- both confirmed to
     resolve to the SAME principal Geothermal Energy Regulations
     1961 page (SR 1961/124). Two fragment-citations of one Act, not
     two different Acts.

Reads / writes:
  data/processed/sg5_act_identifiers.json  -- the 6 filled in
  data/processed/sg{1,2,3,4}_act_identifiers.json -- read-only, if
    present, to check for duplicates against earlier layers too
    (skipped with a note if a file doesn't exist)

This script does NOT rewrite sg5_final_list.json. It reports which
entries are true duplicates (same identifier, different citation
text) so you can decide how to merge them -- summing scores and
linked_from -- with the full picture in front of you, rather than
silently restructuring a list you've already finalized.
"""
import json
from pathlib import Path

IDENTIFIERS_PATH = Path("data/processed/sg5_act_identifiers.json")
EARLIER_IDENTIFIER_PATHS = {
    "SG1": Path("data/processed/sg1_act_identifiers.json"),
    "SG2": Path("data/processed/sg2_act_identifiers.json"),
    "SG3": Path("data/processed/sg3_act_identifiers.json"),
    "SG4": Path("data/processed/sg4_act_identifiers.json"),
}

CONFIRMED = {
    "Biosecurity (National Bovine Tuberculosis Pest Management Strategy) Order 1998 (SR 1998/179)": {
        "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
        "year": 1998, "number": "179",
        "url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1998/179/en/latest/",
        "xml_url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1998/179/en/latest.xml",
        "resolved_via": "sg5_rename_correction",
        "searched_as": "Biosecurity (National Bovine Tuberculosis Pest Management Plan) Order 1998",
    },
    "Biosecurity (National American Foulbrood Pest Management Strategy) Order 1998 (SR 1998/260)": {
        "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
        "year": 1998, "number": "260",
        "url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1998/260/en/latest/",
        "xml_url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1998/260/en/latest.xml",
        "resolved_via": "sg5_rename_correction",
        "searched_as": "Biosecurity (National American Foulbrood Pest Management Plan) Order 1998",
    },
    "Biosecurity (American Foulbrood\u2014Apiary and Beekeeper Levy) Order 2003 (SR 2003/283)": {
        "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
        "year": 2003, "number": "283",
        "url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/2003/283/en/latest/",
        "xml_url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/2003/283/en/latest.xml",
        "resolved_via": "sg5_rename_correction",
        "searched_as": "Biosecurity (American Foulbrood\u2014Beekeeper Levy) Order 2003",
    },
    "Food Hygiene Regulations 1974, Amendment No\xa01 (SR 1976/268)": {
        "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
        "year": 1974, "number": "169",
        "url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1974/169/en/latest/#DLM42658",
        "xml_url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1974/169/en/latest.xml",
        "resolved_via": "sg5_fragment_of_principal_regulation",
        "searched_as": None,
    },
    "Geothermal Energy Regulations 1961, Amendment No 6": {
        "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
        "year": 1961, "number": "124",
        "url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1961/124/en/latest/",
        "xml_url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1961/124/en/latest.xml",
        "resolved_via": "sg5_fragment_of_principal_regulation",
        "searched_as": None,
    },
    "Geothermal Energy Regulations 1961, Amendment No\xa02": {
        "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
        "year": 1961, "number": "124",
        "url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1961/124/en/latest/",
        "xml_url": "https://legislation.govt.nz/secondary-legislation/pco-drafted/1961/124/en/latest.xml",
        "resolved_via": "sg5_fragment_of_principal_regulation",
        "searched_as": None,
    },
}

with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)
by_act = {d["act"]: d for d in identifiers}

print("--- Filling in the 6 confirmed identifiers ---")
n_filled = 0
for act_name, fields in CONFIRMED.items():
    if act_name not in by_act:
        print(f"  SKIP (exact string not found in identifiers file): {act_name!r}")
        continue
    entry = by_act[act_name]
    entry.update(fields)
    entry["resolved"] = True
    n_filled += 1
    print(f"  {act_name!r}\n    -> {fields['year']}/{fields['number']}")

with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(list(by_act.values()), f, indent=2, ensure_ascii=False)
print(f"\n{n_filled}/6 filled in. Saved -> {IDENTIFIERS_PATH}")

still_unresolved = [d for d in by_act.values() if not d.get("resolved")]
print(f"SG5 now: {len(by_act) - len(still_unresolved)}/{len(by_act)} resolved, {len(still_unresolved)} unresolved.")

# ---- Identifier-level duplicate audit ----
print("\n--- Duplicate audit: grouping resolved Acts by (type, year, number) ---")


def key_of(d):
    return (d.get("type"), d.get("year"), str(d.get("number")))


sg5_by_key = {}
for d in by_act.values():
    if not d.get("resolved"):
        continue
    k = key_of(d)
    sg5_by_key.setdefault(k, []).append(d["act"])

dupes_within_sg5 = {k: v for k, v in sg5_by_key.items() if len(v) > 1}
if dupes_within_sg5:
    print("Within SG5 itself, these citation strings resolve to the SAME real Act:")
    for k, names in dupes_within_sg5.items():
        print(f"  {k} :")
        for n in names:
            print(f"    - {n!r}")
    print(
        "\n  -> These should be merged into ONE sg5_final_list.json entry (sum combined_score "
        "and linked_from) rather than counted as separate Acts."
    )
else:
    print("No within-SG5 duplicates found.")

print("\nChecking against earlier layers' resolved identifiers...")
earlier_by_key = {}
for label, path in EARLIER_IDENTIFIER_PATHS.items():
    if not path.exists():
        print(f"  {label}: {path} not found, skipping")
        continue
    with open(path, encoding="utf-8") as f:
        earlier = json.load(f)
    for d in earlier:
        if not d.get("resolved"):
            continue
        earlier_by_key.setdefault(key_of(d), []).append((label, d["act"]))
    print(f"  {label}: loaded {sum(1 for d in earlier if d.get('resolved'))} resolved identifiers")

cross_layer_dupes = []
for k, sg5_names in sg5_by_key.items():
    if k in earlier_by_key:
        cross_layer_dupes.append((k, sg5_names, earlier_by_key[k]))

if cross_layer_dupes:
    print("\nSG5 entries that are ALREADY in an earlier layer (same real Act, different citation text):")
    for k, sg5_names, earlier_hits in cross_layer_dupes:
        print(f"  {k} :")
        for n in sg5_names:
            print(f"    SG5:  {n!r}")
        for label, n in earlier_hits:
            print(f"    {label}:  {n!r}")
    print(
        "\n  -> These should almost certainly be REMOVED from sg5_final_list.json -- they're "
        "not new discoveries, they're an Act you already have, cited differently."
    )
else:
    print("No cross-layer duplicates found among the resolved SG5 Acts.")