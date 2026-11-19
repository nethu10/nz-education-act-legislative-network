"""
sg2_step8_merge_and_finalize.py

Merges the amendment-based and citation-based SG2 candidate pools into
one combined_score per Act (same as SG1: all signal types summed), then
excludes the seed Act, anything already in SG1, and the hub/boilerplate
Acts confirmed on either side of the pipeline:
  - Income Tax Act 2007 / Tax Administration Act 1994 (amendment hubs,
    also heavily-cited targets)
  - Legislation Act 2019 / Legislation Act 2012 (citation-side hubs --
    NZ's "Act about Acts", cited as drafting boilerplate)
  - Public Service Act 2020 / Secondary Legislation Act 2021 (confirmed
    bulk single-event Acts, same exclusion as at SG1/amendment side)

Fix: normalize() now also collapses curly apostrophes (\u2019/\u2018) to
straight ones before comparing/merging names. Without this,
"Veterans' Support Act 2014" (straight apostrophe, from the amendment
side) and "Veterans' Support Act 2014" (curly apostrophe, from the
citation side) were treated as two different Acts, splitting their true
combined score across two entries. Worse, since sg1_final_list.json
itself uses curly apostrophes (e.g. "Children's Act 2014"), a
straight-apostrophe version of an SG1 Act produced by either extraction
step could have silently failed the "already in SG1" exclusion check and
been wrongly admitted as a "new" SG2 candidate.
"""
import json
import re
from pathlib import Path
from collections import defaultdict

AMENDMENT_PATH = Path("data/processed/sg2_cleaned_candidates.json")
CITATION_PATH = Path("data/processed/sg2_citation_candidates.json")
SG1_PATH = Path("data/processed/sg1_final_list.json")
OUTPUT_PATH = Path("data/processed/sg2_combined_final_list.json")

SEED = "Education and Training Act 2020"

EXTRA_EXCLUDED = {
    "Income Tax Act 2007",
    "Tax Administration Act 1994",
    "Legislation Act 2019",
    "Legislation Act 2012",
    "Public Service Act 2020",
    "Secondary Legislation Act 2021",
}

CITE_PATTERN = re.compile(
    r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$"
)

def normalize(name):
    if not name:
        return name
    name = name.replace("\u2019", "'").replace("\u2018", "'")  # curly apostrophes -> straight
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()

with open(SG1_PATH) as f:
    sg1_acts = json.load(f)
sg1_names = {normalize(a["act"]) for a in sg1_acts}

with open(AMENDMENT_PATH) as f:
    amendment_candidates = json.load(f)
with open(CITATION_PATH) as f:
    citation_candidates = json.load(f)

combined = defaultdict(lambda: {"amendment_score": 0, "citation_score": 0, "linked_from": set()})

for c in amendment_candidates:
    name = normalize(c["act"])
    combined[name]["amendment_score"] += c.get("combined_score", 0)
    combined[name]["linked_from"].update(c.get("linked_from", []))

for c in citation_candidates:
    name = normalize(c["act"])
    combined[name]["citation_score"] += c.get("combined_score", 0)
    combined[name]["linked_from"].update(c.get("linked_from", []))

final = []
excluded_count = 0
for name, data in combined.items():
    if name == SEED or name in sg1_names or name in EXTRA_EXCLUDED:
        excluded_count += 1
        continue
    total = data["amendment_score"] + data["citation_score"]
    final.append({
        "act": name,
        "amendment_score": data["amendment_score"],
        "citation_score": data["citation_score"],
        "combined_score": total,
        "linked_from": sorted(data["linked_from"]),
    })

final.sort(key=lambda c: -c["combined_score"])

print(f"Union of amendment + citation candidates: {len(combined)}")
print(f"Excluded (seed / already in SG1 / hub or boilerplate): {excluded_count}")
print(f"Remaining SG2 candidates (combined signal): {len(final)}")
print()

print("Score distribution (combined amendment + citation):")
for t in [30, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1]:
    n = sum(1 for c in final if c["combined_score"] >= t)
    print(f"  score >= {t:>3}: {n:>4} Acts")

print()
print("Top 40 combined candidates:")
for c in final[:40]:
    print(f"  {c['act']}  (combined {c['combined_score']} = amend {c['amendment_score']} + cite {c['citation_score']}, {len(c['linked_from'])} links)")

with open(OUTPUT_PATH, "w") as f:
    json.dump(final, f, indent=2)
print(f"\nSaved -> {OUTPUT_PATH}")