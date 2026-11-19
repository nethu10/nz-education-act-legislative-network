"""
sg4_step17_fetch_collision_override_xml.py  (run on the Mac, project root)

Downloads the XML for the 14 SG4 filename-collision documents that use a
disambiguated filename (SG4_FILENAME_OVERRIDES) and are still missing on disk.
Validates year/number from the root element before saving.
"""
import json, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
sys.path.insert(0, "src")
from sg4_filenames import SG4_FILENAME_OVERRIDES

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "application/xml,*/*"}
OUT = Path("data/raw/sg4_targets")
ids = {d["act"]: d for d in json.load(open("data/processed/sg4_act_identifiers.json", encoding="utf-8"))}
bad = []
for act, fn in SG4_FILENAME_OVERRIDES.items():
    dest = OUT / fn
    if dest.exists() and dest.stat().st_size > 1000:
        print("have", fn); continue
    d = ids.get(act)
    if not d or not d.get("xml_url"):
        print("NO ENTRY/URL", act); bad.append(act); continue
    for attempt in range(3):
        try:
            r = requests.get(d["xml_url"], headers=HEADERS, timeout=60)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                num = root.get("act.no") or root.get("sr.no")
                ok = str(root.get("year")) == str(d["year"]) and str(num) == str(d["number"])
                dest.write_bytes(r.content)
                print("ok " if ok else "ATTR-MISMATCH", fn, len(r.content), (root.get("year"), num))
                if not ok: bad.append(act)
                break
            print("HTTP", r.status_code, d["xml_url"])
        except Exception as e:
            print("err", e)
        time.sleep(2 * (attempt + 1))
    else:
        bad.append(act)
    time.sleep(1)
print("Problems:", bad or "none")
