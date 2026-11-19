"""
sg2_step19_retry_sg3_land_transport_rules.py

Third resolution pass over whatever sg2_step18 left unresolved. Targets
one specific, systematic gap: 22 "Land Transport Rule: X YYYY (code)"
Acts (e.g. "Land Transport Rule: Operator Licensing 2007 (81001)")  --
NZTA's own naming convention for instruments it issues under delegated
authority, which doesn't match how legislation.govt.nz's search indexes
them. Neither step17 nor step18's transformations (direct name,
schedule-of-parent, reprint-suffix-stripped) touch this pattern, so
these never had a fair search attempt.

Transformation: strip the "Land Transport Rule: " prefix and the
trailing "(code)" parenthetical, search just the descriptive middle
(e.g. "Operator Licensing 2007"), tagged resolved_via="land_transport_rule".

Everything else still unresolved gets one more plain direct retry too
(no new transformation) -- this catches genuine transient failures like
the DNS/connection errors seen mid-run in step18 (Evidence Regulations
2007, Building Regulations 1992, Overseas Investment Regulations 2005,
Health (Retention of Health Information) Regulations 1996), which failed
for network reasons, not because nothing was found.

Same update-in-place behaviour as step18: sg3_act_identifiers.json is
updated, already-resolved entries are untouched, and anything still
unresolved after this pass stays resolved=false with a final
score-ranked summary for deciding whether to chase further.
"""
import json
import re
import time
from pathlib import Path

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
    r'href="(/(act|regulation|rule|order|notice)/(public|private|local|imperial)/(\d{4})/(\d+)/[^"]*)"'
)

LAND_TRANSPORT_RULE_RE = re.compile(
    r"^Land Transport Rule:\s*(.+?)\s*\([0-9/]+\)\s*$", re.IGNORECASE
)


def search(name, timeout=25):
    url = f"https://www.legislation.govt.nz/items/?search_term={requests.utils.quote(name)}&per_page=5"
    return requests.get(url, headers=HEADERS, timeout=timeout)


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
print(f"Retrying {len(unresolved_names)} still-unresolved SG3 Acts...\n")

n_fixed = 0
n_still_unresolved = 0
n_land_transport = 0

for i, name in enumerate(unresolved_names, 1):
    query = name
    resolved_via = "direct_retry_pass3"

    m = LAND_TRANSPORT_RULE_RE.match(name)
    if m:
        query = m.group(1).strip()
        resolved_via = "land_transport_rule"
        n_land_transport += 1

    parsed, err = search_with_retries(query)

    entry = by_act[name]
    if parsed:
        entry.update(parsed)
        entry["resolved"] = True
        entry["resolved_via"] = resolved_via
        entry["searched_as"] = query if query != name else None
        n_fixed += 1
        tag = f" (as {resolved_via}, query={query!r})" if resolved_via != "direct_retry_pass3" else ""
        print(f"  [{i}/{len(unresolved_names)}] FIXED: {name!r}{tag} -> {entry['year']}/{entry['number']}")
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
print(f"\nLand Transport Rule entries attempted: {n_land_transport}")
print(f"Fixed this pass: {n_fixed}")
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