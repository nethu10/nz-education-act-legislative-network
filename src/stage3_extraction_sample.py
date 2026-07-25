"""
Stage 3: run the validated extraction prompt across a spot-check sample
before committing to the full ~1700-record run. Includes retry logic so
a single timeout doesn't kill the whole batch, and saves progress
incrementally so a crash partway through doesn't lose completed work.
"""

import json
import random
import time
from pathlib import Path
from extraction_utils import extract

INPUT_PATH = Path("data/processed/provisions.json")
OUTPUT_PATH = Path("data/processed/extraction_sample.json")
SAMPLE_SIZE = 20
MAX_RETRIES = 2

provisions = json.loads(INPUT_PATH.read_text())

# Stratified-ish sample: mix of ordinary provisions and definitions,
# not just whichever happen to come first in the file.
random.seed(42)  # reproducible sample, not a new random draw every run
ordinary = [p for p in provisions if p["type"] == "provision"]
definitions = [p for p in provisions if p["type"] == "definition"]
sample = random.sample(ordinary, 14) + random.sample(definitions, 6)
random.shuffle(sample)

results = []
failures = []

for i, record in enumerate(sample, 1):
    print(f"[{i}/{len(sample)}] {record['id']} ({record['type']}) ...", end=" ")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            extracted = extract(record["heading"], record["text"])
            results.append({"provision_id": record["id"], "extraction": extracted})
            print("ok")
            break
        except Exception as e:
            print(f"attempt {attempt} failed ({type(e).__name__})", end="; ")
            if attempt == MAX_RETRIES:
                failures.append({"provision_id": record["id"], "error": str(e)})
                print("giving up")
            else:
                time.sleep(2)

OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"\nDone. {len(results)} succeeded, {len(failures)} failed out of {len(sample)}.")
if failures:
    print("Failed IDs:", [f["provision_id"] for f in failures])