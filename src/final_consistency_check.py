import json
from pathlib import Path
provisions = json.loads(Path("data/processed/provisions.json").read_text())
extractions = json.loads(Path("data/processed/extractions_full.json").read_text())
flagged_ids = {p["id"] for p in provisions if p.get("is_repealed_or_empty")}
extraction_ids = {e["provision_id"] for e in extractions}
all_ids = {p["id"] for p in provisions}
non_flagged_ids = all_ids - flagged_ids
print(f"Total provisions: {len(all_ids)}")
print(f"Flagged repealed/empty: {len(flagged_ids)}")
print(f"Non-flagged: {len(non_flagged_ids)}")
print(f"Records in extractions_full.json: {len(extraction_ids)}")
missing = non_flagged_ids - extraction_ids
print(f"Non-flagged with NO extraction (expect 0): {len(missing)}")
still_present = flagged_ids & extraction_ids
print(f"Flagged but still in extractions (expect 0): {len(still_present)}")