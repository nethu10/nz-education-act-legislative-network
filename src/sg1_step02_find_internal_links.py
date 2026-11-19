"""
sg1_step02_find_internal_links.py

Stage 2 of retrofitting the internal-link check onto SG1 (see
sg1_step01_resolve_identifiers.py for why this was missing): fetch XML for
each of the 37 resolved SG1 Acts, extract amendment records the same way
sg2_step2/sg2_step11 do, and check whether each reference lands on ANOTHER
SG1 Act -- i.e. do any of the 37 Acts directly connected to the seed also
cite or amend each other, independent of the seed itself.

Deliberately scoped to seed + SG1 only, matching how sg2_step11 was scoped
to seed + SG1 + SG2 for its own layer. A reference to anything outside
seed+SG1 is recorded separately (sg1_new_candidates_seen.json) rather than
chased further here -- for a sanity check against the existing SG2 pool,
not because SG1 needs to discover new Acts (SG2 was already built
independently, from the seed's own citations).

Resumable: raw XML is cached to disk as it's fetched, so re-running after
an interruption skips Acts already downloaded.

BLOCKED as of 2026-09-25: same network block as sg1_step01 -- this
workspace currently cannot reach legislation.govt.nz. Written and ready,
NOT yet run or validated. Run sg1_step01 first (it must succeed and
produce sg1_act_identifiers.json before this script has anything to fetch).

Run from the repo root, after sg1_step01_resolve_identifiers.py:
    python src/sg1_step02_find_internal_links.py

Inputs:
  data/processed/sg1_final_list.json
  data/processed/sg1_act_identifiers.json   (built by sg1_step01)

Outputs:
  data/raw/sg1_targets/{year}_{number}.xml    -- cached raw XML
  data/processed/sg1_internal_links.json      -- SG1-to-SG1 edges found
  data/processed/sg1_new_candidates_seen.json -- refs outside seed/SG1 (sanity check only)
"""
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import requests
from lxml import etree

SG1_PATH = Path("data/processed/sg1_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg1_act_identifiers.json")
RAW_DIR = Path("data/raw/sg1_targets")
LINKS_OUT = Path("data/processed/sg1_internal_links.json")
NEW_CANDIDATES_OUT = Path("data/processed/sg1_new_candidates_seen.json")
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
    """Same normalize() as sg2_step8/sg2_step11: strip citation suffix, fix curly apostrophes."""
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()


# ---- reused verbatim from sg2_step2_build_candidates.py / sg2_step11 ----
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


def main():
    with open(SG1_PATH, encoding="utf-8") as f:
        sg1 = json.load(f)
    with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
        identifiers = json.load(f)

    sg1_names_norm = {normalize(a["act"]) for a in sg1}
    seed_norm = normalize(SEED_ACT_NAME)

    fetchable = [d for d in identifiers if d.get("resolved") and d.get("xml_url")]
    print(f"{len(fetchable)} SG1 Acts have a fetchable XML URL "
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
        for rec in incoming:
            if rec["amending_act"]:
                per_candidate_counts[rec["amending_act"]] += 1
        for rec in outgoing:
            if rec["target_act"]:
                per_candidate_counts[rec["target_act"]] += 1

        for candidate, count in per_candidate_counts.items():
            cand_norm = normalize(candidate)
            if cand_norm == source_norm or cand_norm == seed_norm:
                continue  # self-reference or seed -- not new information
            if cand_norm in sg1_names_norm:
                internal_pool[cand_norm]["combined_score"] += count
                internal_pool[cand_norm]["linked_from"].append(source_name)
                internal_pool[cand_norm]["display_name"] = candidate
            else:
                new_candidates_seen[cand_norm]["combined_score"] += count
                new_candidates_seen[cand_norm]["linked_from"].append(source_name)
                new_candidates_seen[cand_norm]["display_name"] = candidate

        if i % 10 == 0 or i == len(fetchable):
            print(f"  [{i}/{len(fetchable)}] fetched={n_fetched} cached={n_cached} failed={n_failed} "
                  f"| SG1-internal edges so far: {sum(len(v['linked_from']) for v in internal_pool.values())}")

    print(f"\nDone fetching/parsing. fetched={n_fetched} cached={n_cached} failed={n_failed}")
    print(f"Distinct SG1 Acts that are a target of at least one SG1-internal reference: {len(internal_pool)}")
    print(f"Distinct candidates seen outside seed/SG1 (sanity check vs. existing SG2 pool, not chased further): "
          f"{len(new_candidates_seen)}")

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
    print("\nAll SG1-internal edges found (there should only be a handful, out of 37 Acts):")
    for c in internal_out:
        print(f"  {c['act']}  (score {c['combined_score']}, from {len(c['linked_from'])} other SG1 Acts: "
              f"{c['linked_from']})")

    print("\nNext: fold data/processed/sg1_internal_links.json into the graph assembly step")
    print("(assemble_multiedge_graph.py) alongside sg2/sg3/sg4/sg5_internal_links.json,")
    print("so SG1's own internal edges are represented, not just its edges to the seed.")


if __name__ == "__main__":
    main()
