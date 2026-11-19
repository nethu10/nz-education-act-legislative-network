"""
sg2_step24_manual_map_vdam_2016.py

One-off, manual resolution for the single judgement-call case flagged in
step23: "Land Transport Rule: Vehicle Dimensions and Mass 2002 (41001)".
The 2002 rule under code 41001 has since been replaced by a 2016 rule
reusing the same code -- Nethmi decided (2026-09-23) to map the SG3 entry
to the current 2016 replacement rather than leave it unresolved.

This searches legislation.govt.nz directly for the replacement rule's own
title ("Vehicle Dimensions and Mass 2016") using the same corrected
multi-pattern regex as step21/22/23, and if found, writes it onto the
*existing* "...2002 (41001)" entry in sg3_act_identifiers.json (the SG3
Act name itself is NOT renamed -- only its identifier is filled in) with
resolved_via="manual_map_to_2016_replacement" so this deliberate
substitution stays visible and auditable, distinct from every other
resolved_via tag which reflects an actual search match on the name as
written.

Does nothing to any other entry. If the search doesn't turn up the 2016
rule either, nothing is written and the entry stays unresolved -- rerun
with a hand-supplied identifier instead if that happens (print a fetched
HTML snippet to check by eye).
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

SG3_PATH = Path("data/processed/sg3_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")

TARGET_ACT = "Land Transport Rule: Vehicle Dimensions and Mass 2002 (41001)"
REPLACEMENT_QUERY = "Land Transport Rule: Vehicle Dimensions and Mass 2016"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

RESULT_LINK_RE = re.compile(
    r'href="(?P<path>'
    r'/(?P<type1>act|regulation|rule|order|notice)/(?P<status1>public|private|local|imperial)/(?P<year1>\d{4})/(?P<number1>\d+)/en/latest/[^"]*'
    r'|/secondary-legislation/(?P<subtype2>pco-drafted)/(?P<year2>\d{4})/(?P<number2>\d+)/en/latest/[^"]*'
    r'|/secondary-legislation/(?P<subtype3>agency-drafted)/~(?P<year3>\d{4})/~(?P<number3>\d+)/en/latest/[^"]*'
    r')"'
)


def search(name, timeout=25):
    url = f"https://www.legislation.govt.nz/items/?search_term={quote(name)}&per_page=5"
    return requests.get(url, headers=HEADERS, timeout=timeout)


def parse_first_result(html):
    m = RESULT_LINK_RE.search(html)
    if not m:
        return None
    gd = m.groupdict()
    url = f"https://www.legislation.govt.nz{gd['path']}"

    if gd["year1"]:
        doc_type, status, year, number = gd["type1"], gd["status1"], int(gd["year1"]), gd["number1"]
        return {
            "type": doc_type, "status": status, "year": year, "number": number, "url": url,
            "xml_url": f"https://legislation.govt.nz/{doc_type}/{status}/{year}/{number}/en/latest.xml",
        }
    if gd["year2"]:
        year, number = int(gd["year2"]), gd["number2"]
        return {
            "type": "secondary-legislation", "subtype": "pco-drafted", "status": None,
            "year": year, "number": number, "url": url,
            "xml_url": f"https://legislation.govt.nz/secondary-legislation/pco-drafted/{year}/{number}/en/latest.xml",
        }
    if gd["year3"]:
        year, number = int(gd["year3"]), gd["number3"]
        return {
            "type": "secondary-legislation", "subtype": "agency-drafted", "status": None,
            "year": year, "number": number, "url": url,
            "xml_url": f"https://legislation.govt.nz/secondary-legislation/agency-drafted/~{year}/~{number}/en/latest.xml",
        }
    return None


with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

by_act = {d["act"]: d for d in identifiers}
if TARGET_ACT not in by_act:
    raise SystemExit(f"'{TARGET_ACT}' not found in {IDENTIFIERS_PATH} -- nothing to do.")

print(f"Searching for the 2016 replacement: {REPLACEMENT_QUERY!r}\n")
r = search(REPLACEMENT_QUERY)
parsed = parse_first_result(r.text)

if not parsed:
    print("No match found -- entry left unresolved. Nothing written.")
else:
    entry = by_act[TARGET_ACT]
    entry.update(parsed)
    entry["resolved"] = True
    entry["resolved_via"] = "manual_map_to_2016_replacement"
    entry["searched_as"] = REPLACEMENT_QUERY
    entry["note"] = (
        "SG3 candidate cites the 2002 rule (code 41001); manually mapped to its "
        "2016 replacement (same code) per Nethmi's decision on 2026-09-23, since "
        "the 2002 instrument is no longer in force."
    )
    with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
        json.dump(identifiers, f, indent=2, ensure_ascii=False)

    n_total_resolved = sum(1 for d in identifiers if d.get("resolved"))
    print(f"FIXED: {TARGET_ACT!r} -> {parsed['type']}/{parsed.get('subtype', parsed.get('status'))}/"
          f"{parsed['year']}/{parsed['number']}")
    print(f"Saved -> {IDENTIFIERS_PATH}")
    print(f"Overall: {n_total_resolved}/{len(sg3)} resolved")