"""
Checks whether "1989 Act" (score 8, in the SG1 candidate list) and
"Education Act 1989" (seen at score 2 in the full ranking) are actually
the same law extracted under two different citation-derived names --
a normalization gap the name-matching step didn't catch, since the
two strings share no obvious common substring pattern.
"""

import json
from pathlib import Path

final = json.loads(Path("data/processed/sg1_ranking_cleaned.json").read_text())

for name in ["1989 Act", "Education Act 1989"]:
    matches = [r for r in final if r["act"] == name]
    for m in matches:
        print(f"{name}: {m}")

# Look at the actual citation source text behind each, to confirm they're
# really the same underlying law before merging anything
citations = json.loads(Path("data/processed/citation_relationships_final.json").read_text())
print("\n--- Real source descriptions behind '1989 Act' citations ---")
for r in citations:
    if r["act_name"].strip() == "1989 Act":
        print(f"  {r['provision_id']}: \"{r['description']}\"")

print("\n--- Real source descriptions behind 'Education Act 1989' citations ---")
for r in citations:
    if r["act_name"].strip() == "Education Act 1989":
        print(f"  {r['provision_id']}: \"{r['description']}\"")