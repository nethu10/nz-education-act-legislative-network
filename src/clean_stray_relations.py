"""
Remove non-dict "relations" entries (stray text fragments the model
occasionally leaves behind, like the trailing 'summary): ' seen in
LMS272870) from the full extraction dataset. The six genuine relations
in each affected record are left untouched — this only strips junk.
"""

import json
from pathlib import Path

path = Path("data/processed/extractions_full.json")
results = json.loads(path.read_text())

cleaned_count = 0
for r in results:
    relations = r["extraction"].get("relations", [])
    clean_relations = [rel for rel in relations if isinstance(rel, dict)]
    if len(clean_relations) != len(relations):
        removed = len(relations) - len(clean_relations)
        print(f"{r['provision_id']}: removed {removed} non-dict relation entr{'y' if removed == 1 else 'ies'}")
        r["extraction"]["relations"] = clean_relations
        cleaned_count += 1

path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n{cleaned_count} record(s) cleaned.")