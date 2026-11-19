"""
sg2_step9d_retry_unresolved.py

Second pass over the 76 SG2 Acts that sg2_step9c left unresolved. Fixes
three distinct causes rather than just blindly retrying everything:

  1. Transient ReadTimeouts (~18) -- retried with backoff (2 attempts,
     longer timeout) and nothing else changed.

  2. "Schedule N of the X Act" / "Schedule N of the X Regulations"
     pseudo-names (~9) -- these aren't standalone documents on the site,
     they're a fragment of Act X. Stripped down to just "X" before
     searching, and the result is tagged resolved_via="schedule_of_parent"
     so we know it's really pointing at the parent Act, not a distinct
     SG2 node. Two of these are schedules of Public Service Act 2020,
     which sg2_step8 already excludes as a hub Act by exact name --
     worth checking after this run whether they should be excluded too
     now that we know what they really are.

  3. Everything else -- retried with:
       - old reprint-citation suffixes stripped, e.g. "(RS Vol 33, p 715)"
         or "(1957 Reprint, Vol 3, p 79)", which aren't part of the
         Act's real title and likely confuse the search
       - the URL match relaxed to accept ANY /{type}/{status}/{year}/{number}/
         path, not just ones ending in "en/latest/" -- a revoked or
         superseded instrument may only have a dated/repealed version,
         which the original step9c regex silently rejected

Acts still unresolved after this pass are left as resolved=false in the
output and are NOT silently dropped -- data/processed/sg2_act_identifiers.json
is updated in place (originally-resolved entries are kept as-is), and a
final summary breaks down what's still missing and at what score, so the
decision to accept the remainder as unresolved (vs. chase them manually)
is made with the evidence in front of us rather than assumed here.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

SG2_PATH = Path("data/processed/sg2_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg2_act_identifiers.json")
DELAY_SECONDS = 1.0
MAX_ATTEMPTS = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# relaxed: no longer requires the path to end in "en/latest/"
RESULT_LINK_RE = re.compile(
    r'href="(/(act|regulation|rule|order|notice)/(public|private|local|imperial)/(\d{4})/(\d+)/[^"]*)"'
)

SCHEDULE_PREFIX_RE = re.compile(r"^Schedule\s+[\w-]+\s+of\s+the\s+(.+)$", re.IGNORECASE)
REPRINT_SUFFIX_RE = re.compile(
    r"\s*\((?:\d{4}\s+No\s+\d+\)\s*\((?:RS|.*?Reprint)[^)]*\)|(?:RS|.*?Reprint)[^)]*)\s*$"
)


def search(name, timeout=25):
    url = f"https://www.legislation.govt.nz/items/?search_term={quote(name)}&per_page=5"
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
            time.sleep(2 * attempt)  # backoff
    return None, last_err


with open(SG2_PATH, encoding="utf-8") as f:
    sg2 = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

by_act = {d["act"]: d for d in identifiers}
unresolved_names = [d["act"] for d in identifiers if not d.get("resolved")]
print(f"Retrying {len(unresolved_names)} unresolved SG2 Acts...\n")

n_fixed = 0
n_still_unresolved = 0

for i, name in enumerate(unresolved_names, 1):
    # decide what to actually search for
    query = name
    resolved_via = "direct_retry"

    m = SCHEDULE_PREFIX_RE.match(name)
    if m:
        query = m.group(1).strip()
        resolved_via = "schedule_of_parent"
    else:
        stripped = REPRINT_SUFFIX_RE.sub("", name).strip()
        if stripped != name:
            query = stripped
            resolved_via = "reprint_suffix_stripped"

    parsed, err = search_with_retries(query)

    entry = by_act[name]
    if parsed:
        entry.update(parsed)
        entry["resolved"] = True
        entry["resolved_via"] = resolved_via
        entry["searched_as"] = query if query != name else None
        n_fixed += 1
        tag = f" (as {resolved_via}, query={query!r})" if resolved_via != "direct_retry" else ""
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
print(f"\nFixed this pass: {n_fixed}")
print(f"Still unresolved: {n_still_unresolved}")
print(f"Overall: {n_total_resolved}/{len(sg2)} resolved")
print(f"Saved -> {IDENTIFIERS_PATH}")

if n_still_unresolved:
    print("\nStill-unresolved Acts, with their SG2 combined_score (for deciding whether to chase further):")
    score_by_name = {c["act"]: c["combined_score"] for c in sg2}
    remaining = sorted(
        (d for d in identifiers if not d.get("resolved")),
        key=lambda d: -score_by_name.get(d["act"], 0),
    )
    for d in remaining:
        print(f"  {score_by_name.get(d['act']):>4}  {d['act']!r}")