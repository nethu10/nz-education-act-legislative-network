"""
sg2_step21_retry_sg3_secondary_legislation.py

Fourth resolution pass over whatever's still unresolved after
step17/step18/step19. Root cause found from real sample URLs the user
pulled by hand: legislation.govt.nz hosts most secondary legislation
(Regulations, Orders, and agency-drafted instruments like NZTA's Land
Transport Rules) under a URL scheme steps 17-19's RESULT_LINK_RE never
recognised at all:

  Acts (unchanged, still works):
    /act/{status}/{year}/{number}/en/latest/

  PCO-drafted secondary legislation (most Regulations/Orders):
    /secondary-legislation/pco-drafted/{year}/{number}/en/latest/

  Agency-drafted secondary legislation (e.g. Land Transport Rules):
    /secondary-legislation/agency-drafted/~{year}/~{number}/en/latest/
    -- note the tildes, and the year/number here is an internal
    compilation identifier, NOT the year in the instrument's own title
    (e.g. "Land Transport Rule: Operator Licensing 2007" lives under
    ~2025/~275522 -- there is no way to guess this from the name, it has
    to come from an actual search hit).

This isn't a new name transformation -- the search results were already
finding these pages all along, the regex just couldn't see the links.
So this pass does a plain retry of the ORIGINAL Act name against the
corrected regex, no query rewriting.

Acts that still don't resolve after this (e.g. "Children's Commissioner
Act 2003", whose URL uses the OLD /act/.../ pattern this regex already
covered) are a different, smaller category: genuine search-ranking
misses or Acts not in the top 5 results, not a URL-pattern gap. Left
unresolved with a final score-ranked summary, same as before.

NOTE: this same URL-scheme gap likely also explains SG2's one
persistently-unresolved Act ("Land Transport Rule", mentioned earlier in
the pipeline) -- low-impact at 1/437, not re-run here, but worth
revisiting later with the same fix if useful.
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
print(f"Retrying {len(unresolved_names)} still-unresolved SG3 Acts with the corrected "
      f"secondary-legislation URL pattern...\n")

n_fixed = 0
n_fixed_secondary = 0
n_still_unresolved = 0

for i, name in enumerate(unresolved_names, 1):
    parsed, err = search_with_retries(name)

    entry = by_act[name]
    if parsed:
        entry.update(parsed)
        entry["resolved"] = True
        entry["resolved_via"] = "secondary_legislation_regex_fix"
        n_fixed += 1
        if parsed["type"] == "secondary-legislation":
            n_fixed_secondary += 1
        print(f"  [{i}/{len(unresolved_names)}] FIXED: {name!r} -> "
              f"{parsed['type']}/{parsed.get('subtype', parsed.get('status'))}/{parsed['year']}/{parsed['number']}")
    else:
        entry["resolved"] = False
        if err:
            entry["error"] = err
        n_still_unresolved += 1
        print(f"  [{i}/{len(unresolved_names)}] still unresolved: {name!r}" + (f" [{err}]" if err else ""))

    time.sleep(DELAY_SECONDS)

with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(identifiers, f, indent=2, ensure_ascii=False)

n_total_resolved = sum(1 for d in identifiers if d.get("resolved"))
print(f"\nFixed this pass: {n_fixed} (of which {n_fixed_secondary} were the secondary-legislation URL pattern)")
print(f"Still unresolved: {n_still_unresolved}")
print(f"Overall: {n_total_resolved}/{len(sg3)} resolved")
print(f"Saved -> {IDENTIFIERS_PATH}")

if n_still_unresolved:
    print("\nStill-unresolved Acts, with their SG3 combined_score:")
    score_by_name = {c["act"]: c["combined_score"] for c in sg3}
    remaining = sorted(
        (d for d in identifiers if not d.get("resolved")),
        key=lambda d: -score_by_name.get(d["act"], 0),
    )
    for d in remaining:
        print(f"  {score_by_name.get(d['act']):>4}  {d['act']!r}")