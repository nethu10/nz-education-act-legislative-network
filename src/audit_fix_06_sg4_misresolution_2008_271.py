"""
audit_fix_06_sg4_misresolution_2008_271.py

Fixes a misresolution found during the SG4 filename-collision audit
(data/processed/sg4_collision_full_audit.md, pair #55, 2008_405.xml).

"Fisheries (Challenger Area Commercial Fishing) Amendment Regulations 2008"
and "Fisheries (Challenger Area Commercial Fishing) Amendment Regulations
(No 2) 2008" are two DIFFERENT real SR instruments (confirmed live: made
25 Aug 2008 vs 20 Oct 2008, 20 vs 13 sections, completely different
section content) -- not a duplicate pair. But both ended up resolved to
the same identifier (year=2008, number=405) in sg4_act_identifiers.json,
which is the (No 2) instrument's real number. The non-"(No 2)" one's real
number is 405 -> WRONG; its real SR number is 271, confirmed via the live
title_autocomplete endpoint and by fetching
https://legislation.govt.nz/secondary-legislation/pco-drafted/2008/271/en/latest.xml
directly (sr.no="271", title matches exactly, well-formed XML, 112,373
bytes).

This is not a dedup (both documents are real and both belong in SG4) --
it's a one-sided re-resolution of a single identifier entry.

Updates (in data/processed/sg4_act_identifiers.json):
  "Fisheries (Challenger Area Commercial Fishing) Amendment Regulations 2008"
    number: "405" -> "271"
    url:     .../2008/405/en/latest/  -> .../2008/271/en/latest/
    xml_url: .../2008/405/en/latest.xml -> .../2008/271/en/latest.xml

Leaves the "(No 2) 2008" entry untouched (its 405 resolution is correct).

The actual XML content for 2008/271 was fetched live and saved separately
to data/raw/sg4_targets/2008_271.xml (new file -- 2008_405.xml already
correctly holds the (No 2) instrument's content, confirmed by its
sr.no="405" attribute and title before this fix ran).
"""
import json
from pathlib import Path

IDENTIFIERS = Path("data/processed/sg4_act_identifiers.json")

TARGET_ACT = "Fisheries (Challenger Area Commercial Fishing) Amendment Regulations 2008"
WRONG_NUMBER = "405"
RIGHT_NUMBER = "271"

with open(IDENTIFIERS, encoding="utf-8") as f:
    data = json.load(f)

fixed = 0
for d in data:
    if d.get("act") == TARGET_ACT and d.get("number") == WRONG_NUMBER:
        old_url = d["url"]
        old_xml_url = d["xml_url"]
        d["number"] = RIGHT_NUMBER
        d["url"] = d["url"].replace(f"/2008/{WRONG_NUMBER}/", f"/2008/{RIGHT_NUMBER}/")
        d["xml_url"] = d["xml_url"].replace(f"/2008/{WRONG_NUMBER}/", f"/2008/{RIGHT_NUMBER}/")
        d["resolved_via"] = "audit_fix_06_misresolution_correction"
        print(f"Fixed: {d['act']!r}")
        print(f"  number:  {WRONG_NUMBER} -> {RIGHT_NUMBER}")
        print(f"  url:     {old_url} -> {d['url']}")
        print(f"  xml_url: {old_xml_url} -> {d['xml_url']}")
        fixed += 1

if fixed == 0:
    raise SystemExit("ERROR: target entry not found or already fixed -- nothing changed.")
elif fixed > 1:
    raise SystemExit(f"ERROR: matched {fixed} entries, expected exactly 1 -- aborting without writing.")

with open(IDENTIFIERS, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Sanity: confirm the (No 2) entry is untouched and still correct
# NOTE: the real act string uses a NON-BREAKING SPACE between "No" and "2"
# (same NBSP-variant issue seen elsewhere in this pipeline) -- match on that.
no2 = [d for d in data if d.get("act") == "Fisheries (Challenger Area Commercial Fishing) Amendment Regulations (No 2) 2008"]
assert len(no2) == 1, f"expected 1 match, got {len(no2)} -- check for NBSP/variant issues"
assert no2[0]["number"] == "405"
print(f"\n(No 2) entry confirmed unchanged: number={no2[0]['number']}, url={no2[0]['url']}")
print(f"\n{IDENTIFIERS} written. 1 entry corrected.")
