"""
sg2_step4_finalize_candidates_v3.py

v2 -> v3 fix: about half the candidate names carry a bare "(YYYY No N)"
citation suffix and half don't (extraction-path inconsistency), meaning
the same real Act could be split across two rows under two name strings,
understating its true combined score. Added a normalize+merge pass that
strips the trailing citation and sums scores/linked_from for any names
that collapse together, run BEFORE the exclusion filters so those filters
see true totals.

Everything else (self-referential / omnibus taxation / bulk single-event
Acts / invalid-name) is unchanged from v2.
"""
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

CANDIDATES_PATH = Path("data/processed/sg2_amendment_candidates.json")
OUTPUT_PATH = Path("data/processed/sg2_cleaned_candidates.json")
SELF_REF_REVIEW_PATH = Path("data/processed/sg2_self_referential_flagged.json")

with open(CANDIDATES_PATH) as f:
    candidates = json.load(f)

SEED = "Education and Training Act 2020"

# ---- 0. normalize + merge citation-suffix duplicates ----
CITE_SUFFIX_RE = re.compile(r"\s*\((?:\d{4}\s+No\s+\d+|(?:SR|LI)\s+\d{4}/\d+)\)\s*$")

def normalize_name(name):
    if not name:
        return name
    return CITE_SUFFIX_RE.sub("", name).strip()

merged = {}
for c in candidates:
    raw_name = c.get("act") or c.get("candidate") or c.get("name")
    norm_name = normalize_name(raw_name)
    if norm_name not in merged:
        merged[norm_name] = {"act": norm_name, "combined_score": 0, "linked_from": []}
    merged[norm_name]["combined_score"] += c.get("combined_score", 0)
    merged[norm_name]["linked_from"].extend(c.get("linked_from", []))

candidates = list(merged.values())
print(f"Raw records: merged into {len(candidates)} distinct Acts "
      f"(citation-suffix duplicates collapsed)")
print()

# ---- self-referential heuristic (unchanged) ----
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

# ---- omnibus Taxation Acts ----
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
    name = c["act"]
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

print(f"Merged candidate pool:   {len(candidates)}")
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
    print(f"  {c['act']}  (score {c.get('combined_score')}, {len(c.get('linked_from', []))} links)")

with open(OUTPUT_PATH, "w") as f:
    json.dump(kept, f, indent=2)
with open(SELF_REF_REVIEW_PATH, "w") as f:
    json.dump(self_ref_flagged, f, indent=2)

print(f"\nSaved cleaned candidates -> {OUTPUT_PATH}")
print(f"Saved self-referential flags (for spot-check) -> {SELF_REF_REVIEW_PATH}")