"""
Stage 6, step 2: download the XML for each of the 13 target Acts,
using the same URL pattern and pinned date as Stage 1 -- so the
expanded network represents one coherent snapshot in time, not a mix
of different download dates.
"""

import json
import time
import requests
from pathlib import Path

VERSION_DATE = "latest"  # Tried same pin as the seed Act but changed it to latest
RAW_DIR = Path("data/raw/stage6_targets")
RAW_DIR.mkdir(parents=True, exist_ok=True)

targets = json.loads(Path("data/processed/stage6_target_acts.json").read_text())

results = []

for t in targets:
    url = f"https://legislation.govt.nz/act/public/{t['year']}/{t['number']}/en/{VERSION_DATE}.xml"
    headers = {"User-Agent": "Nethmi-Unitec-Thesis-Research/1.0"}

    print(f"Fetching {t['name']} ...", end=" ")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200 and response.text.strip().startswith("<?xml"):
            safe_filename = f"{t['year']}_{t['number']}.xml"
            out_path = RAW_DIR / safe_filename
            out_path.write_text(response.text, encoding="utf-8")
            print(f"OK ({len(response.text):,} chars) -> {out_path}")
            results.append({**t, "status": "success", "chars": len(response.text), "file": str(out_path)})
        else:
            print(f"FAILED (status {response.status_code})")
            results.append({**t, "status": "failed", "http_status": response.status_code})
    except Exception as e:
        print(f"FAILED ({type(e).__name__}: {e})")
        results.append({**t, "status": "failed", "error": str(e)})

    time.sleep(1.5)  # polite pause between requests

succeeded = [r for r in results if r["status"] == "success"]
failed = [r for r in results if r["status"] != "success"]

print(f"\n{len(succeeded)} of {len(targets)} succeeded.")
if failed:
    print("Failed:")
    for f in failed:
        print(f"  {f['name']}")

Path("data/processed/stage6_fetch_results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)