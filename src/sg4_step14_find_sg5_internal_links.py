"""
sg4_step14_find_sg5_internal_links.py

Finds SG5-internal links: scans the 47 finalized SG5 Acts' own XML for
citations, bucketing each one found into either "already in the
network" (seed/SG1/SG2/SG3/SG4/SG5 -- SG5-internal if the target is
itself an SG5 Act) or "new" (would be an SG6 candidate). This is the
one scan nobody has run yet -- every earlier layer's internal links
came for free as a byproduct of building the NEXT layer's candidate
pool (SG3-internal came from the script that built SG4's pool; SG4-
internal came from the script that built SG5's pool). Since the
network stops at SG5, nothing has ever scanned SG5's own Acts until
now -- this script is that scan, one layer up from
sg4_step06_find_sg4_internal_links.py, same structure throughout.

The "new_candidates_seen" output is what would seed an SG6 -- since
the network is stopping at SG5, that file is written for completeness
(and as a record of what's being deliberately left out) but is not
meant to be used further. It has NOT been cleaned of the pseudo-
candidate patterns found auditing SG5's own pool (schedule-heading
phrases, duplicated-year artifacts) -- there's no reason to spend that
effort on a file that will be set aside.

Fixes baked in from the start (learned across SG3-SG5's construction,
applied proactively here rather than found via another audit pass):
  - SECTION_CLAUSE_RE: excludes bare "Section N" / "Clause N"
    cross-references at extraction time (sg4_step06's fix).
  - GENERIC_TRAILING_PAREN: iterative trailing-parenthetical
    stripping, for citations with more than one stacked suffix
    (sg4_step06's fix, for cases like the Crimes Act's double suffix).
  - NESTED_LOCAL_PRIVATE: strips the "(YYYY No N (P))" / "(L)"
    nested-parenthesis Local/Private Act suffix (found auditing SG5's
    raw pool in sg4_step08/09).
  - Alt-name-before-slash fallback: if a candidate doesn't match any
    known Act directly, also tries the text before a "/" (NZ's
    bilingual dual-name format, e.g. "Te Ture Whenua Maori/Maori Land
    Act 1993") before concluding it's genuinely unknown. This existed
    in identifier-resolution's cascade already but was missing from
    pool-building's own matching -- found via the Te Ture Whenua Maori
    duplicate that slipped through pool-building in SG5 and only
    surfaced later in an identifier-based duplicate audit.

Inputs:
  data/processed/sg1_final_list.json
  data/processed/sg2_final_list.json
  data/processed/sg3_final_list.json
  data/processed/sg4_final_list.json
  data/processed/sg5_final_list.json         -- 47 Acts
  data/processed/sg5_act_identifiers.json    -- 47 Acts, 47 resolved

Outputs:
  data/processed/sg5_internal_links.json
  data/processed/sg5_new_candidates_seen.json  -- would-be SG6 pool,
    set aside deliberately, not carried further
"""
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import requests
from lxml import etree

SG1_PATH = Path("data/processed/sg1_final_list.json")
SG2_PATH = Path("data/processed/sg2_final_list.json")
SG3_PATH = Path("data/processed/sg3_final_list.json")
SG4_PATH = Path("data/processed/sg4_final_list.json")
SG5_PATH = Path("data/processed/sg5_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg5_act_identifiers.json")
RAW_DIR = Path("data/raw/sg5_targets")
LINKS_OUT = Path("data/processed/sg5_internal_links.json")
NEW_CANDIDATES_OUT = Path("data/processed/sg5_new_candidates_seen.json")
RAW_DIR.mkdir(parents=True, exist_ok=True)

SEED_ACT_NAME = "Education and Training Act 2020"
DELAY_SECONDS = 1.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}

CITE_PATTERN = re.compile(
    r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$"
)
GENERIC_TRAILING_PAREN = re.compile(r"^(.+?)\s*\([^()]*\)\s*$")
NESTED_LOCAL_PRIVATE = re.compile(r"^(.+?)\s*\((\d{4}\s+No\s+\d+)\s*\([PL]\)\)\s*$")
SECTION_CLAUSE_RE = re.compile(r"^(section|clause)\s+\d+[a-z]*$", re.IGNORECASE)
MACRON_MAP = str.maketrans("āēīōūĀĒĪŌŪ", "aeiouAEIOU")


def normalize(name):
    """Citation-suffix strip (including the nested Local/Private form
    and the iterative generic-trailing-paren fallback) + apostrophe
    fix + macron-stripping + whitespace collapsing (folds NBSP into a
    normal space)."""
    if not name:
        return name
    name = name.strip()
    if name.endswith("."):
        name = name[:-1].strip()
    name = name.replace("\u2019", "'").replace("\u2018", "'")
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


def before_slash(name):
    """NZ's bilingual dual-name format ('X/Y'): try the text before the
    slash as a fallback match. Only meaningful when a '/' is actually
    present and isn't just part of a citation code."""
    if "/" not in name:
        return None
    before, _, _ = name.partition("/")
    before = before.strip()
    return before if before else None


# ---- rename-aware resolution (unchanged from sg2_step26_v2 / sg4_step06) ----
RENAME_MAP = {
    "Schedule 32 of the Social Security Act 1964": "Social Security Act 1964",
    "Schedule 1 of the New Zealand Superannuation and Retirement Income Act 2001":
        "New Zealand Superannuation and Retirement Income Act 2001",
    "Schedule 1AA of the New Zealand Superannuation and Retirement Income Act 2001":
        "New Zealand Superannuation and Retirement Income Act 2001",
    "Injury Prevention, Rehabilitation, and Compensation Act 2001": "Accident Compensation Act 2001",
    "Healthy Futures (Pae Ora) Act 2022": "Pae Ora (Healthy Futures) Act 2022",
    "Housing Restructuring and Tenancy Matters Act 1992": "Public and Community Housing Management Act 1992",
    "State Sector Act 1988 (RS Vol 33, p 715)": "State Sector Act 1988",
    "New Zealand Act 2021": "Reserve Bank of New Zealand Act 2021",
    "Schedule 1 of the Ombudsmen Act 1975": "Ombudsmen Act 1975",
    "Oranga Tamariki System Legislation Amendment Act 2025":
        "Oversight of Oranga Tamariki System Legislation Amendment Act 2025",
    "Waitangi Day and ANZAC Day) Amendment Act 2013":
        "Holidays (Full Recognition of Waitangi Day and ANZAC Day) Amendment Act 2013",
    "Support Workers (Pay Equity) Settlements Act 2017":
        "Care and Support Workers (Pay Equity) Settlement Act 2017",
    "Schedule 2 of the Public Service Act 2020": None,
    "Schedule 6 of the Public Service Act 2020": None,
    "Schedule 1 of the Privacy Act 2020": None,
    "Family Courts Act 1980": "Family Court Act 1980",
    "District Courts Rules 2014": "District Court Rules 2014",
    "Family Courts Rules 2002": "Family Court Rules 2002",
    "Sexual Violence (Strengthening Legal Protections) Legislation Act 2025":
        "Victims of Sexual Violence (Strengthening Legal Protections) Legislation Act 2025",
    "Family Violence (Strengthening Legal Protections) Legislation Act 2025":
        "Victims of Family Violence (Strengthening Legal Protections) Legislation Act 2025",
}

def resolve_canonical(name):
    n = normalize(name)
    if n in RENAME_MAP:
        return RENAME_MAP[n]
    return n


# ---- reused verbatim from sg2_step26_v2 / sg4_step06 ----
def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def element_text(el):
    if el is None:
        return ""
    raw = " ".join(el.itertext())
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"\s+([,.:;)])", r"\1", cleaned)
    return cleaned

def extract_amendment_records(root):
    records = []
    for note in root.iter():
        if local_name(note.tag) != "history-note":
            continue
        def first_text(tag_name):
            el = note.find(tag_name)
            return el.text if el is not None else None
        records.append({
            "operation": first_text("amending-operation"),
            "amending_act": first_text("amending-leg"),
        })
    return records

def extract_outgoing_amendments(root):
    records = []
    for group2 in root.iter():
        if local_name(group2.tag) != "schedule.amendments.group2":
            continue
        heading_el = group2.find("heading")
        target_act = element_text(heading_el) if heading_el is not None else None
        for para in group2.findall("para"):
            records.append({"target_act": target_act, "text": element_text(para)})
    return records
# ---- end reused block ----


with open(SG1_PATH, encoding="utf-8") as f:
    sg1 = json.load(f)
with open(SG2_PATH, encoding="utf-8") as f:
    sg2 = json.load(f)
with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)
with open(SG4_PATH, encoding="utf-8") as f:
    sg4 = json.load(f)
with open(SG5_PATH, encoding="utf-8") as f:
    sg5 = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

sg1_names_norm = {normalize(a["act"]) for a in sg1}
seed_norm = normalize(SEED_ACT_NAME)
sg2_names_norm = {normalize(c["act"]) for c in sg2}
sg3_names_norm = {normalize(c["act"]) for c in sg3}
sg4_names_norm = {normalize(c["act"]) for c in sg4}
sg5_names_norm = {normalize(c["act"]) for c in sg5}

known_elsewhere = sg1_names_norm | sg2_names_norm | sg3_names_norm | sg4_names_norm
all_known = known_elsewhere | sg5_names_norm | {seed_norm}

fetchable = [d for d in identifiers if d.get("resolved") and d.get("xml_url")]
print(f"{len(fetchable)} SG5 Acts have a fetchable XML URL "
      f"({len(identifiers) - len(fetchable)} skipped: unresolved or no XML available)\n")

internal_pool = defaultdict(lambda: {"combined_score": 0, "linked_from": []})
new_candidates_seen = defaultdict(lambda: {"combined_score": 0, "linked_from": []})

n_fetched = 0
n_cached = 0
n_failed = 0
n_pseudo_excluded = 0

for i, entry in enumerate(fetchable, 1):
    source_name = entry["act"]
    source_norm = normalize(source_name)
    year, number = entry["year"], entry["number"]
    cache_path = RAW_DIR / f"{year}_{number}.xml"

    if cache_path.exists():
        xml_bytes = cache_path.read_bytes()
        n_cached += 1
    else:
        try:
            r = requests.get(entry["xml_url"], headers=HEADERS, timeout=60)
            if r.status_code != 200:
                print(f"  [{i}/{len(fetchable)}] FAILED {source_name!r}: status {r.status_code}")
                n_failed += 1
                time.sleep(DELAY_SECONDS)
                continue
            xml_bytes = r.content
            cache_path.write_bytes(xml_bytes)
            n_fetched += 1
            time.sleep(DELAY_SECONDS)
        except Exception as e:
            print(f"  [{i}/{len(fetchable)}] FAILED {source_name!r}: {type(e).__name__}: {e}")
            n_failed += 1
            time.sleep(DELAY_SECONDS)
            continue

    try:
        root = etree.fromstring(xml_bytes)
    except Exception as e:
        print(f"  [{i}/{len(fetchable)}] PARSE FAILED {source_name!r}: {type(e).__name__}: {e}")
        n_failed += 1
        continue

    incoming = extract_amendment_records(root)
    outgoing = extract_outgoing_amendments(root)

    per_candidate_counts = defaultdict(int)
    for r in incoming:
        if r["amending_act"]:
            per_candidate_counts[r["amending_act"]] += 1
    for r in outgoing:
        if r["target_act"]:
            per_candidate_counts[r["target_act"]] += 1

    for candidate, count in per_candidate_counts.items():
        cand_norm = resolve_canonical(candidate)
        if cand_norm is None:
            continue
        if SECTION_CLAUSE_RE.match(cand_norm):
            n_pseudo_excluded += 1
            continue

        # direct match, then the before-slash fallback if no direct match
        match_norm = cand_norm
        if match_norm != source_norm and match_norm not in all_known:
            alt = before_slash(candidate)
            if alt:
                alt_norm = resolve_canonical(alt)
                if alt_norm and (alt_norm == source_norm or alt_norm in all_known):
                    match_norm = alt_norm

        if match_norm == source_norm or match_norm == seed_norm or match_norm in known_elsewhere:
            continue
        if match_norm in sg5_names_norm:
            internal_pool[match_norm]["combined_score"] += count
            internal_pool[match_norm]["linked_from"].append(source_name)
            internal_pool[match_norm]["display_name"] = candidate
        else:
            new_candidates_seen[match_norm]["combined_score"] += count
            new_candidates_seen[match_norm]["linked_from"].append(source_name)
            new_candidates_seen[match_norm]["display_name"] = candidate

    if i % 10 == 0 or i == len(fetchable):
        print(f"  [{i}/{len(fetchable)}] fetched={n_fetched} cached={n_cached} failed={n_failed} "
              f"| SG5-internal edges so far: {sum(len(v['linked_from']) for v in internal_pool.values())}")

print(f"\nDone fetching/parsing. fetched={n_fetched} cached={n_cached} failed={n_failed}")
print(f"Pseudo-candidates excluded at source (Section/Clause): {n_pseudo_excluded}")
print(f"Distinct SG5 Acts that are a target of at least one SG5-internal reference: {len(internal_pool)}")
print(f"Distinct NEW (outside the whole network) candidates seen -- would be SG6, "
      f"set aside deliberately, not carried further: {len(new_candidates_seen)}")

internal_out = [
    {"act": info["display_name"], "combined_score": info["combined_score"], "linked_from": info["linked_from"]}
    for info in internal_pool.values()
]
internal_out.sort(key=lambda c: -c["combined_score"])
with open(LINKS_OUT, "w", encoding="utf-8") as f:
    json.dump(internal_out, f, indent=2, ensure_ascii=False)

new_out = [
    {"act": info["display_name"], "combined_score": info["combined_score"], "linked_from": info["linked_from"]}
    for info in new_candidates_seen.values()
]
new_out.sort(key=lambda c: -c["combined_score"])
with open(NEW_CANDIDATES_OUT, "w", encoding="utf-8") as f:
    json.dump(new_out, f, indent=2, ensure_ascii=False)

print(f"\nSaved -> {LINKS_OUT}")
print(f"Saved -> {NEW_CANDIDATES_OUT}  (not carried further -- the network stops at SG5)")
print("\nSG5 Acts by number/strength of SG5-internal references pointing at them:")
for c in internal_out[:20]:
    print(f"  {c['act']}  (score {c['combined_score']}, from {len(c['linked_from'])} other SG5 Acts)")
if not internal_out:
    print("  (none -- the 47 SG5 Acts don't cite each other directly, only via SG1-SG4)")