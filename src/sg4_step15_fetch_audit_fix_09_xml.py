"""
sg4_step15_fetch_audit_fix_09_xml.py

Run on the Mac (legislation.govt.nz's WAF blocks the cloud workspace).
Downloads raw XML for the 39 entries resolved by audit_fix_09 into
data/raw/sg4_targets/, skipping files already present, and validates each
(well-formed XML, year/number attribute match).
"""
import json, time, sys
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
sys.path.insert(0, "src")
from sg4_filenames import filename_for_sg4

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "application/xml,*/*"}
OUT = Path("data/raw/sg4_targets"); OUT.mkdir(parents=True, exist_ok=True)
ids = json.load(open("data/processed/sg4_act_identifiers.json", encoding="utf-8"))
todo = [d for d in ids if d.get("resolved_via") == "audit_fix_09_manual_verified"]
print(len(todo), "entries")
bad = []
for d in todo:
    fn = OUT / filename_for_sg4(d)
    if fn.exists() and fn.stat().st_size > 1000:
        print("skip", fn.name); continue
    for attempt in range(3):
        try:
            r = requests.get(d["xml_url"], headers=HEADERS, timeout=60)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                num = root.get("act.no") or root.get("sr.no") or root.get("sr.number")
                yr = root.get("year") or root.get("sr.year")
                ok = (str(yr) == str(d["year"]) and str(num) == str(d["number"]))
                fn.write_bytes(r.content)
                print("ok " if ok else "ATTR-MISMATCH", fn.name, len(r.content), (yr, num))
                if not ok: bad.append((d["act"], yr, num))
                break
            print("HTTP", r.status_code, d["xml_url"])
        except Exception as e:
            print("err", e)
        time.sleep(2 * (attempt + 1))
    else:
        bad.append((d["act"], "fetch failed", None))
    time.sleep(1)
print("\nProblems:", bad or "none")
