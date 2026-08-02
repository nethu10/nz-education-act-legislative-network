"""
Check whether LMS729725's empty text is an isolated case or a real gap
in Stage 2's parsing — before drawing any conclusion about the SLM's
behavior on it.
"""

import json
from pathlib import Path

provisions = json.loads(Path("data/processed/provisions.json").read_text())

empty_or_short = [p for p in provisions if len(p.get("text", "").strip()) < 20]
print(f"Total provisions: {len(provisions)}")
print(f"Provisions with empty or near-empty text (<20 chars): {len(empty_or_short)}")
for p in empty_or_short[:10]:
    print(f"  {p['id']} | {p['heading']!r} | text={p['text']!r}")