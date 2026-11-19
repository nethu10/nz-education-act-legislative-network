"""
sg2_step7_resolve_sample_v2.py

v1's link.aspx returned a uniform 404 across all 15 sample ids -- that's
a signal the endpoint itself is wrong, not that the ids are bad (a
per-id failure would show a mix of results, not 100% identical 404s).
Testing both candidate resolver endpoints side-by-side against the same
small sample to find out which one (if either) actually works via a
plain requests.get() call, since we know at least one URL worked when
opened directly in a real browser.
"""
import json
import time
from pathlib import Path
import requests

UNIQUE_IDS_PATH = Path("data/processed/sg2_unique_citation_ids.json")

CANDIDATES = [
    "https://www.legislation.govt.nz/link.aspx?id={id}",
    "https://www.legislation.govt.nz/pdfLink.aspx?id={id}",
]
DELAY_SECONDS = 0.5

with open(UNIQUE_IDS_PATH) as f:
    unique_ids = json.load(f)

sample = [r["id"] for r in unique_ids[:5]]
print(f"Testing {len(CANDIDATES)} resolver patterns on {len(sample)} ids: {sample}")
print()

for template in CANDIDATES:
    print(f"=== {template} ===")
    for id_ in sample:
        url = template.format(id=id_)
        try:
            resp = requests.get(url, timeout=10, allow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0 (Nethmi-Unitec-Thesis-Research/1.0)"})
            print(f"  {id_}: status={resp.status_code}, final_url={resp.url}, content-type={resp.headers.get('content-type')}")
        except Exception as e:
            print(f"  {id_}: FAILED ({type(e).__name__}: {e})")
        time.sleep(DELAY_SECONDS)
    print()