"""
sg2_step9_resolve_identifiers.py

First half of the SG2-internal-link-finding stage: resolve each of the 437
SG2 Acts (currently just a display name, e.g. "Financial Markets Authority
Act 2011") to its legislation.govt.nz (year, number) identifier, so we can
build a direct XML URL for it the same way stage1_acquisition.py did for
the seed Act.

We already know the working XML-fetch pattern from stage1_acquisition.py's
own trial log:
    https://legislation.govt.nz/act/public/{year}/{number}/en/latest.xml
What we DON'T know yet is the search endpoint's URL/query format -- that's
the actual unknown this script exists to nail down. It tries a short list
of plausible search URLs against the very first SG2 Act only, prints the
raw response status + a slice of the HTML for each, and stops there. Once
we can see which pattern (if any) returns real search-results markup, the
follow-up script scales that pattern across all 437 Acts in one run.

Run this, then paste the full printed output back -- status codes, and
the HTML slice for whichever pattern looks most like a real results page
(look for repeated occurrences of "/act/public/" or "/act/private/" or
similar hrefs in the slice).
"""
import json
import re
from pathlib import Path
from urllib.parse import quote

import requests

SG2_PATH = Path("data/processed/sg2_final_list.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

with open(SG2_PATH, encoding="utf-8") as f:
    sg2 = json.load(f)

test_act = sg2[0]["act"]
print(f"Test Act: {test_act!r}\n")

q = quote(test_act)
candidate_urls = [
    f"https://www.legislation.govt.nz/search/results?search=y_all%40text%3D{q}&p=1",
    f"https://www.legislation.govt.nz/search/results?search={q}",
    f"https://www.legislation.govt.nz/results?search={q}",
    f"https://www.legislation.govt.nz/act/search/results?search={q}",
    f"https://www.legislation.govt.nz/search?q={q}",
]

DOC_HREF_RE = re.compile(
    r'href="(/(?:act|regulation|rule|order|notice)/(?:public|private|local)/\d{4}/\d+[^"]*)"'
)

for url in candidate_urls:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        hits = DOC_HREF_RE.findall(r.text)
        print(f"Tried {url}")
        print(f"  -> status {r.status_code}, final URL {r.url}, {len(r.text)} chars, "
              f"{len(hits)} document-like hrefs found")
        if hits:
            print(f"  first few hrefs: {hits[:5]}")
        else:
            # show a slice so we can eyeball what came back (error page? JS shell? redirect?)
            snippet = re.sub(r"\s+", " ", r.text)[:400]
            print(f"  snippet: {snippet}")
        print()
    except Exception as e:
        print(f"Tried {url}")
        print(f"  -> ERROR {type(e).__name__}: {e}\n")
