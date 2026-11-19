"""
sg2_step26_find_sg3_internal_links.py

The SG3 sequel to sg2_step11_find_internal_links.py: fetch XML for all
resolved SG3 Acts (894/901), extract amendment/citation records the same
way step2/step11 did, and this time check whether each reference lands on
ANOTHER SG3 Act (not just seed/SG1/SG2, which is all step11 checked for).

Resumable: raw XML is cached to disk as it's fetched, so re-running after
an interruption skips Acts already downloaded. Paced at ~1 request/second
for the fetches that do happen -- 894 Acts, so expect this to take a
while; let it run and paste back the printed summary when done.

Rename-awareness: reuses step11's RENAME_MAP (old/historical Act names
that resolve to a current SG2 node) PLUS the 3 Court/Courts naming variants
merged in sg2_step20 (Family Court Act 1980, District Court Rules 2014,
Family Court Rules 2002). Raw XML text can still literally cite "Family
Courts Act 1980" even though the canonical SG3 node is now the singular
"Family Court Act 1980" -- without this mapping, every such reference
would wrongly look like a new outside reference instead of the SG3 node it
actually is.

Deliberately scoped to seed + SG1 + SG2 + SG3 only: any reference to
something outside all four of those sets is recorded separately
(sg3_new_candidates_seen.json) as the future SG4 pool, but not chased
further here.

Inputs:
  data/processed/sg1_final_list.json
  data/processed/sg2_final_list.json
  data/processed/sg3_final_list.json           -- 901 Acts (post step20 dedup)
  data/processed/sg3_act_identifiers.json      -- 901 Acts, 894 resolved (post step25 reconcile)

Outputs:
  data/raw/sg3_targets/{year}_{number}.xml      -- cached raw XML
  data/processed/sg3_internal_links.json        -- SG3-to-SG3 edges found
  data/processed/sg3_new_candidates_seen.json   -- refs outside seed/SG1/SG2/SG3 (for SG4 later, not used now)
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
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")
RAW_DIR = Path("data/raw/sg3_targets")
LINKS_OUT = Path("data/processed/sg3_internal_links.json")
NEW_CANDIDATES_OUT = Path("data/processed/sg3_new_candidates_seen.json")
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

def normalize(name):
    """Same normalize() as sg2_step8/step11: strip citation suffix, fix curly apostrophes."""
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()

# ---- rename-aware resolution, extended for SG3 ----
# Same RENAME_MAP as sg2_step11/step13/step15, PLUS the 3 Court/Courts
# naming-inconsistency pairs merged in sg2_step20 (confirmed via
# sg2_step25 to resolve to the exact same legislation.govt.nz identifier
# on both sides -- this is a real citation-text duplicate, not a rename).
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
    # fragments of an excluded hub Act / an SG1 Act, not real documents
    "Schedule 2 of the Public Service Act 2020": None,
    "Schedule 6 of the Public Service Act 2020": None,
    "Schedule 1 of the Privacy Act 2020": None,
    # Court/Courts citation-text duplicates (sg2_step20, confirmed same
    # identifier by sg2_step25) -- map the incorrect plural to the
    # canonical singular SG3 node name.
    "Family Courts Act 1980": "Family Court Act 1980",
    "District Courts Rules 2014": "District Court Rules 2014",
    "Family Courts Rules 2002": "Family Court Rules 2002",
    # 2025 companion-Act citation-text duplicates (sg2_step27 audit +
    # sg2_step28 merge) -- some source Acts drop "Victims of" when
    # cross-referencing these.
    "Sexual Violence (Strengthening Legal Protections) Legislation Act 2025":
        "Victims of Sexual Violence (Strengthening Legal Protections) Legislation Act 2025",
    "Family Violence (Strengthening Legal Protections) Legislation Act 2025":
        "Victims of Family Violence (Strengthening Legal Protections) Legislation Act 2025",
}

def resolve_canonical(name):
    """normalize() (citation-suffix + apostrophe) THEN apply the rename map,
    so a reference under any old/variant/historical name resolves to the
    same node its current SG-layer entry uses. Returns None for names that
    are confirmed fragments of an excluded/SG1 Act, not a real document."""
    n = normalize(name)
    if n in RENAME_MAP:
        return RENAME_MAP[n]
    return n


# ---- reused verbatim from sg2_step2_build_candidates.py / step11 ----
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
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

sg1_names_norm = {normalize(a["act"]) for a in sg1}
seed_norm = normalize(SEED_ACT_NAME)
sg2_names_norm = {normalize(c["act"]) for c in sg2}
sg3_names_norm = {normalize(c["act"]) for c in sg3}

fetchable = [d for d in identifiers if d.get("resolved") and d.get("xml_url")]
print(f"{len(fetchable)} SG3 Acts have a fetchable XML URL "
      f"({len(identifiers) - len(fetchable)} skipped: unresolved or no XML available)\n")

internal_pool = defaultdict(lambda: {"combined_score": 0, "linked_from": []})
new_candidates_seen = defaultdict(lambda: {"combined_score": 0, "linked_from": []})

n_fetched = 0
n_cached = 0
n_failed = 0

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
            continue  # confirmed fragment of an excluded/SG1 Act, not a real document
        if cand_norm == source_norm or cand_norm == seed_norm or cand_norm in sg1_names_norm or cand_norm in sg2_names_norm:
            continue  # self-reference, seed, already SG1, or already SG2 -- not new information
        if cand_norm in sg3_names_norm:
            internal_pool[cand_norm]["combined_score"] += count
            internal_pool[cand_norm]["linked_from"].append(source_name)
            internal_pool[cand_norm]["display_name"] = candidate
        else:
            new_candidates_seen[cand_norm]["combined_score"] += count
            new_candidates_seen[cand_norm]["linked_from"].append(source_name)
            new_candidates_seen[cand_norm]["display_name"] = candidate

    if i % 20 == 0 or i == len(fetchable):
        print(f"  [{i}/{len(fetchable)}] fetched={n_fetched} cached={n_cached} failed={n_failed} "
              f"| SG3-internal edges so far: {sum(len(v['linked_from']) for v in internal_pool.values())}")

print(f"\nDone fetching/parsing. fetched={n_fetched} cached={n_cached} failed={n_failed}")
print(f"Distinct SG3 Acts that are a target of at least one SG3-internal reference: {len(internal_pool)}")
print(f"Distinct NEW (outside seed/SG1/SG2/SG3) candidates seen (set aside for SG4, not used now): {len(new_candidates_seen)}")

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
print("\nTop 20 SG3 Acts by number/strength of SG3-internal references pointing at them:")
for c in internal_out[:20]:
    print(f"  {c['act']}  (score {c['combined_score']}, from {len(c['linked_from'])} other SG3 Acts)")
