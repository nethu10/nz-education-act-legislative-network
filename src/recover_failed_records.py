"""
Retry the small number of records that failed in the full extraction run,
now that validate_extraction has been made defensive rather than crash-prone.
"""

import json
from pathlib import Path
from extraction_utils import extract, validate_extraction

FAILED_IDS = ["LMS267770", "LMS272870"]

provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}
results = json.loads(Path("data/processed/extractions_full.json").read_text())
warnings_log = json.loads(Path("data/processed/extraction_warnings.json").read_text())
done_ids = {r["provision_id"] for r in results}

for fid in FAILED_IDS:
    if fid in done_ids:
        print(f"{fid} already present, skipping.")
        continue
    p = provisions[fid]
    print(f"Retrying {fid} ...", end=" ")
    try:
        extracted = extract(p["heading"], p["text"])
        warnings = validate_extraction(extracted)
        if warnings:
            warnings_log.append({"provision_id": fid, "warnings": warnings})
        results.append({"provision_id": fid, "extraction": extracted})
        print(f"ok" + (f" ({len(warnings)} warning(s))" if warnings else ""))
    except Exception as e:
        print(f"still failing ({type(e).__name__}): {e}")

Path("data/processed/extractions_full.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
Path("data/processed/extraction_warnings.json").write_text(json.dumps(warnings_log, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nTotal records: {len(results)} / {len(provisions)}")