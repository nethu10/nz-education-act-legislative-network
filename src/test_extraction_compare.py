"""
Stage 3, third test: re-run the Commencement provision with the refined
prompt (checking the type label improves), and test a genuine citation
case for comparison, since Commencement is an atypical provision.
"""

import json
from pathlib import Path
from extraction_utils import extract

provisions = json.loads(Path("data/processed/provisions.json").read_text())

commencement = next(p for p in provisions if p["id"] == "LMS170679")

citation_candidates = [
    p for p in provisions
    if p["type"] == "provision"
    and len(p["external_refs"]) >= 1
    and len(p["text"]) < 500
    and p["id"] != commencement["id"]  # exclude the record we already tested
]
print(f"Found {len(citation_candidates)} candidates with a real external_ref (citation to another Act), excluding Commencement.")
citation_case = citation_candidates[0]

for label, record in [("COMMENCEMENT (retest)", commencement), ("CITATION CASE (new)", citation_case)]:
    print("\n" + "=" * 60)
    print(label)
    print("=" * 60)
    print("Text:", record["text"][:200])
    result = extract(record["heading"], record["text"])
    print("\nResult:")
    print(json.dumps(result, indent=2, ensure_ascii=False))