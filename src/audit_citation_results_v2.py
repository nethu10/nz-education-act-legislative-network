"""
Stricter validation pass: only counts an act_name as genuinely valid
if it matches the real pattern of a specific law name (contains a
year, or is a clearly identifiable named Act/Regulation) -- catching
generic placeholders and section-number mismatches the first, looser
filter missed. Also directly inspects the "exact name mentioned"
broken case to understand the prompt failure.
"""

import json
import re
from pathlib import Path

results = json.loads(Path("data/processed/citation_relationships_slm.json").read_text())

GENERIC_TERMS = {
    "an act", "another act", "any other act", "any other enactment", "other acts",
    "other legislation", "the act", "the amendment act", "the regulation",
    "the regulations", "regulations", "regulation", "rules", "this act",
    "this act or another enactment or rule of law", "another enactment, or rule of law",
    "the exact name mentioned", "the drs rules or resolutions",
}
SECTION_ONLY_PATTERN = re.compile(r"^(section|regulation)\s+\d+", re.IGNORECASE)
HAS_YEAR_OR_NAMED = re.compile(r"\b(19|20)\d{2}\b")  # a real Act/Regulation name usually carries a year

broken_prompt_echo = [r for r in results if r["act_name"].strip().lower() == "the exact name mentioned"]
generic = [r for r in results if r["act_name"].strip().lower() in GENERIC_TERMS and r not in broken_prompt_echo]
section_only = [r for r in results if SECTION_ONLY_PATTERN.match(r["act_name"].strip())]
self_matches = [r for r in results if "education and training act" in r["act_name"].lower()]

excluded_ids = {id(r) for r in broken_prompt_echo + generic + section_only + self_matches}
remaining = [r for r in results if id(r) not in excluded_ids]

no_year = [r for r in remaining if not HAS_YEAR_OR_NAMED.search(r["act_name"])]
genuinely_clean = [r for r in remaining if HAS_YEAR_OR_NAMED.search(r["act_name"])]

print(f"Total originally confirmed: {len(results)}")
print(f"Broken prompt-echo ('the exact name mentioned'): {len(broken_prompt_echo)}")
print(f"Generic placeholders: {len(generic)}")
print(f"Section numbers mistaken for Act names: {len(section_only)}")
print(f"Self-matches to the seed Act: {len(self_matches)}")
print(f"Remaining, no year/number at all (needs manual look): {len(no_year)}")
for r in no_year:
    print(f"    {r['provision_id']}: act_name={r['act_name']!r}")
print(f"\nGENUINELY VALID (has a year, real specific law): {len(genuinely_clean)}")

print("\n--- Direct look at the broken prompt-echo case(s) ---")
for r in broken_prompt_echo:
    print(f"  {r['provision_id']}: description=\"{r['description']}\"")

distinct = sorted(set(r["act_name"] for r in genuinely_clean))
print(f"\nDistinct genuinely valid external Acts/Regulations: {len(distinct)}")
for name in distinct:
    print(f"  {name}")

Path("data/processed/citation_relationships_validated.json").write_text(
    json.dumps(genuinely_clean, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved {len(genuinely_clean)} validated records to data/processed/citation_relationships_validated.json")