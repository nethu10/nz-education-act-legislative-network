"""
Stage 3, second test: run extraction on a genuinely harder provision —
one with multiple real cross-references — before scaling to the full
dataset.
"""

import json
from pathlib import Path
from extraction_utils import extract

provisions = json.loads(Path("data/processed/provisions.json").read_text())

# A real stress test: an ordinary provision with 2+ internal references,
# kept reasonably short so we can read the result easily.
candidates = [
    p for p in provisions
    if p["type"] == "provision" and len(p["internal_refs"]) >= 2 and len(p["text"]) < 800
]
print(f"Found {len(candidates)} candidate provisions with 2+ internal refs.")

test_record = candidates[0]
print("\nTesting on:")
print(json.dumps(test_record, indent=2, ensure_ascii=False))

result = extract(test_record["heading"], test_record["text"])

print("\nExtraction result:")
print(json.dumps(result, indent=2, ensure_ascii=False))

print(f"\nStage 2 structurally captured {len(test_record['internal_refs'])} internal_refs: {test_record['internal_refs']}")
print(f"The SLM found {len(result['relations'])} relations. Do these plausibly correspond to each other?")