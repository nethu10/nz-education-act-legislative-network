"""
sg4_step08_audit_sg5_candidates.py

Diagnostic only -- writes nothing. Checks the full 1,044-candidate SG5
pool (sg4_new_candidates_seen.json) for two new contamination patterns
surfaced by the top-20 sanity check, neither caught by the existing
Section/Clause filter:

1. Schedule-heading descriptive phrases mis-captured as citation
   targets (e.g. "Amendments required that are technical or are
   consequential to amendments in this Act") -- same root cause as the
   Section/Clause bug (extract_outgoing_amendments() trusting a
   <heading> element's text), different shape. Heuristic: a real
   Act/Regulation/Order/Rule name virtually always contains a 4-digit
   year somewhere; these descriptive headings don't.

2. Nested-parenthesis Local/Private Act citations -- "Name YYYY (YYYY
   No N (P))" / "(L)" -- which neither CITE_PATTERN nor the generic
   trailing-paren fallback can strip (both assume no parens-within-
   parens), so a real Act cited this way never gets matched against
   already-known Acts. Cross-checked against Seed/SG1/SG2/SG3/SG4 using
   a normalize() that ALSO peels this specific pattern, to see whether
   any are already-known Acts hiding behind this suffix (the same
   check that caught the Crimes Act duplicate).

Also flags a possible extraction-duplication artifact: a name matching
"Act YYYY Amendment Act YYYY" with the same year both times.
"""
import json
import re
from pathlib import Path

SEED = "Education and Training Act 2020"
SG1_PATH = Path("data/processed/sg1_final_list.json")
SG2_PATH = Path("data/processed/sg2_final_list.json")
SG3_PATH = Path("data/processed/sg3_final_list.json")
SG4_PATH = Path("data/processed/sg4_final_list.json")
CANDIDATES_PATH = Path("data/processed/sg4_new_candidates_seen.json")

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
GENERIC_TRAILING_PAREN = re.compile(r"^(.+?)\s*\([^()]*\)\s*$")
NESTED_LOCAL_PRIVATE = re.compile(r"^(.+?)\s*\(\d{4}\s+No\s+\d+\s*\([PL]\)\)\s*$")
MACRON_MAP = str.maketrans("āēīōūĀĒĪŌŪ", "aeiouAEIOU")
HAS_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
DUP_YEAR_RE = re.compile(r"Act\s+(\d{4})\s+Amendment\s+Act\s+\1\b")


def normalize(name):
    if not name:
        return name
    name = name.strip()
    if name.endswith("."):
        name = name[:-1].strip()
    name = name.replace("’", "'").replace("‘", "'")
    while True:
        m = NESTED_LOCAL_PRIVATE.match(name)
        if m:
            name = m.group(1).strip()
            continue
        m = CITE_PATTERN.match(name)
        if m:
            name = m.group(1).strip()
            continue
        m2 = GENERIC_TRAILING_PAREN.match(name)
        if m2:
            name = m2.group(1).strip()
            continue
        break
    name = name.translate(MACRON_MAP)
    name = re.sub(r"\s+", " ", name).strip()
    return name


with open(SG1_PATH, encoding="utf-8") as f:
    sg1 = json.load(f)
with open(SG2_PATH, encoding="utf-8") as f:
    sg2 = json.load(f)
with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)
with open(SG4_PATH, encoding="utf-8") as f:
    sg4 = json.load(f)
with open(CANDIDATES_PATH, encoding="utf-8") as f:
    candidates = json.load(f)

known_names_norm = {normalize(SEED)}
for entries in (sg1, sg2, sg3, sg4):
    for e in entries:
        known_names_norm.add(normalize(e["act"]))

print(f"Total SG5 candidates: {len(candidates)}\n")

print("=" * 70)
print("CHECK 1: candidates with no 4-digit year anywhere (likely heading/")
print("phrase artifacts, not real Act names)")
print("=" * 70)
no_year = [c for c in candidates if not HAS_YEAR_RE.search(c["act"])]
no_year.sort(key=lambda c: -c["combined_score"])
print(f"Found {len(no_year)}")
for c in no_year:
    print(f"  score {c['combined_score']:>4}  {c['act']!r}")

print()
print("=" * 70)
print("CHECK 2: nested-parenthesis Local/Private Act citations")
print("=" * 70)
nested = [c for c in candidates if NESTED_LOCAL_PRIVATE.match(c["act"].strip())]
print(f"Found {len(nested)}")
for c in nested:
    loose = normalize(c["act"])
    already_known = loose in known_names_norm
    flag = "  <-- ALREADY KNOWN, false 'new' candidate" if already_known else ""
    print(f"  score {c['combined_score']:>4}  {c['act']!r}")
    print(f"      -> normalizes to {loose!r}{flag}")

print()
print("=" * 70)
print("CHECK 3: possible extraction-duplication artifacts (same year twice)")
print("=" * 70)
dup_year = [c for c in candidates if DUP_YEAR_RE.search(c["act"])]
print(f"Found {len(dup_year)}")
for c in dup_year:
    print(f"  score {c['combined_score']:>4}  {c['act']!r}")