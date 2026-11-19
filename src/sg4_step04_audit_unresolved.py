"""
sg4_step04_audit_unresolved.py

Diagnostic only -- writes nothing. Two checks against the FULL
sg4_act_identifiers.json (not just the 57 unresolved):

1. Flags every candidate whose name looks like a stray section/clause
   cross-reference ("Section 264", "Clause 42", ...) rather than an
   Act/Regulation title -- and reports whether any of these actually
   resolved (a much worse bug than failing to resolve, since it would
   mean a bogus node is sitting in the SG4 network right now).

2. For unresolved candidates, applies a looser iterative normalize()
   that peels off trailing parenthetical annotations one at a time
   (generic first, e.g. "(RS Vol 1, p 635)", then the strict citation-
   code pattern), so double-suffixed names like
   "Crimes Act 1961 (1961 No 43) (RS Vol 1, p 635)" reduce to
   "Crimes Act 1961" -- then checks that reduced form against every
   name already in Seed/SG1/SG2/SG3, to catch any other already-known
   Acts hiding behind a messy citation suffix.
"""
import json
import re
from pathlib import Path

SEED = "Education and Training Act 2020"
SG1_PATH = Path("data/processed/sg1_final_list.json")
SG2_PATH = Path("data/processed/sg2_final_list.json")
SG3_PATH = Path("data/processed/sg3_final_list.json")
SG4_IDENTIFIERS = Path("data/processed/sg4_act_identifiers.json")

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
GENERIC_TRAILING_PAREN = re.compile(r"^(.+?)\s*\([^()]*\)\s*$")
MACRON_MAP = str.maketrans("āēīōūĀĒĪŌŪ", "aeiouAEIOU")
SECTION_CLAUSE_RE = re.compile(r"^(section|clause)\s+\d+[a-z]*$", re.IGNORECASE)


def normalize(name):
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    name = m.group(1).strip() if m else name.strip()
    name = name.translate(MACRON_MAP)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_loose(name):
    """Peels off trailing parenthetical annotations one at a time --
    generic first (handles non-standard suffixes like RS-volume
    references), then the strict citation-code pattern -- until
    nothing more comes off. Also strips a trailing period first."""
    if not name:
        return name
    name = name.strip()
    if name.endswith("."):
        name = name[:-1].strip()
    name = name.replace("’", "'").replace("‘", "'")
    while True:
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
with open(SG4_IDENTIFIERS, encoding="utf-8") as f:
    sg4_ids = json.load(f)

known_names_norm = {normalize(SEED)}
for layer_name, entries in [("SG1", sg1), ("SG2", sg2), ("SG3", sg3)]:
    for e in entries:
        known_names_norm.add(normalize(e["act"]))

print(f"Total SG4 candidates checked: {len(sg4_ids)}")
if sg4_ids:
    print(f"Example record keys: {sorted(sg4_ids[0].keys())}\n")

# ---- Check 1: Section/Clause pseudo-candidates, across ALL entries ----
print("=" * 70)
print("CHECK 1: stray section/clause pseudo-candidates (any resolved status)")
print("=" * 70)
pseudo = [e for e in sg4_ids if SECTION_CLAUSE_RE.match(e.get("act", "").strip())]
print(f"Found {len(pseudo)} candidates matching 'Section N' / 'Clause N'")
for e in pseudo:
    resolved = e.get("resolved")
    if resolved:
        print(f"  [RESOLVED -- CHECK THIS] {e.get('act')!r} -> "
              f"{e.get('url') or e.get('xml_url') or '(no url field found)'}")
    else:
        print(f"  [unresolved, as expected] {e.get('act')!r}")

# ---- Check 2: unresolved candidates that are actually already-known
# Acts hiding behind a messy/double citation suffix ----
print()
print("=" * 70)
print("CHECK 2: unresolved candidates that loosely match a known Act")
print("=" * 70)
hits = []
for e in sg4_ids:
    if e.get("resolved"):
        continue
    loose = normalize_loose(e.get("act", ""))
    if loose in known_names_norm:
        hits.append((e.get("act"), loose))
print(f"Found {len(hits)} unresolved candidates that loosely match an "
      f"already-known Seed/SG1/SG2/SG3 Act")
for raw, loose in hits:
    print(f"  {raw!r}")
    print(f"    -> loosely normalizes to: {loose!r} (already known)")