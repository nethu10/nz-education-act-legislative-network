"""
sg4_step06_find_sg4_internal_links.py

SG4-internal link finding, mirroring sg2_step26_find_sg3_internal_links_v2.py
one layer up: for each of the 1135 SG4 Acts, fetch its XML and find which
citations/amendments point at ANOTHER SG4 Act (-> sg4_internal_links.json,
feeds the SG4-internal diagram) versus something entirely new, outside
seed/SG1/SG2/SG3/SG4 (-> sg4_new_candidates_seen.json, the raw SG5
candidate pool).

Two fixes are baked in from the start this time, both prompted directly
by what sg4_step04_audit_unresolved.py found in the SG3->SG4 step:

1. normalize() already includes the macron/NBSP fix (no v1->v2 patch
   cycle needed here) -- macron-stripping + whitespace collapsing
   (Python's \\s matches NBSP U+00A0), applied after the citation-
   suffix/apostrophe handling.

2. normalize() now ALSO strips a trailing period and iteratively peels
   trailing parenthetical annotations -- generic fallback (any
   "(...)" immediately at the end) after the strict citation-code
   pattern fails to match. This handles double-stacked suffixes like
   "Crimes Act 1961 (1961 No 43) (RS Vol 1, p 635)", which previously
   slipped through as a false "new" candidate because CITE_PATTERN
   only strips ONE trailing group. Safe against the existing
   RENAME_MAP: the only key with a trailing parenthetical --
   "State Sector Act 1988 (RS Vol 33, p 715)" -- already maps to
   exactly what the generic strip produces on its own, so behaviour
   is unchanged there. The assumption this relies on (checked against
   every multi-parenthetical name seen so far this project): a
   *descriptive* qualifier is always embedded mid-title, before the
   year ("Pae Ora (Disestablishment ...) Amendment Act 2024"); a
   parenthetical sitting at the very end, after the year, is always a
   citation/volume annotation, never part of the real title. Worth
   revisiting if a genuine counterexample ever turns up.

3. Candidates matching "Section N" / "Clause N" (bare cross-references
   mis-captured as citation targets -- confirmed contaminating 287 of
   the previous layer's 4570 raw candidates) are now excluded at
   extraction time, before they can be bucketed as internal OR new --
   rather than caught after the fact the way SG4's were.

Inputs:
  data/processed/sg1_final_list.json
  data/processed/sg2_final_list.json
  data/processed/sg3_final_list.json
  data/processed/sg4_final_list.json           -- 1135 Acts (post sg4_step05)
  data/processed/sg4_act_identifiers.json      -- 1135 Acts, 1095 resolved

Outputs:
  data/processed/sg4_internal_links.json
  data/processed/sg4_new_candidates_seen.json
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
IDENTIFIERS_PATH = Path("data/processed/sg4_act_identifiers.json")
RAW_DIR = Path("data/raw/sg4_targets")
LINKS_OUT = Path("data/processed/sg4_internal_links.json")
NEW_CANDIDATES_OUT = Path("data/processed/sg4_new_candidates_seen.json")
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
MACRON_MAP = str.maketrans("āēīōūĀĒĪŌŪ", "aeiouAEIOU")
SECTION_CLAUSE_RE = re.compile(r"^(section|clause)\s+\d+[a-z]*$", re.IGNORECASE)


def normalize(name):
    """Citation-suffix strip + apostrophe fix, PLUS macron-stripping,
    whitespace/NBSP collapsing, trailing-period stripping, and an
    iterative peel of trailing parenthetical annotations. See module
    docstring for why each piece is here."""
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

# ---- rename-aware resolution (unchanged from sg2_step26_v2) ----
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


# ---- reused verbatim from sg2_step26_v2 ----
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
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

sg1_names_norm = {normalize(a["act"]) for a in sg1}
seed_norm = normalize(SEED_ACT_NAME)
sg2_names_norm = {normalize(c["act"]) for c in sg2}
sg3_names_norm = {normalize(c["act"]) for c in sg3}
sg4_names_norm = {normalize(c["act"]) for c in sg4}

fetchable = [d for d in identifiers if d.get("resolved") and d.get("xml_url")]
print(f"{len(fetchable)} SG4 Acts have a fetchable XML URL "
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
        if (cand_norm == source_norm or cand_norm == seed_norm
                or cand_norm in sg1_names_norm or cand_norm in sg2_names_norm
                or cand_norm in sg3_names_norm):
            continue
        if cand_norm in sg4_names_norm:
            internal_pool[cand_norm]["combined_score"] += count
            internal_pool[cand_norm]["linked_from"].append(source_name)
            internal_pool[cand_norm]["display_name"] = candidate
        else:
            new_candidates_seen[cand_norm]["combined_score"] += count
            new_candidates_seen[cand_norm]["linked_from"].append(source_name)
            new_candidates_seen[cand_norm]["display_name"] = candidate

    if i % 20 == 0 or i == len(fetchable):
        print(f"  [{i}/{len(fetchable)}] fetched={n_fetched} cached={n_cached} failed={n_failed} "
              f"pseudo_excluded={n_pseudo_excluded} "
              f"| SG4-internal edges so far: {sum(len(v['linked_from']) for v in internal_pool.values())}")

print(f"\nDone fetching/parsing. fetched={n_fetched} cached={n_cached} failed={n_failed}")
print(f"Section/Clause pseudo-candidates excluded at source: {n_pseudo_excluded}")
print(f"Distinct SG4 Acts that are a target of at least one SG4-internal reference: {len(internal_pool)}")
print(f"Distinct NEW (outside seed/SG1/SG2/SG3/SG4) candidates seen (set aside for SG5): {len(new_candidates_seen)}")

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
print(f"Saved -> {NEW_CANDIDATES_OUT}")
print("\nTop 20 SG4 Acts by number/strength of SG4-internal references pointing at them:")
for c in internal_out[:20]:
    print(f"  {c['act']}  (score {c['combined_score']}, from {len(c['linked_from'])} other SG4 Acts)")
