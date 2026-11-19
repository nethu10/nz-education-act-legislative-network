"""
sg2_step17_resolve_sg3_identifiers.py

The SG3 sequel to sg2_step9c_resolve_all_identifiers.py: resolves all 904
SG3 Act names to their legislation.govt.nz (type, status, year, number)
identifier, using the same search endpoint and validation approach.

    GET https://www.legislation.govt.nz/items/?search_term=<name>&per_page=5

Paced at ~1 request/second, same courtesy reasoning as step9c (904 Acts
=> roughly 15 minutes to run). Validates against "Financial Markets
Authority Act 2011" first (known answer: year 2011, number 5) before
running the full list -- that Act isn't part of SG3, it's just a fixed,
independently-confirmed known-answer check, same one step9c used, kept
identical here so a validation failure means the site/parsing changed,
not that something about SG3 itself is different.

Output: data/processed/sg3_act_identifiers.json, one entry per SG3 Act,
same shape as sg2_act_identifiers.json:
    {
      "act": "...",
      "resolved": true/false,
      "type": "act" | "regulation" | ...,
      "status": "public" | "private" | "local" | "imperial",
      "year": 2011,
      "number": "5",
      "url": "https://www.legislation.govt.nz/act/public/2011/5/en/latest/",
      "xml_url": "https://legislation.govt.nz/act/public/2011/5/en/latest.xml",
      "year_mismatch": true/false
    }
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

SG3_PATH = Path("data/processed/sg3_final_list.json")
OUTPUT_PATH = Path("data/processed/sg3_act_identifiers.json")
DELAY_SECONDS = 1.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

RESULT_LINK_RE = re.compile(
    r'href="(/(act|regulation|rule|order|notice)/(public|private|local|imperial)/(\d{4})/(\d+)/en/latest/[^"]*)"'
)
NAME_YEAR_RE = re.compile(r"(18|19|20)\d{2}")


def search(name):
    url = f"https://www.legislation.govt.nz/items/?search_term={quote(name)}&per_page=5"
    r = requests.get(url, headers=HEADERS, timeout=20)
    return r


def parse_first_result(html):
    m = RESULT_LINK_RE.search(html)
    if not m:
        return None
    path, doc_type, status, year, number = m.groups()
    return {
        "type": doc_type,
        "status": status,
        "year": int(year),
        "number": number,
        "url": f"https://www.legislation.govt.nz{path}",
        "xml_url": f"https://legislation.govt.nz/{doc_type}/{status}/{year}/{number}/en/latest.xml",
    }


# ---- validate against the known answer first (same check as step9c) ----
print("Validating against 'Financial Markets Authority Act 2011' (expected: 2011 / 5)...")
r = search("Financial Markets Authority Act 2011")
print(f"  status {r.status_code}, {len(r.text)} chars")
result = parse_first_result(r.text)
print(f"  parsed: {result}")

if not result or result["year"] != 2011 or result["number"] != "5":
    print("\n!! Validation FAILED -- top result doesn't match the known answer (2011/5).")
    print("Stopping here rather than mis-resolving all 904. Raw response snippet:")
    print(re.sub(r"\s+", " ", r.text)[:3000])
    raise SystemExit(1)

print("Validation OK. Proceeding to resolve all 904 SG3 Acts...\n")
time.sleep(DELAY_SECONDS)

with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)

results = []
n_resolved = 0
n_unresolved = 0
n_year_mismatch = 0

for i, c in enumerate(sg3, 1):
    name = c["act"]
    entry = {"act": name, "resolved": False}
    try:
        r = search(name)
        parsed = parse_first_result(r.text)
        if parsed:
            entry.update(parsed)
            entry["resolved"] = True
            name_years_full = re.findall(r"(?:18|19|20)\d{2}", name)
            if name_years_full and str(parsed["year"]) not in name_years_full:
                entry["year_mismatch"] = True
                n_year_mismatch += 1
            else:
                entry["year_mismatch"] = False
            n_resolved += 1
        else:
            n_unresolved += 1
    except Exception as e:
        entry["error"] = f"{type(e).__name__}: {e}"
        n_unresolved += 1

    results.append(entry)
    if i % 25 == 0 or i == len(sg3):
        print(f"  [{i}/{len(sg3)}] resolved={n_resolved} unresolved={n_unresolved} year_mismatch={n_year_mismatch}")

    time.sleep(DELAY_SECONDS)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nDone. Resolved {n_resolved}/{len(sg3)}, unresolved {n_unresolved}, "
      f"year mismatches flagged for review: {n_year_mismatch}")
print(f"Saved -> {OUTPUT_PATH}")
