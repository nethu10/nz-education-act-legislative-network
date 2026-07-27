"""
Stage 3: full extraction run across all ~1700 provisions and definitions.
Saves progress incrementally and can resume if interrupted — this run
is long enough that losing partial progress would be costly.
"""

import json
import time
from pathlib import Path
from extraction_utils import extract, validate_extraction

INPUT_PATH = Path("data/processed/provisions.json")
OUTPUT_PATH = Path("data/processed/extractions_full.json")
WARNINGS_PATH = Path("data/processed/extraction_warnings.json")
MAX_RETRIES = 2
SAVE_EVERY = 50

provisions = json.loads(INPUT_PATH.read_text())

results = []
done_ids = set()
if OUTPUT_PATH.exists():
    results = json.loads(OUTPUT_PATH.read_text())
    done_ids = {r["provision_id"] for r in results}
    print(f"Resuming: {len(done_ids)} records already completed, skipping those.")

warnings_log = []
if WARNINGS_PATH.exists():
    warnings_log = json.loads(WARNINGS_PATH.read_text())

failures = []
remaining = [p for p in provisions if p["id"] not in done_ids]
print(f"{len(remaining)} records remaining out of {len(provisions)} total.")

start_time = time.time()

for i, record in enumerate(remaining, 1):
    print(f"[{i}/{len(remaining)}] {record['id']} ({record['type']}) ...", end=" ")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            extracted = extract(record["heading"], record["text"])
            warnings = validate_extraction(extracted)
            if warnings:
                warnings_log.append({"provision_id": record["id"], "warnings": warnings})
                print(f"ok ({len(warnings)} warning(s))")
            else:
                print("ok")
            results.append({"provision_id": record["id"], "extraction": extracted})
            break
        except Exception as e:
            print(f"attempt {attempt} failed ({type(e).__name__})", end="; ")
            if attempt == MAX_RETRIES:
                failures.append({"provision_id": record["id"], "error": str(e)})
                print("giving up")
            else:
                time.sleep(2)

    if i % SAVE_EVERY == 0 or i == len(remaining):
        OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        WARNINGS_PATH.write_text(json.dumps(warnings_log, indent=2, ensure_ascii=False), encoding="utf-8")
        elapsed = time.time() - start_time
        rate = i / elapsed
        eta_min = ((len(remaining) - i) / rate) / 60 if rate > 0 else 0
        print(f"  --- saved progress ({i}/{len(remaining)}), ~{eta_min:.0f} min remaining ---")

print(f"\nDone. {len(results)} total succeeded, {len(failures)} failed, {len(warnings_log)} had validation warnings.")
if failures:
    print("Failed IDs:", [f["provision_id"] for f in failures])