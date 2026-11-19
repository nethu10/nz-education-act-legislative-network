"""
SG2, step 1: fetch XML for all 37 SG1 Acts -- extended from
stage6_fetch_target_acts.py to also handle secondary legislation
(Regulations/Rules/Orders), which Stage 6 never needed since it only
targeted primary Acts.
"""
import json
import re
import time
import requests
from pathlib import Path

VERSION_DATE = "latest"
RAW_DIR = Path("data/raw/sg2_targets")
RAW_DIR.mkdir(parents=True, exist_ok=True)

sg1_acts = json.loads(Path("data/processed/sg1_final_list.json").read_text())

CITE_PATTERN = re.compile(
    r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$"
)

def parse_citation(full_act_string):
    """Split 'Crown Entities Act 2004 (2004 No 115)' into name + URL path
    prefix + year + number. Returns None if no citation is present
    (e.g. 'Education Act 1989' in your list has none -- fetch that one
    manually)."""
    m = CITE_PATTERN.match(full_act_string.strip())
    if not m:
        return None
    name, cite = m.group(1), m.group(2)
    if cite.startswith(("SR", "LI")):
        path_prefix = "secondary-legislation/pco-drafted"  # untested guess -- this run is the test
        year, number = re.match(r"(?:SR|LI)\s+(\d{4})/(\d+)", cite).groups()
    else:
        path_prefix = "act/public"
        year, number = re.match(r"(\d{4})\s+No\s+(\d+)", cite).groups()
    return {"name": name, "cite": cite, "path_prefix": path_prefix,
            "year": year, "number": number}

def fetch_target_xml(parsed, retries=2):
    url = (f"https://legislation.govt.nz/{parsed['path_prefix']}/"
           f"{parsed['year']}/{parsed['number']}/en/{VERSION_DATE}.xml")
    print(f"    URL: {url}")
    headers = {"User-Agent": "Nethmi-Unitec-Thesis-Research/1.0"}
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200 and response.text.strip().startswith("<?xml"):
                return response.text, None
            return None, f"status {response.status_code}"
        except Exception as e:
            if attempt < retries - 1:
                print("    (timeout, retrying...)")
                time.sleep(2)
                continue
            return None, f"{type(e).__name__}: {e}"

results = []
unparsed = []

for a in sg1_acts:
    parsed = parse_citation(a["act"])
    if parsed is None:
        print(f"SKIPPED (no citation found, needs manual lookup): {a['act']}")
        unparsed.append(a["act"])
        continue

    existing = list(RAW_DIR.glob(f"*_{parsed['year']}_{parsed['number']}.xml"))
    if existing:
        print(f"Already have {parsed['name']} -> {existing[0]}")
        results.append({**parsed, "original": a["act"], "status": "success",
                         "chars": existing[0].stat().st_size, "file": str(existing[0])})
        continue

    print(f"Fetching {parsed['name']} [{parsed['path_prefix']}] ...", end=" ")
    xml_text, error = fetch_target_xml(parsed)

    if xml_text:
        safe_prefix = parsed["path_prefix"].split("/")[0]  # "act" or "secondary-legislation"
        out_path = RAW_DIR / f"{safe_prefix}_{parsed['year']}_{parsed['number']}.xml"
        out_path.write_text(xml_text, encoding="utf-8")
        print(f"OK ({len(xml_text):,} chars) -> {out_path}")
        results.append({**parsed, "original": a["act"], "status": "success",
                         "chars": len(xml_text), "file": str(out_path)})
    else:
        print(f"FAILED ({error})")
        results.append({**parsed, "original": a["act"], "status": "failed", "error": error})

    time.sleep(1.5)

succeeded = [r for r in results if r["status"] == "success"]
failed = [r for r in results if r["status"] != "success"]

print(f"\n{len(succeeded)} of {len(sg1_acts)} succeeded "
      f"({len(unparsed)} skipped for missing citation, {len(failed)} fetch failures).")
if unparsed:
    print("Needs manual citation lookup:", unparsed)
if failed:
    print("Fetch failed:")
    for f in failed:
        print(f"  {f['original']}")

Path("data/processed/sg2_fetch_results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)