"""
Full, untruncated view of the borderline cross_reference cases, since
the earlier diagnostic cut text off at 350 characters — need to see
whether the reference-bearing content was just past that cutoff.
"""

import json
from pathlib import Path

provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}
extractions = {e["provision_id"]: e["extraction"] for e in json.loads(Path("data/processed/extractions_full.json").read_text())}

for pid in ["LMS997662", "LMS997664", "LMS325621", "LMS729725"]:
    print("=" * 70)
    print(pid, "-", provisions.get(pid, {}).get("heading"))
    print("=" * 70)
    print("FULL text:", provisions.get(pid, {}).get("text", "(not found)"))
    print("\nRelations:", json.dumps(extractions.get(pid, {}).get("relations", []), indent=2, ensure_ascii=False))
    print()