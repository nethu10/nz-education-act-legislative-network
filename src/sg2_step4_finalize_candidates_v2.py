"""
sg2_step4_finalize_candidates.py (v2)

v1 -> v2 fixes, based on the v1 output:
  1. OMNIBUS_PATTERN was too narrow (only "Taxation (Annual Rates for...").
     The v1 "cleaned" top-40 was still dominated by 20+ other
     "Taxation (..., and Remedial Matters/Miscellaneous Provisions) Act"
     titles -- same genre of NZ periodic omnibus tax-law vehicle, just
     different subject words in the parenthetical subtitle. Broadened to
     match any Act titled "Taxation (...)" -- this does NOT catch
     "Income Tax Act", "Tax Administration Act" (the two underlying hub
     Acts) or "Taxation Review Authorities Act" (a real institutional Act),
     since none of those have "Taxation (" as a prefix.
  2. Added a name-sanity filter: a candidate with no 4-digit year AND no
     legislative-type keyword (Act/Rules/Regulations/Order/Notice/Bylaw/
     Bill) is a parsing artifact, not a real Act (e.g. "Section 3"), and
     is now excluded and reported instead of silently ranking.

Applies, in order: seed / invalid name / omnibus taxation / bulk single-
event Acts / self-referential. Prints counts per category plus the score
distribution, and separately saves the self-referential list for a spot-
check against step 3's original 268 (this pass found 326 -- worth
reconciling before relying on it further).
"""
import json
import re
from pathlib import Path
from collections import Counter

CANDIDATES_PATH = Path("data/processed/sg2_amendment_candidates.json")
OUTPUT_PATH = Path("data/processed/sg2_cleaned_candidates.json")
SELF_REF_REVIEW_PATH = Path("data/processed/sg2_self_referential_flagged.json")

with open(CANDIDATES_PATH) as f:
    candidates = json.load(f)

SEED = "Education and Training Act 2020"

# ---- self-referential heuristic (unchanged from v1) ----
STOPWORDS = {"amendment", "act", "no", "of", "the", "and"}
YEAR_RE = re.compile(r"\b(18|19|20)\d{2}\b")
PAREN_RE = re.compile(r"\([^)]*\)")

def base_words(name):
    name = PAREN_RE.sub("", name or "")
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

# ---- omnibus Taxation Acts -- broadened ----
OMNIBUS_TAX_PATTERN = re.compile(r"^Taxation\s*\(", re.IGNORECASE)

# ---- confirmed bulk single-event Acts (SG1 precedent) ----
BULK_EVENT_ACTS = {
    "Secondary Legislation Act 2021",
    "Public Service Act 2020",
    "Employment Relations (Pay Deductions) Act 2025",
}

# ---- name-sanity filter ----
YEAR_ANYWHERE_RE = re.compile(r"(18|19|20)\d{2}")
LEGIS_KEYWORD_RE = re.compile(r"\b(Act|Rules?|Regulations?|Order|Notice|Bylaw|Bill)\b", re.IGNORECASE)

def looks_like_real_title(name):
    if not name:
        return False
    if not YEAR_ANYWHERE_RE.search(name):
        return False
    if not LEGIS_KEYWORD_RE.search(name):
        return False
    return True

kept, excluded, self_ref_flagged = [], [], []
exclusion_reasons = Counter()

for c in candidates:
    name = c.get("act") or c.get("candidate") or c.get("name")
    sources = c.get("linked_from", [])
    reasons = []

    if name == SEED:
        reasons.append("seed")
    if not looks_like_real_title(name):
        reasons.append("invalid_name")
    if OMNIBUS_TAX_PATTERN.match(name or ""):
        reasons.append("omnibus_taxation")
    if name in BULK_EVENT_ACTS:
        reasons.append("bulk_event")
    if is_self_referential(name, sources):
        reasons.append("self_referential")
        self_ref_flagged.append({"act": name, "combined_score": c.get("combined_score"), "linked_from": sources})

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
with open(SELF_REF_REVIEW_PATH, "w") as f:
    json.dump(self_ref_flagged, f, indent=2)

print(f"\nSaved cleaned candidates -> {OUTPUT_PATH}")
print(f"Saved self-referential flags (for spot-check) -> {SELF_REF_REVIEW_PATH}")