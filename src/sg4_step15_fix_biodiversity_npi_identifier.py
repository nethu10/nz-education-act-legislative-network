"""
sg4_step15_fix_biodiversity_npi_identifier.py

Fixes one broken identifier in sg5_act_identifiers.json: "National
Policy Statement for Indigenous Biodiversity 2023" resolved to a
year/number combo whose XML fetch returned a 500 (the one failure in
sg4_step14's run). Manually confirmed the correct identifier on
legislation.govt.nz directly:
  https://legislation.govt.nz/secondary-legislation/agency-drafted/~2024/~340459/en/latest/

Corrected to type=secondary-legislation, subtype=agency-drafted,
year=2024, number="340459" -- same schema/xml_url construction as
every other agency-drafted entry (per parse_first_result() in
sg4_step03_resolve_identifiers.py).

After this runs, re-run sg4_step14_find_sg5_internal_links.py again --
the other 46 Acts will hit the local XML cache
(data/raw/sg5_targets/*.xml) and skip straight past, so only this one
Act needs a fresh network fetch.
"""
import json
from pathlib import Path

IDENTIFIERS_PATH = Path("data/processed/sg5_act_identifiers.json")
TARGET_NAME = "National Policy Statement for Indigenous Biodiversity 2023"

YEAR = 2024
NUMBER = "340459"

with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

found = False
for d in identifiers:
    if d.get("act") == TARGET_NAME:
        print("Current (broken) entry:")
        print(json.dumps(d, indent=2, ensure_ascii=False))

        d.clear()
        d.update({
            "act": TARGET_NAME,
            "resolved": True,
            "type": "secondary-legislation",
            "subtype": "agency-drafted",
            "status": None,
            "year": YEAR,
            "number": NUMBER,
            "url": f"https://www.legislation.govt.nz/secondary-legislation/agency-drafted/~{YEAR}/~{NUMBER}/en/latest/whole.html",
            "xml_url": f"https://legislation.govt.nz/secondary-legislation/agency-drafted/~{YEAR}/~{NUMBER}/en/latest.xml",
            "resolved_via": "manual_fix_500_error",
            "searched_as": None,
        })

        print("\nCorrected to:")
        print(json.dumps(d, indent=2, ensure_ascii=False))
        found = True
        break

if not found:
    raise SystemExit(f"Couldn't find {TARGET_NAME!r} in {IDENTIFIERS_PATH} -- check the exact act name.")

with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(identifiers, f, indent=2, ensure_ascii=False)

print(f"\nSaved -> {IDENTIFIERS_PATH}")
