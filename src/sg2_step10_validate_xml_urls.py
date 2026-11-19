"""
sg2_step10_validate_xml_urls.py

Before fetching XML for all 437 SG2 Acts, confirm the xml_url pattern
actually works for BOTH identifier shapes we now have:
  - "act" type:                 .../act/{status}/{year}/{number}/en/latest.xml
                                 (confirmed working for the seed Act in
                                 stage1_acquisition.py, but not yet tested
                                 for an arbitrary SG2 "act" entry)
  - "secondary-legislation" type: .../secondary-legislation/{pco-drafted|
                                 agency-drafted}/{year}/{number}/en/latest.xml
                                 (built by analogy from the act pattern --
                                 NEVER actually confirmed to exist)

Tests 5 entries: 3 "secondary-legislation" (the bulk of what's new here)
and 2 "act". Prints status code + first 300 chars of each response so we
can see clearly whether we got real XML back or a 404/redirect.
"""
import json
import re
from pathlib import Path

import requests

IDENTIFIERS_PATH = Path("data/processed/sg2_act_identifiers.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/xml,text/xml,*/*;q=0.8",
}

with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

resolved = [d for d in identifiers if d.get("resolved") and d.get("xml_url")]

sec_leg = [d for d in resolved if d.get("type") == "secondary-legislation"
           and "~" not in str(d.get("year", "")) and "~" not in str(d.get("number", ""))][:3]
acts = [d for d in resolved if d.get("type") == "act"][:2]

sample = sec_leg + acts
print(f"Testing {len(sample)} sample XML URLs ({len(sec_leg)} secondary-legislation, {len(acts)} act)...\n")

for d in sample:
    url = d["xml_url"]
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"{d['act']!r}")
        print(f"  {url}")
        print(f"  -> status {r.status_code}, {len(r.text)} chars, "
              f"content-type={r.headers.get('Content-Type')}")
        looks_like_xml = r.text.lstrip().startswith("<?xml") or r.text.lstrip().startswith("<")
        print(f"  looks like XML: {looks_like_xml}")
        print(f"  snippet: {re.sub(chr(92)+'s+', ' ', r.text)[:300]}")
        print()
    except Exception as e:
        print(f"{d['act']!r}")
        print(f"  {url}")
        print(f"  -> ERROR {type(e).__name__}: {e}\n")
