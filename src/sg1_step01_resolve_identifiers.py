"""
sg1_step01_resolve_identifiers.py

SG1 never went through the identifier-resolution + internal-link-finding
treatment that SG2 (sg2_step9c + sg2_step11), SG3 (sg2_step26_v2), and SG5
(sg4_step11 + sg4_step14) all got -- SG1 was built earlier, as a standalone
diagram deliverable (37 Acts, names + scores only), before the
"check whether Acts within this layer cite each other" step was introduced
into the pipeline at SG2. This is stage 1 of retrofitting that check onto
SG1: resolve each of the 37 SG1 Acts to a (type, status, year, number)
legislation.govt.nz identifier, exactly the way sg2_step9c did for SG2.

Uses the same validated search endpoint and parsing regex as sg2_step9c
(GET https://www.legislation.govt.nz/items/?search_term=<name>&per_page=5,
first https://.../{type}/{status}/{year}/{number}/en/latest/... href wins),
and the same known-answer validation gate before running the full list.

SG1 Act names carry a citation suffix (e.g. "Crown Entities Act 2004 (2004
No 115)") -- stripped with the same normalize()/CITE_PATTERN used
throughout the pipeline (sg2_step8 etc.) before searching, since the suffix
isn't part of the Act's title as legislation.govt.nz indexes it.

BLOCKED as of 2026-09-25: this workspace's network policy is currently
denying all connections to legislation.govt.nz (confirmed via direct curl:
"CONNECT tunnel failed, response 403"). This script is written and ready
but has NOT been run or validated against a live response. Once network
access is restored, run it and check the validation-gate output carefully
before trusting the full 37-Act run.

Run from the repo root:
    python src/sg1_step01_resolve_identifiers.py

Output: data/processed/sg1_act_identifiers.json, one entry per SG1 Act,
same shape as sg2_act_identifiers.json / sg3_act_identifiers.json:
    {
      "act": "...",              # original name WITH citation suffix, as in sg1_final_list.json
      "resolved": true/false,
      "type": "act" | "regulation" | ...,
      "status": "public" | "private" | "local" | "imperial",
      "year": 2004,
      "number": "115",
      "url": "https://www.legislation.govt.nz/act/public/2004/115/en/latest/",
      "xml_url": "https://legislation.govt.nz/act/public/2004/115/en/latest.xml",
      "year_mismatch": true/false
    }
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

SG1_PATH = Path("data/processed/sg1_final_list.json")
OUTPUT_PATH = Path("data/processed/sg1_act_identifiers.json")
DELAY_SECONDS = 1.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

RESULT_LINK_RE = re.compile(
    r'href="(/(act|regulation|rule|order|notice)/(public|private|local|imperial)/(\d{4})/(\d+)/en/latest/[^"]*)"'
)

# same citation-suffix-stripping normalize() used throughout the pipeline
# (sg2_step8, sg2_step11, sg2_step26, ...) -- SG1 names all carry this
# suffix (e.g. "Crown Entities Act 2004 (2004 No 115)"), which needs
# stripping before searching by title.
CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")


def normalize(name):
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()


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


def main():
    print("Validating against 'Financial Markets Authority Act 2011' (expected: 2011 / 5) "
          "-- same validation gate sg2_step9c used...")
    r = search("Financial Markets Authority Act 2011")
    print(f"  status {r.status_code}, {len(r.text)} chars")
    result = parse_first_result(r.text)
    print(f"  parsed: {result}")

    if not result or result["year"] != 2011 or result["number"] != "5":
        print("\n!! Validation FAILED -- top result doesn't match the known answer (2011/5).")
        print("Stopping here rather than mis-resolving all 37. Raw response snippet:")
        print(re.sub(r"\s+", " ", r.text)[:3000])
        raise SystemExit(1)

    print("Validation OK. Proceeding to resolve all 37 SG1 Acts...\n")
    time.sleep(DELAY_SECONDS)

    with open(SG1_PATH, encoding="utf-8") as f:
        sg1 = json.load(f)
    print(f"Loaded {len(sg1)} SG1 Acts from {SG1_PATH}")

    results = []
    n_resolved = 0
    n_unresolved = 0
    n_year_mismatch = 0

    for i, c in enumerate(sg1, 1):
        original_name = c["act"]
        search_name = normalize(original_name)
        entry = {"act": original_name, "resolved": False}
        try:
            r = search(search_name)
            parsed = parse_first_result(r.text)
            if parsed:
                entry.update(parsed)
                entry["resolved"] = True
                name_years_full = re.findall(r"(?:18|19|20)\d{2}", search_name)
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
        status_str = "OK" if entry.get("resolved") else "UNRESOLVED"
        print(f"  [{i}/{len(sg1)}] {original_name!r} -> {status_str}"
              + (f" ({entry.get('year')}/{entry.get('number')})" if entry.get("resolved") else ""))

        time.sleep(DELAY_SECONDS)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Resolved {n_resolved}/{len(sg1)}, unresolved {n_unresolved}, "
          f"year mismatches flagged for review: {n_year_mismatch}")
    print(f"Saved -> {OUTPUT_PATH}")
    print("\nIf any Acts are unresolved or year-mismatched, check them manually before")
    print("running sg1_step02_find_internal_links.py -- an unresolved Act can't be")
    print("checked for internal links either as a source or a target.")


if __name__ == "__main__":
    main()
