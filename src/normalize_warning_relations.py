"""
Normalize the 4 non-standard relation types found during full extraction
to the nearest category in the validated five-type taxonomy, based on
manual review of their actual content. A disclosed, minimal correction
applied only to these known records — not a re-extraction.

  'title'       -> 'cross_reference'  (an internal fact about this Act's
                    own name — same treatment as the Commencement provision)
  'repeal'      -> 'amendment'        (the most complete form of a formal
                    change to another Act's legal status)
  'consequence' -> 'power_or_duty'    (still a power the Minister holds,
                    conditionally triggered by non-compliance)
"""

import json
from pathlib import Path

NORMALIZATION_MAP = {"title": "cross_reference", "repeal": "amendment", "consequence": "power_or_duty"}

results = json.loads(Path("data/processed/extractions_full.json").read_text())

changed = 0
for r in results:
    for rel in r["extraction"].get("relations", []):
        if isinstance(rel, dict) and rel.get("type") in NORMALIZATION_MAP:
            old = rel["type"]
            rel["type"] = NORMALIZATION_MAP[old]
            changed += 1
            print(f"{r['provision_id']}: '{old}' -> '{rel['type']}'")

Path("data/processed/extractions_full.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n{changed} relation(s) normalized and saved.")