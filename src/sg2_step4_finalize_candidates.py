"""
Applies the three exclusion categories confirmed from
sg2_step3_investigate_candidates.py to the raw SG2 amendment-based
candidate pool (data/processed/sg2_amendment_candidates.json):

  1. Self-referential candidates (268 flagged) -- a source Act's own
     amendment-series variant (e.g. "Education Amendment Act 1990" relative
     to "Education Act 1989"), not a genuine cross-Act relationship.
  2. Omnibus "Taxation (Annual Rates for ..., ...) Act" series (11 Acts,
     combined score 7,496) -- artefact of Income Tax Act 2007 / Tax
     Administration Act 1994 being generic hub Acts. Excluded on the same
     "avoid hub dominance" rationale Ardekani et al. (2026) give for
     depth-limited layered expansion, and consistent with SG1's precedent
     of removing bulk/mechanical sweeps rather than genuine thematic links.
  3. Confirmed bulk single-event Acts reappearing from SG1 (Secondary
     Legislation Act 2021, Public Service Act 2020) -- same two Acts
     excluded at SG1, for the same reason.

Outputs the cleaned, ranked candidate list and prints the score
distribution so an SG2 threshold can be chosen on evidence, the same way
SG1's >=6 was chosen rather than assumed.
"""
import json
import re
from pathlib import Path
from collections import Counter

CANDIDATES_PATH = Path("data/processed/sg2_amendment_candidates.json")
SG1_PATH = Path("data/processed/sg1_final_list.json")
OUTPUT_PATH = Path("data/processed/sg2_cleaned_candidates.json")

with open(CANDIDATES_PATH) as f:
    candidates = json.load(f)

with open(SG1_PATH) as f:
    sg1_acts = json.load(f)

SEED = "Education and Training Act 2020"

# ---- 1. self-referential heuristic (same logic as step 3) ----
STOPWORDS = {"amendment", "act", "no", "of", "the", "and"}
YEAR_RE = re.compile(r"\b(18|19|20)\d{2}\b")
PAREN_RE = re.compile(r"\([^)]*\)")

def base_words(name):
    name = PAREN_RE.sub("", name)
    name = YEAR_RE.sub("", name)
    words = {w.lower() for w in re.findall(r"[A-Za-z']+", name)}
    return words - STOPWORDS

def is_self_referential(candidate_name, source_names):
    cand_words = base_words(candidate_name)
    if not cand_words:
        return False
    for src in source_names:
        src_words = base_words(src)
        if not src_words:
            continue
        if cand_words <= src_words or src_words <= cand_words:
            return True
    return False

# ---- 2. omnibus Taxation Acts ----
OMNIBUS_PATTERN = re.compile(r"^Taxation \(Annual Rates for", re.IGNORECASE)

# ---- 3. confirmed bulk single-event Acts (SG1 precedent) ----
BULK_EVENT_ACTS = {
    "Secondary Legislation Act 2021",
    "Public Service Act 2020",
    "Employment Relations (Pay Deductions) Act 2025",
}

kept, excluded = [], []
exclusion_reasons = Counter()

for c in candidates:
    name = c.get("act") or c.get("candidate") or c.get("name")
    sources = c.get("linked_from", [])
    reasons = []

    if name == SEED:
        reasons.append("seed")
    if OMNIBUS_PATTERN.match(name or ""):
        reasons.append("omnibus_taxation")
    if name in BULK_EVENT_ACTS:
        reasons.append("bulk_event")
    if is_self_referential(name, sources):
        reasons.append("self_referential")

    if reasons:
        c["exclusion_reasons"] = reasons
        excluded.append(c)
        for r in reasons:
            exclusion_reasons[r] += 1
    else:
        kept.append(c)

kept.sort(key=lambda c: -c.get("combined_score", 0))

print(f"Raw candidate pool:      {len(candidates)}")
print(f"Excluded (total):        {len(excluded)}")
for reason, n in exclusion_reasons.most_common():
    print(f"  - {reason}: {n}")
print(f"Cleaned SG2 candidates:  {len(kept)}")
print()

print("Score distribution of cleaned candidates:")
for threshold in [30, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1]:
    n = sum(1 for c in kept if c.get("combined_score", 0) >= threshold)
    print(f"  score >= {threshold:>3}: {n:>4} Acts")

print()
print("Top 40 cleaned candidates:")
for c in kept[:40]:
    name = c.get("act") or c.get("candidate") or c.get("name")
    print(f"  {name}  (score {c.get('combined_score')}, {len(c.get('linked_from', []))} links)")

with open(OUTPUT_PATH, "w") as f:
    json.dump(kept, f, indent=2)
print(f"\nSaved cleaned candidates -> {OUTPUT_PATH}")