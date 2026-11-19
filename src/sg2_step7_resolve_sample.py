"""
sg2_step7_resolve_sample.py

Validates the citation-id resolver on a small sample before running it
across all 4,248 unique ids. Tests a mix of DLM and LMS ids, including
some high-frequency ones, and both the "act" and "secondary-legislation"
source types (since we've only confirmed the resolver's behaviour for one
Act so far -- Treaty of Waitangi Act 1975 via DLM435834 -- and secondary
legislation citations may resolve to a differently-shaped URL).

Prints the raw resolved URL for each id rather than trying to parse it
yet, so we can see the real shape of both URL types before writing the
parsing logic for the full run.
"""
import json
import time
from pathlib import Path
import requests

UNIQUE_IDS_PATH = Path("data/processed/sg2_unique_citation_ids.json")

RESOLVER_URL = "https://www.legislation.govt.nz/link.aspx?id={id}"
SAMPLE_SIZE = 15
DELAY_SECONDS = 0.5

with open(UNIQUE_IDS_PATH) as f:
    unique_ids = json.load(f)

# mix: a few of the highest-frequency ids, a few mid-frequency, a few low
high = [r["id"] for r in unique_ids[:5]]
mid = [r["id"] for r in unique_ids[len(unique_ids)//2 : len(unique_ids)//2 + 5]]
low = [r["id"] for r in unique_ids[-5:]]
sample = high + mid + low

print(f"Testing resolver on {len(sample)} ids: {sample}")
print()

for id_ in sample:
    url = RESOLVER_URL.format(id=id_)
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True,
                             headers={"User-Agent": "Nethmi-Unitec-Thesis-Research/1.0"})
        print(f"{id_}: status={resp.status_code}, final_url={resp.url}")
    except Exception as e:
        print(f"{id_}: FAILED ({type(e).__name__}: {e})")
    time.sleep(DELAY_SECONDS)