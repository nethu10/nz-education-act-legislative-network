import json
from pathlib import Path
provisions = json.loads(Path("data/processed/provisions.json").read_text())
flagged = [p for p in provisions if p.get("is_repealed_or_empty")]
print(f"Provisions flagged is_repealed_or_empty: {len(flagged)} (expect 70)")