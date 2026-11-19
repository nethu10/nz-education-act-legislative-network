"""
sg4_step09_clean_sg5_candidates.py

Cleans sg4_new_candidates_seen.json based on sg4_step08's audit,
correcting one bug in that audit's own year-detection regex along the
way (it only matched 19xx/20xx, missing 19th-century NZ legislation --
e.g. "Wanganui Harbour and River Conservators Board Act 1876" was
wrongly flagged as having no year).

Removes:
1. Structural pseudo-candidates with no plausible NZ-legislation year
   anywhere (1800-2099) -- section/clause/regulation/schedule/rule/
   form/policy/chapter/part numbered cross-references and stray
   heading phrases, not real Act names.
2. Nested-parenthesis Local/Private Act citations ("Name YYYY (YYYY No
   N (P/L))") that normalize to an Act already in Seed/SG1/SG2/SG3/SG4
   -- false "new" candidates, same bug family as the Crimes Act
   cross-layer duplicate.
3. The 2 duplicated-year artifacts ("Act YYYY Amendment Act YYYY"),
   collapsed to single-year form and checked the same way.

Everything KEPT that had a nested-parenthesis Local/Private suffix has
that suffix stripped from its stored "act" name, so identifier
resolution and SG5-internal-link-finding don't have to solve this a
second time.
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
NESTED_LOCAL_PRIVATE = re.compile(r"^(.+?)\s*\((\d{4}\s+No\s+\d+)\s*\([PL]\)\)\s*$")
MACRON_MAP = str.maketrans("āēīōūĀĒĪŌŪ", "aeiouAEIOU")
HAS_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")  # 1800-2099, corrected range
DUP_YEAR_RE = re.compile(r"^(.*\bAct\s+(\d{4}))\s+Amendment\s+Act\s+\2\s*$")


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

kept = []
removed_no_year = []
removed_already_known = []
fixed_duplicated_year = []
suffix_stripped = 0

for c in candidates:
    raw = c["act"]

    m = DUP_YEAR_RE.match(raw)
    if m:
        collapsed = m.group(1).strip()
        loose = normalize(collapsed)
        if loose in known_names_norm:
            removed_already_known.append((raw, loose))
            continue
        fixed_duplicated_year.append((raw, collapsed))
        c["act"] = collapsed
        raw = collapsed

    if not HAS_YEAR_RE.search(raw):
        removed_no_year.append(raw)
        continue

    nm = NESTED_LOCAL_PRIVATE.match(raw.strip())
    if nm:
        loose = normalize(raw)
        if loose in known_names_norm:
            removed_already_known.append((raw, loose))
            continue
        c["act"] = nm.group(1).strip()
        suffix_stripped += 1

    kept.append(c)

kept.sort(key=lambda c: -c["combined_score"])
with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
    json.dump(kept, f, indent=2, ensure_ascii=False)

print(f"Before: {len(candidates)}")
print(f"Removed -- no plausible year (structural pseudo-candidate): {len(removed_no_year)}")
print(f"Removed -- already known (duplicate): {len(removed_already_known)}")
for raw, loose in removed_already_known:
    print(f"    {raw!r} -> {loose!r}")
print(f"Fixed -- duplicated-year artifact collapsed: {len(fixed_duplicated_year)}")
for raw, collapsed in fixed_duplicated_year:
    print(f"    {raw!r} -> {collapsed!r}")
print(f"Nested-parenthesis suffix stripped (kept as new candidates): {suffix_stripped}")
print(f"\nAfter: {len(kept)}")
print(f"Saved -> {CANDIDATES_PATH}")