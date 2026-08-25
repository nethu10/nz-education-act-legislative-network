"""
Stage 6, step 1: pull the exact (year, act number) out of each of the
13 target Act names, using the "(YYYY No NNN)" pattern already present
in the data -- so we can build correct download URLs for each one,
the same way Stage 1 did for the seed Act.
"""

import json
import re
from pathlib import Path

TARGET_ACTS = [
    "Crown Entities Act 2004 (2004 No 115)",
    "Treaty of Waitangi Act 1975 (1975 No 114)",
    "Social Security Act 2018 (2018 No 32)",
    "Income Tax Act 2007 (2007 No 97)",
    "Public Bodies Contracts Act 1959 (1959 No 98)",
    "Student Loan Scheme Act 2011 (2011 No 62)",
    "Employment Relations Act 2000 (2000 No 24)",
    "Lincoln University Act 1961 (1961 No 52)",
    "Massey University Act 1963 (1963 No 7)",
    "University of Auckland Act 1961 (1961 No 50)",
    "University of Canterbury Act 1961 (1961 No 49)",
    "University of Waikato Act 1963 (1963 No 8)",
    "Victoria University of Wellington Act 1961 (1961 No 51)",
]

identifiers = []
for name in TARGET_ACTS:
    match = re.search(r"\((\d{4}) No (\d+)\)", name)
    if match:
        year, number = match.group(1), match.group(2)
        identifiers.append({"name": name, "year": year, "number": number})
        print(f"OK    {name}  ->  year={year}, number={number}")
    else:
        print(f"FAILED to extract identifier from: {name}")

print(f"\nSuccessfully identified {len(identifiers)} of {len(TARGET_ACTS)} Acts.")

Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/processed/stage6_target_acts.json").write_text(
    json.dumps(identifiers, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("Saved to data/processed/stage6_target_acts.json")