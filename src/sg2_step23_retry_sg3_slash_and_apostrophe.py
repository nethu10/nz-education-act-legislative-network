"""
sg2_step23_retry_sg3_slash_and_apostrophe.py

Sixth resolution pass, over whatever step22 left unresolved (12/901 after
that pass). Manually checked all 12 against legislation.govt.nz search;
most are genuine misses (mid-title parentheses that can't be safely
stripped, or instruments that may not be in the searchable index at all),
but two specific, confirmed causes are worth one more targeted retry:

  1. alt_name_after_slash entries where step22 took the WRONG side of the
     "/". "Te Ture mo Te Reo Maori 2016/the Maori Language Act 2016"
     confirmed (via manual search) to be a plain Public Act at
     /act/public/2016/17/ -- but legislation.govt.nz indexes it under the
     PRIMARY (before-slash) title, not the English alt-title step22 tried.
     This retries the before-slash half for anything still unresolved that
     contains a "/".

  2. Possessive-apostrophe names. "Children's Commissioner Act 2003" and
     "Children's Health Camps Board Dissolution Act 1999" both confirmed
     (via manual search) to be simple, unambiguous Public Acts with no
     special naming issues otherwise -- the one thing they share is an
     apostrophe. This retries with the apostrophe normalised both ways
     (curly U+2019 <-> straight U+0027) and with it removed entirely, in
     case a character-encoding mismatch against the site's own indexing is
     knocking the real result out of the top 5.

Deliberately NOT retried here:
  - "Land Transport Rule: Vehicle Dimensions and Mass 2002 (41001)" --
    confirmed via manual search that the CURRENT in-force rule under code
    41001 is the 2016 revision, not 2002. The SG3 citation text explicitly
    says "2002", so silently resolving it to the 2016 replacement would be
    an assumption the source text doesn't support. This is a judgement
    call, not a pipeline bug -- left for a manual decision rather than
    auto-fixed.
  - Everything else still unresolved after step22 (Domestic Violence
    (General) Regulations 1996, Housing Restructuring and Tenancy Matters
    (Appeals) Regulations 2000, the two United Nations Sanctions
    Regulations, Health Reforms (Transitional Provisions) Act 1993, the
    Transport Notice, the Resource Management Order) -- all have a
    parenthetical in the MIDDLE of their real title (not a trailing code),
    so there's no safe mechanical transformation left to try; treated as
    genuine search-ranking misses or instruments outside the searchable
    index.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

SG3_PATH = Path("data/processed/sg3_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")
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

CURLY_APOS = "’"
STRAIGHT_APOS = "'"


def candidate_queries(name):
    """Yield (query, resolved_via) candidates to try in order, for a name
    that's still unresolved after step22."""
    if "/" in name:
        before, _, _ = name.partition("/")
        before = before.strip()
        if before:
            yield before, "alt_name_before_slash"

    if CURLY_APOS in name or STRAIGHT_APOS in name:
        if CURLY_APOS in name:
            yield name.replace(CURLY_APOS, STRAIGHT_APOS), "apostrophe_straight"
        if STRAIGHT_APOS in name:
            yield name.replace(STRAIGHT_APOS, CURLY_APOS), "apostrophe_curly"
        no_apos = name.replace(CURLY_APOS, "").replace(STRAIGHT_APOS, "")
        if no_apos != name:
            yield no_apos, "apostrophe_removed"


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


with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

by_act = {d["act"]: d for d in identifiers}
unresolved_names = [d["act"] for d in identifiers if not d.get("resolved")]
print(f"Retrying {len(unresolved_names)} still-unresolved SG3 Acts "
      f"(slash-direction fix + apostrophe normalisation)...\n")

n_fixed = 0
n_still_unresolved = 0
n_skipped = 0

for i, name in enumerate(unresolved_names, 1):
    entry = by_act[name]
    candidates = list(candidate_queries(name))

    if not candidates:
        n_skipped += 1
        print(f"  [{i}/{len(unresolved_names)}] no new query to try, left as-is: {name!r}")
        continue

    fixed = False
    for query, resolved_via in candidates:
        parsed, err = search_with_retries(query)
        time.sleep(DELAY_SECONDS)
        if parsed:
            entry.update(parsed)
            entry["resolved"] = True
            entry["resolved_via"] = resolved_via
            entry["searched_as"] = query
            n_fixed += 1
            fixed = True
            print(f"  [{i}/{len(unresolved_names)}] FIXED: {name!r} (as {resolved_via}, "
                  f"query={query!r}) -> {parsed['type']}/{parsed.get('subtype', parsed.get('status'))}/"
                  f"{parsed['year']}/{parsed['number']}")
            break

    if not fixed:
        n_still_unresolved += 1
        print(f"  [{i}/{len(unresolved_names)}] still unresolved after {len(candidates)} "
              f"variant(s): {name!r}")

with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(identifiers, f, indent=2, ensure_ascii=False)

n_total_resolved = sum(1 for d in identifiers if d.get("resolved"))
print(f"\nFixed this pass: {n_fixed}")
print(f"Still unresolved (no new variant to try): {n_skipped}")
print(f"Still unresolved (variants tried, none worked): {n_still_unresolved}")
print(f"Overall: {n_total_resolved}/{len(sg3)} resolved")
print(f"Saved -> {IDENTIFIERS_PATH}")

if n_skipped or n_still_unresolved:
    print("\nStill-unresolved Acts, with their SG3 combined_score:")
    score_by_name = {c["act"]: c["combined_score"] for c in sg3}
    remaining = sorted(
        (d for d in identifiers if not d.get("resolved")),
        key=lambda d: -score_by_name.get(d["act"], 0),
    )
    for d in remaining:
        print(f"  {score_by_name.get(d['act']):>4}  {d['act']!r}")