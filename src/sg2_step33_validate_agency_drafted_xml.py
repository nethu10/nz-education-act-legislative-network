"""
sg2_step33_validate_agency_drafted_xml.py

Diagnostic: sg2_step26 fetched XML for 899 SG3 Acts, and 30 failed -- almost
all of them Land Transport Rules (agency-drafted secondary legislation,
tilde-prefixed identifiers). That's suspicious, because the xml_url for
this document type was NEVER actually confirmed to exist -- sg2_step10's
original validation deliberately excluded tilde-prefixed entries and only
tested the regular "act" and "pco-drafted" XML patterns. This checks
directly whether legislation.govt.nz actually serves XML at
.../agency-drafted/~{year}/~{number}/en/latest.xml, or whether that URL
pattern (built by analogy, not confirmed) simply doesn't exist for this
document type -- which would mean the 30 "failures" are a genuine data-
source gap, not transient network errors, and no amount of retrying would
fix them.

Tests every currently-unresolved-XML SG3 entry that's agency-drafted type,
plus prints raw status/content for a first look. Paste the whole output
back -- it decides whether we need a different approach for these 22ish
Land Transport Rules (e.g. falling back to the HTML page instead of XML)
or whether this was just a transient blip after all.
"""
import json
import re
from pathlib import Path

import requests

IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")
RAW_DIR = Path("data/raw/sg3_targets")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/xml,text/xml,*/*;q=0.8",
}

with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

resolved = [d for d in identifiers if d.get("resolved") and d.get("xml_url")]

not_yet_cached = []
for d in resolved:
    cache_path = RAW_DIR / f"{d['year']}_{d['number']}.xml"
    if not cache_path.exists():
        not_yet_cached.append(d)

agency_drafted = [d for d in not_yet_cached if d.get("subtype") == "agency-drafted"]
other = [d for d in not_yet_cached if d.get("subtype") != "agency-drafted"]

print(f"{len(not_yet_cached)} SG3 Acts have no cached XML yet "
      f"({len(agency_drafted)} agency-drafted, {len(other)} other -- these should "
      f"roughly match sg2_step26's 30 failures)\n")

print("=" * 70)
print(f"Testing {min(5, len(agency_drafted))} agency-drafted XML URLs...")
print("=" * 70)
for d in agency_drafted[:5]:
    url = d["xml_url"]
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        looks_like_xml = r.text.lstrip().startswith("<?xml") or r.text.lstrip().startswith("<")
        print(f"\n{d['act']!r}")
        print(f"  {url}")
        print(f"  -> status {r.status_code}, {len(r.text)} chars, "
              f"content-type={r.headers.get('Content-Type')}, looks like XML: {looks_like_xml}")
        print(f"  snippet: {re.sub(chr(92)+'s+', ' ', r.text)[:300]}")
    except Exception as e:
        print(f"\n{d['act']!r}")
        print(f"  {url}")
        print(f"  -> ERROR {type(e).__name__}: {e}")

if other:
    print("\n" + "=" * 70)
    print(f"Testing {min(5, len(other))} non-agency-drafted failures (should be normal)...")
    print("=" * 70)
    for d in other[:5]:
        url = d["xml_url"]
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            looks_like_xml = r.text.lstrip().startswith("<?xml") or r.text.lstrip().startswith("<")
            print(f"\n{d['act']!r}")
            print(f"  {url}")
            print(f"  -> status {r.status_code}, {len(r.text)} chars, looks like XML: {looks_like_xml}")
        except Exception as e:
            print(f"\n{d['act']!r}")
            print(f"  {url}")
            print(f"  -> ERROR {type(e).__name__}: {e}")