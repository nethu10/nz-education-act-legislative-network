"""
sg2_step4_finalize_candidates_v5.py

Applies the exclusion categories confirmed through steps 1-3 to the raw
SG2 amendment-based candidate pool (data/processed/sg2_amendment_candidates.json):

  0. Normalize + merge citation-suffix duplicates (e.g. "District Court
     Act 2016" vs "District Court Act 2016 (2016 No 49)") before anything
     else runs, so no Act's true combined_score is ever split across two
     name variants. v3 confirmed there were no such duplicates in this
     dataset (1425 raw = 1425 merged), but this stays in as a standing
     safeguard.
  1. Self-referential candidates -- a source Act's own amendment-series
     variant (e.g. "Education Amendment Act 1990" relative to "Education
     Act 1989"), not a genuine cross-Act relationship.
  2. Omnibus "Taxation (...)" Acts -- NZ's periodic omnibus tax-law
     vehicles (any Act titled "Taxation (...)"), an artefact of Income Tax
     Act 2007 / Tax Administration Act 1994 being generic hub Acts. Does
     NOT catch "Income Tax Act", "Tax Administration Act", or "Taxation
     Review Authorities Act", since none of those have "Taxation (" as a
     prefix.
  3. Confirmed bulk single-event Acts reappearing from SG1 (Secondary
     Legislation Act 2021, Public Service Act 2020) -- same exclusion
     reason as at SG1.
  4. Invalid names -- parsing artifacts from the amendment-text extraction
     that aren't real Act names (e.g. "Section 3", "Section 120C"). v4's
     invalid_name filter required BOTH a year and an English legislative
     keyword (Act/Rules/Regulations/...); that wrongly caught "Te Ture mō
     te Hararei Tūmatanui o te Kāhui o Matariki 2022" (the Matariki Public
     Holiday Act -- a real, te reo Māori-titled Act with no English
     keyword). Every genuine "Section N" artifact has no year at all, so
     the year check alone does the real work -- the keyword check only
     added a failure mode for non-English-titled Acts. v5 drops the
     keyword requirement and checks for a year only.

Outputs the cleaned, ranked candidate list, the self-referential list (for
spot-checking), and the full excluded list (with per-Act reasons), plus a
score distribution with marginal counts to support picking an SG2
threshold on evidence, the same way SG1's >=6 was.
"""
import json
import re
from pathlib import Path
from collections import Counter

CANDIDATES_PATH = Path("data/processed/sg2_amendment_candidates.json")
OUTPUT_PATH = Path("data/processed/sg2_cleaned_candidates.json")
SELF_REF_REVIEW_PATH = Path("data/processed/sg2_self_referential_flagged.json")
EXCLUDED_PATH = Path("data/processed/sg2_excluded_candidates.json")

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
print(f"Raw records merged into {len(candidates)} distinct Acts")
print()

# ---- 1. self-referential heuristic ----
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

# ---- 2. omnibus Taxation Acts ----
OMNIBUS_TAX_PATTERN = re.compile(r"^Taxation\s*\(", re.IGNORECASE)

# ---- 3. confirmed bulk single-event Acts (SG1 precedent) ----
BULK_EVENT_ACTS = {
    "Secondary Legislation Act 2021",
    "Public Service Act 2020",
    "Employment Relations (Pay Deductions) Act 2025",
}

# ---- 4. name-sanity filter -- year only (v5: keyword requirement dropped) ----
YEAR_ANYWHERE_RE = re.compile(r"(18|19|20)\d{2}")

def looks_like_real_title(name):
    if not name:
        return False
    if not YEAR_ANYWHERE_RE.search(name):
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

print("Sample of invalid_name exclusions (sanity check -- should all look like junk, not real Acts):")
invalid_examples = [c for c in excluded if "invalid_name" in c["exclusion_reasons"]][:20]
for c in invalid_examples:
    print(f"  {c['act']!r}  (score {c.get('combined_score')})")
print()

print("Score distribution of cleaned candidates (with marginal counts):")
thresholds = [30, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1]
counts = [sum(1 for c in kept if c.get("combined_score", 0) >= t) for t in thresholds]
prev = 0
for t, n in zip(thresholds, counts):
    print(f"  score >= {t:>3}: {n:>4} Acts   (+{n - prev} vs next threshold up)")
    prev = n

print()
print("Top 40 cleaned candidates:")
for c in kept[:40]:
    print(f"  {c['act']}  (score {c.get('combined_score')}, {len(c.get('linked_from', []))} links)")

with open(OUTPUT_PATH, "w") as f:
    json.dump(kept, f, indent=2)
with open(SELF_REF_REVIEW_PATH, "w") as f:
    json.dump(self_ref_flagged, f, indent=2)
with open(EXCLUDED_PATH, "w") as f:
    json.dump(excluded, f, indent=2)

print(f"\nSaved cleaned candidates -> {OUTPUT_PATH}")
print(f"Saved self-referential flags -> {SELF_REF_REVIEW_PATH}")
print(f"Saved full excluded list -> {EXCLUDED_PATH}")