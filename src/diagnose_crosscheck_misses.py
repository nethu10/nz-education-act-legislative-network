"""
Look at the real content of the 5 "missed" examples from the structural
cross-check — full provision text, its structural refs, and exactly what
the SLM extracted — to find out whether these are genuine recall misses
or references correctly folded into a power_or_duty / definition_reference
relation instead.
"""

import json
from pathlib import Path

provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}
extractions = {e["provision_id"]: e["extraction"] for e in json.loads(Path("data/processed/extractions_full.json").read_text())}

MISSED_IDS = ["LMS256361"]

for pid in MISSED_IDS:
    prov = provisions.get(pid, {})
    extraction = extractions.get(pid, {})
    print("=" * 70)
    print(pid, "-", prov.get("heading"))
    print("=" * 70)
    print("Text:", prov.get("text", "")[:300])
    print("internal_refs:", prov.get("internal_refs"))
    print("external_refs:", prov.get("external_refs"))
    print("\nSLM relations found:")
    print(json.dumps(extraction.get("relations", []), indent=2, ensure_ascii=False))
    print()