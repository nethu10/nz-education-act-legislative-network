"""
Checks the full 186 confirmed citation results for the two specific
error patterns found in manual spot-checking: generic 'regulations'
as an act_name (not a real law name), and accidental self-matches to
the seed Act despite the prompt explicitly excluding it.
"""

import json
from pathlib import Path

results = json.loads(Path("data/processed/citation_relationships_slm.json").read_text())

self_matches = [r for r in results if "education and training act" in r["act_name"].lower()]
generic_matches = [r for r in results if r["act_name"].strip().lower() in ("regulations", "regulation", "the regulations", "rules")]
clean = [r for r in results if r not in self_matches and r not in generic_matches]

print(f"Total confirmed: {len(results)}")
print(f"Self-matches to the seed Act (invalid): {len(self_matches)}")
print(f"Generic 'regulations'/'rules' with no specific name (invalid): {len(generic_matches)}")
print(f"Genuinely clean, specific external Act citations: {len(clean)}")

print("\nDistinct genuinely-named external Acts found:")
distinct_clean_names = sorted(set(r["act_name"] for r in clean))
for name in distinct_clean_names:
    print(f"  {name}")