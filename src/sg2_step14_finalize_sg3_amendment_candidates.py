"""
sg2_step14_finalize_sg3_amendment_candidates.py

The SG3 sequel to sg2_step4_finalize_candidates_v5.py: applies the same
four evidence-based exclusion categories to the amendment-side SG3 raw
pool (data/processed/sg2_new_candidates_seen.json, the "outside
seed/SG1/SG2" byproduct of sg2_step11_find_internal_links.py).

Unlike sg2_amendment_candidates.json at the SG2 stage, this pool was
already built with rename-aware resolve_canonical() (normalize() +
RENAME_MAP from sg2_step13), so no separate citation-suffix-duplicate
merge step is needed here -- step11 already merged those before writing
this file.

Categories applied (identical definitions to step4):
  1. Self-referential -- a source Act's own amendment-series variant.
  2. Omnibus "Taxation (...)" Acts.
  3. Confirmed bulk single-event Acts (same list as SG1/SG2: Secondary
     Legislation Act 2021, Public Service Act 2020, Employment Relations
     (Pay Deductions) Act 2025). Both of the first two are NOT SG1 or SG2
     Acts (they were excluded at those stages too), so they resurface
     here and need excluding again on the same evidence.
  4. Invalid/parsing-artifact names (year-anywhere check only, per v5's
     fix for te-reo-titled Acts like Te Ture mo te Hararei Tumatanui o te
     Kahui o Matariki 2022).

Outputs the cleaned, ranked list plus the self-referential and excluded
lists (for spot-checking), same shape as step4's outputs.
"""
import json
import re
from pathlib import Path
from collections import Counter

CANDIDATES_PATH = Path("data/processed/sg2_new_candidates_seen.json")
OUTPUT_PATH = Path("data/processed/sg3_cleaned_amendment_candidates.json")
SELF_REF_REVIEW_PATH = Path("data/processed/sg3_self_referential_flagged.json")
EXCLUDED_PATH = Path("data/processed/sg3_excluded_amendment_candidates.json")

with open(CANDIDATES_PATH) as f:
    candidates = json.load(f)

SEED = "Education and Training Act 2020"

# ---- self-referential heuristic (identical to step4) ----
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

# ---- omnibus Taxation Acts (identical to step4) ----
OMNIBUS_TAX_PATTERN = re.compile(r"^Taxation\s*\(", re.IGNORECASE)

# ---- confirmed bulk single-event Acts (same list as SG1/SG2) ----
BULK_EVENT_ACTS = {
    "Secondary Legislation Act 2021",
    "Public Service Act 2020",
    "Employment Relations (Pay Deductions) Act 2025",
}

# ---- name-sanity filter -- year only (identical to step4 v5) ----
YEAR_ANYWHERE_RE = re.compile(r"(18|19|20)\d{2}")

def looks_like_real_title(name):
    if not name:
        return False
    return bool(YEAR_ANYWHERE_RE.search(name))

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
        c = dict(c)
        c["exclusion_reasons"] = reasons
        excluded.append(c)
        for r in reasons:
            exclusion_reasons[r] += 1
    else:
        kept.append(c)

kept.sort(key=lambda c: -c.get("combined_score", 0))

print(f"Raw amendment-side SG3 pool: {len(candidates)}")
print(f"Excluded (total):           {len(excluded)}")
for reason, n in exclusion_reasons.most_common():
    print(f"  - {reason}: {n}")
print(f"Cleaned SG3 amendment-side candidates: {len(kept)}")
print()

print("Sample of invalid_name exclusions (sanity check -- should all look like junk, not real Acts):")
invalid_examples = [c for c in excluded if "invalid_name" in c["exclusion_reasons"]][:20]
for c in invalid_examples:
    print(f"  {c['act']!r}  (score {c.get('combined_score')})")
print()

print("Top 20 cleaned amendment-side SG3 candidates:")
for c in kept[:20]:
    print(f"  {c['act']}  (score {c.get('combined_score')}, {len(c.get('linked_from', []))} links)")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(kept, f, indent=2, ensure_ascii=False)
with open(SELF_REF_REVIEW_PATH, "w", encoding="utf-8") as f:
    json.dump(self_ref_flagged, f, indent=2, ensure_ascii=False)
with open(EXCLUDED_PATH, "w", encoding="utf-8") as f:
    json.dump(excluded, f, indent=2, ensure_ascii=False)

print(f"\nSaved cleaned candidates -> {OUTPUT_PATH}")
print(f"Saved self-referential flags -> {SELF_REF_REVIEW_PATH}")
print(f"Saved full excluded list -> {EXCLUDED_PATH}")