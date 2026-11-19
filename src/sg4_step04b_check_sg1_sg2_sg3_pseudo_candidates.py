"""
sg4_step04b_check_sg1_sg2_sg3_pseudo_candidates.py

Diagnostic only. Checks whether the same "Section N" / "Clause N"
pseudo-candidate pattern (found contaminating SG4) also made it into
SG1, SG2, or SG3 membership -- i.e. whether any earlier layer's
citation-extraction step had the same false-positive bug and let a
bare section/clause cross-reference get promoted as if it were a
real Act.
"""
import json
import re
from pathlib import Path

SG1_PATH = Path("data/processed/sg1_final_list.json")
SG2_PATH = Path("data/processed/sg2_final_list.json")
SG3_PATH = Path("data/processed/sg3_final_list.json")

SECTION_CLAUSE_RE = re.compile(r"^(section|clause)\s+\d+[a-z]*$", re.IGNORECASE)

for label, path in [("SG1", SG1_PATH), ("SG2", SG2_PATH), ("SG3", SG3_PATH)]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    hits = [d.get("act") for d in data if SECTION_CLAUSE_RE.match((d.get("act") or "").strip())]
    print(f"{label}: {len(data)} Acts, {len(hits)} pseudo-candidate matches")
    for h in hits:
        print(f"    {h!r}")