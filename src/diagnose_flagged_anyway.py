"""
Look at real examples of provisions the SLM flagged as citation/
cross_reference/amendment despite the XML showing no tagged reference,
to test the hypothesis that these are prose citations to other Acts
that the government's own XML simply didn't hyperlink.
"""

import json
from pathlib import Path

provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}
extractions = {e["provision_id"]: e["extraction"] for e in json.loads(Path("data/processed/extractions_full.json").read_text())}

REF_BACKED_TYPES = {"citation", "cross_reference", "amendment"}

examples = []
for pid, prov in provisions.items():
    has_structural_ref = bool(prov.get("internal_refs")) or bool(prov.get("external_refs"))
    if has_structural_ref:
        continue
    extraction = extractions.get(pid)
    if not extraction:
        continue
    relations = extraction.get("relations", [])
    flagged = [r for r in relations if isinstance(r, dict) and r.get("type") in REF_BACKED_TYPES]
    if flagged:
        examples.append((pid, prov, flagged))

print(f"Total flagged-anyway provisions: {len(examples)}\n")

for pid, prov, flagged in examples[:8]:
    print("=" * 70)
    print(pid, "-", prov.get("heading"))
    print("=" * 70)
    print("Text:", prov.get("text", "")[:350])
    print("\nFlagged relation(s):")
    print(json.dumps(flagged, indent=2, ensure_ascii=False))
    print()