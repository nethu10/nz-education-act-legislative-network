"""
sg2_step15_merge_and_finalize_sg3.py

The SG3 sequel to sg2_step8_merge_and_finalize.py: merges the cleaned
amendment-side SG3 pool (sg2_step14's output) with the raw citation-side
SG3 pool (sg2_step12's output, data/processed/sg3_citation_candidates.json)
into one combined_score per Act, then excludes:
  - the seed Act
  - all 37 SG1 Acts
  - all 422 SG2 Acts (the exclusion category specific to this layer --
    nothing already counted at an earlier layer gets to count again)
  - the same hub/boilerplate Acts confirmed at SG1/SG2 (Income Tax Act
    2007, Tax Administration Act 1994, Legislation Act 2019, Legislation
    Act 2012 -- the first three are already covered by the SG1 exclusion
    since they're SG1 Acts themselves, kept here as a defensive no-op --
    plus Public Service Act 2020 / Secondary Legislation Act 2021, which
    are NOT SG1 or SG2 Acts, having been excluded at those stages too,
    so they resurface here and need excluding again)

WHY resolve_canonical() (not just normalize()) IS NEEDED HERE
-------------------------------------------------------------------
sg3_citation_candidates.json was built by sg2_step12, which extracts
citation target names as literal text and has no awareness of
sg2_step13's rename map. A check found 13 of the 15 renamed/removed SG2
identifier-collision names (e.g. "Healthy Futures (Pae Ora) Act 2022",
score 70; "Injury Prevention, Rehabilitation, and Compensation Act 2001",
score 15) appearing as raw citation TARGETS in that file. Every one of
these is the historical/old name of an Act that IS now in
sg2_final_list.json under its canonical name -- without resolving them
first, they would incorrectly survive the "already in SG2" exclusion
check (simple normalize() alone doesn't map an old name to its current
one) and inflate the SG3 candidate pool with Acts that are already
accounted for in SG2. The amendment-side pool doesn't have this problem
(sg2_step11 already resolves through the rename map before writing
sg2_new_candidates_seen.json), but the citation-side pool does, so
resolve_canonical() is applied to both here for consistency and safety.
"""
import json
import re
from pathlib import Path
from collections import defaultdict

AMENDMENT_PATH = Path("data/processed/sg3_cleaned_amendment_candidates.json")
CITATION_PATH = Path("data/processed/sg3_citation_candidates.json")
SG1_PATH = Path("data/processed/sg1_final_list.json")
SG2_PATH = Path("data/processed/sg2_final_list.json")
OUTPUT_PATH = Path("data/processed/sg3_combined_final_list.json")

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
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()

# ---- same rename map as sg2_step13/sg2_step11, for resolving old SG2
# identifier-collision names encountered as raw citation-side text ----
RENAME_MAP = {
    "Schedule 32 of the Social Security Act 1964": "Social Security Act 1964",
    "Schedule 1 of the New Zealand Superannuation and Retirement Income Act 2001":
        "New Zealand Superannuation and Retirement Income Act 2001",
    "Schedule 1AA of the New Zealand Superannuation and Retirement Income Act 2001":
        "New Zealand Superannuation and Retirement Income Act 2001",
    "Injury Prevention, Rehabilitation, and Compensation Act 2001": "Accident Compensation Act 2001",
    "Healthy Futures (Pae Ora) Act 2022": "Pae Ora (Healthy Futures) Act 2022",
    "Housing Restructuring and Tenancy Matters Act 1992": "Public and Community Housing Management Act 1992",
    "State Sector Act 1988 (RS Vol 33, p 715)": "State Sector Act 1988",
    "New Zealand Act 2021": "Reserve Bank of New Zealand Act 2021",
    "Schedule 1 of the Ombudsmen Act 1975": "Ombudsmen Act 1975",
    "Oranga Tamariki System Legislation Amendment Act 2025":
        "Oversight of Oranga Tamariki System Legislation Amendment Act 2025",
    "Waitangi Day and ANZAC Day) Amendment Act 2013":
        "Holidays (Full Recognition of Waitangi Day and ANZAC Day) Amendment Act 2013",
    "Support Workers (Pay Equity) Settlements Act 2017":
        "Care and Support Workers (Pay Equity) Settlement Act 2017",
    "Schedule 2 of the Public Service Act 2020": None,
    "Schedule 6 of the Public Service Act 2020": None,
    "Schedule 1 of the Privacy Act 2020": None,
}

def resolve_canonical(name):
    n = normalize(name)
    if n in RENAME_MAP:
        return RENAME_MAP[n]
    return n

with open(SG1_PATH) as f:
    sg1_acts = json.load(f)
sg1_names = {normalize(a["act"]) for a in sg1_acts}

with open(SG2_PATH) as f:
    sg2_acts = json.load(f)
sg2_names = {normalize(c["act"]) for c in sg2_acts}

with open(AMENDMENT_PATH) as f:
    amendment_candidates = json.load(f)
with open(CITATION_PATH) as f:
    citation_candidates = json.load(f)

combined = defaultdict(lambda: {"amendment_score": 0, "citation_score": 0, "linked_from": set()})
dropped_as_fragment = 0

for c in amendment_candidates:
    name = resolve_canonical(c["act"])
    if name is None:
        dropped_as_fragment += 1
        continue
    combined[name]["amendment_score"] += c.get("combined_score", 0)
    combined[name]["linked_from"].update(c.get("linked_from", []))

for c in citation_candidates:
    name = resolve_canonical(c["act"])
    if name is None:
        dropped_as_fragment += 1
        continue
    combined[name]["citation_score"] += c.get("combined_score", 0)
    combined[name]["linked_from"].update(c.get("linked_from", []))

final = []
excluded_count = 0
excluded_breakdown = defaultdict(int)
for name, data in combined.items():
    if name == SEED:
        excluded_count += 1
        excluded_breakdown["seed"] += 1
        continue
    if name in sg1_names:
        excluded_count += 1
        excluded_breakdown["already_sg1"] += 1
        continue
    if name in sg2_names:
        excluded_count += 1
        excluded_breakdown["already_sg2"] += 1
        continue
    if name in EXTRA_EXCLUDED:
        excluded_count += 1
        excluded_breakdown["hub_or_boilerplate"] += 1
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

print(f"Union of amendment + citation SG3 candidates: {len(combined) + dropped_as_fragment}")
print(f"Dropped as confirmed fragment (RENAME_MAP -> None): {dropped_as_fragment}")
print(f"Excluded (seed / already SG1 / already SG2 / hub or boilerplate): {excluded_count}")
for reason, n in excluded_breakdown.items():
    print(f"  - {reason}: {n}")
print(f"Remaining SG3 candidates (combined signal): {len(final)}")
print()

print("Score distribution (combined amendment + citation), with marginal counts:")
thresholds = [50, 30, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1]
counts = [sum(1 for c in final if c["combined_score"] >= t) for t in thresholds]
prev = 0
for t, n in zip(thresholds, counts):
    print(f"  score >= {t:>3}: {n:>4} Acts   (+{n - prev} vs next threshold up)")
    prev = n

print()
print("Top 40 combined SG3 candidates:")
for c in final[:40]:
    print(f"  {c['act']}  (combined {c['combined_score']} = amend {c['amendment_score']} + cite {c['citation_score']}, {len(c['linked_from'])} links)")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(final, f, indent=2, ensure_ascii=False)
print(f"\nSaved -> {OUTPUT_PATH}")