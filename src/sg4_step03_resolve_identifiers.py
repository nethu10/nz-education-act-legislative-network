"""
sg4_step03_resolve_identifiers.py

First identifier-resolution pass for SG4 -- but consolidated, unlike
SG3's original step17 (which needed six more retry passes, steps
18-23, to mop up). This bakes in everything learned along the way:

  1. The corrected multi-pattern URL regex (step21) covering all three
     legislation.govt.nz schemes -- Acts, PCO-drafted secondary
     legislation, and agency-drafted (tilde-prefixed) secondary
     legislation. Step17's original regex only knew the Act pattern,
     which alone caused most of SG3's unresolved count.
  2. A query-transformation cascade tried in order for any name that
     doesn't resolve on the raw string, combining step22 and step23's
     fixes -- IMPORTANTLY using step23's CORRECTED alt-name-split
     direction (before the "/", not after -- step22's original
     after-slash attempt was confirmed wrong for "Te Ture mo Te Reo
     Maori 2016/the Maori Language Act 2016", which is indexed under
     the primary before-slash title).
  3. A macron-normalisation variant, new for SG4 -- prompted by finding
     "Māori Trustee Act 1953" and "Maori Trustee Act 1953" [one with
     macron, one without] as two separate entries citing the same
     target while building the SG3-internal links. The same class of
     encoding mismatch could easily recur among SG4's own candidates.

Deliberately NOT pre-applied: the RENAME_MAP of specific historical
Act renames, Court/Courts variants, and the 2025 companion-Act
citation pairs built up for SG1-SG3. Those are known fixes for
SPECIFIC Act names already seen in SG1-SG3 -- by construction, SG4's
candidates are new names that were never in those layers, so that map
doesn't directly apply here. If SG4 turns out to contain its OWN
renames/variants (plausible, same reform patterns could recur), those
get found and fixed the same evidence-based way SG3's were: from what
actually shows up unresolved, not guessed in advance.

Output: data/processed/sg4_act_identifiers.json, same shape as
sg3_act_identifiers.json:
    {
      "act": "...",
      "resolved": true/false,
      "type": "act" | "regulation" | ... | "secondary-legislation",
      "subtype": "pco-drafted" | "agency-drafted" (secondary-legislation only),
      "status": "public" | "private" | "local" | "imperial" | null,
      "year": 2011,
      "number": "5",
      "url": "...",
      "xml_url": "...",
      "resolved_via": null | "land_transport_rule" | "fragment_citation" |
                      "trailing_parenthetical_stripped" | "alt_name_before_slash" |
                      "apostrophe_straight" | "apostrophe_curly" |
                      "apostrophe_removed" | "macron_stripped",
      "searched_as": null | "<the query actually used, if different from 'act'>"
    }

Paced at ~1 request/second per query attempt (same courtesy as before).
1,169 Acts, mostly one request each => roughly 20-30 minutes depending
on how many need the cascade.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

SG4_PATH = Path("data/processed/sg4_final_list.json")
OUTPUT_PATH = Path("data/processed/sg4_act_identifiers.json")
DELAY_SECONDS = 1.0
MAX_ATTEMPTS = 3

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

LAND_TRANSPORT_RULE_RE = re.compile(
    r"^Land Transport Rule:\s*(.+?)\s*\([0-9/]+\)\s*$", re.IGNORECASE
)
FRAGMENT_CITATION_RE = re.compile(
    r"^(?:Parts?|Sections?|Schedules?)\b.*?\bof the\s+(.+)$", re.IGNORECASE
)
TRAILING_PAREN_RE = re.compile(r"\s*\((?:[^()]|\([^()]*\))*\)\s*$")

CURLY_APOS = "\u2019"
STRAIGHT_APOS = "'"
MACRON_MAP = str.maketrans("\u0101\u0113\u012b\u014d\u016b\u0100\u0112\u012a\u014c\u016a", "aeiouAEIOU")


def candidate_queries(name):
    """Yield (query, resolved_via) variants to try in order. Always tries
    the raw name first -- most SG4 Acts should resolve there, same as
    ~94% of SG3 did once the regex itself was fixed."""
    yield name, None

    m = LAND_TRANSPORT_RULE_RE.match(name)
    if m:
        yield m.group(1).strip(), "land_transport_rule"

    m = FRAGMENT_CITATION_RE.match(name)
    if m:
        yield m.group(1).strip(), "fragment_citation"

    stripped = TRAILING_PAREN_RE.sub("", name).strip()
    if stripped and stripped != name:
        yield stripped, "trailing_parenthetical_stripped"

    slash_idx = name.find("/")
    paren_idx = name.find("(")
    if slash_idx != -1 and (paren_idx == -1 or slash_idx < paren_idx):
        before, _, _ = name.partition("/")
        before = before.strip()
        if before and before != name:
            yield before, "alt_name_before_slash"

    if CURLY_APOS in name or STRAIGHT_APOS in name:
        if CURLY_APOS in name:
            yield name.replace(CURLY_APOS, STRAIGHT_APOS), "apostrophe_straight"
        if STRAIGHT_APOS in name:
            yield name.replace(STRAIGHT_APOS, CURLY_APOS), "apostrophe_curly"
        no_apos = name.replace(CURLY_APOS, "").replace(STRAIGHT_APOS, "")
        if no_apos != name:
            yield no_apos, "apostrophe_removed"

    macron_stripped = name.translate(MACRON_MAP)
    if macron_stripped != name:
        yield macron_stripped, "macron_stripped"


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
            "type": doc_type,
            "status": status,
            "year": year,
            "number": number,
            "url": url,
            "xml_url": f"https://legislation.govt.nz/{doc_type}/{status}/{year}/{number}/en/latest.xml",
        }
    if gd["year2"]:
        year, number = int(gd["year2"]), gd["number2"]
        return {
            "type": "secondary-legislation",
            "subtype": "pco-drafted",
            "status": None,
            "year": year,
            "number": number,
            "url": url,
            "xml_url": f"https://legislation.govt.nz/secondary-legislation/pco-drafted/{year}/{number}/en/latest.xml",
        }
    if gd["year3"]:
        year, number = int(gd["year3"]), gd["number3"]
        return {
            "type": "secondary-legislation",
            "subtype": "agency-drafted",
            "status": None,
            "year": year,
            "number": number,
            "url": url,
            "xml_url": f"https://legislation.govt.nz/secondary-legislation/agency-drafted/~{year}/~{number}/en/latest.xml",
        }
    return None


def search_with_retries(name):
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            r = search(name, timeout=25)
            return parse_first_result(r.text), None
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(2 * attempt)
    return None, last_err


print("Validating against 'Financial Markets Authority Act 2011' (expected: 2011 / 5)...")
r = search("Financial Markets Authority Act 2011")
print(f"  status {r.status_code}, {len(r.text)} chars")
result = parse_first_result(r.text)
print(f"  parsed: {result}")

if not result or result["year"] != 2011 or result["number"] != "5":
    print("\n!! Validation FAILED -- top result doesn't match the known answer (2011/5).")
    print("Stopping here rather than mis-resolving all 1,169. Raw response snippet:")
    print(re.sub(r"\s+", " ", r.text)[:3000])
    raise SystemExit(1)

print("Validation OK. Proceeding to resolve all SG4 Acts...\n")
time.sleep(DELAY_SECONDS)

with open(SG4_PATH, encoding="utf-8") as f:
    sg4 = json.load(f)

results = []
n_resolved = 0
n_unresolved = 0
n_via_cascade = 0

for i, c in enumerate(sg4, 1):
    name = c["act"]
    entry = {"act": name, "resolved": False}

    fixed = False
    last_err = None
    for query, resolved_via in candidate_queries(name):
        parsed, err = search_with_retries(query)
        if err:
            last_err = err
        time.sleep(DELAY_SECONDS)
        if parsed:
            entry.update(parsed)
            entry["resolved"] = True
            entry["resolved_via"] = resolved_via
            entry["searched_as"] = query if query != name else None
            n_resolved += 1
            if resolved_via:
                n_via_cascade += 1
            fixed = True
            break

    if not fixed:
        entry["resolved"] = False
        if last_err:
            entry["error"] = last_err
        n_unresolved += 1

    results.append(entry)
    if i % 25 == 0 or i == len(sg4):
        print(f"  [{i}/{len(sg4)}] resolved={n_resolved} (of which via cascade={n_via_cascade}) unresolved={n_unresolved}")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nDone. Resolved {n_resolved}/{len(sg4)} ({n_via_cascade} needed a query-transform variant), "
      f"unresolved {n_unresolved}")
print(f"Saved -> {OUTPUT_PATH}")

if n_unresolved:
    print("\nStill-unresolved Acts, with their SG4 combined_score (highest first):")
    score_by_name = {c["act"]: c.get("combined_score", 0) for c in sg4}
    remaining = sorted(
        (d for d in results if not d.get("resolved")),
        key=lambda d: -score_by_name.get(d["act"], 0),
    )
    for d in remaining[:60]:
        print(f"  {score_by_name.get(d['act']):>4}  {d['act']!r}")
    if len(remaining) > 60:
        print(f"  ... and {len(remaining) - 60} more (full list is in {OUTPUT_PATH})")
