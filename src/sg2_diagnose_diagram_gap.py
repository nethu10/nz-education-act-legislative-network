"""
Diagnose why make_sg1_sg2_diagram.py only included 310/437 SG2 Acts.

Prints the raw structure first, then tests several normalization
strategies against sg1_names so we can see exactly where the match
is failing, before touching the diagram script.
"""

import json
import re
from pathlib import Path

SG1_PATH = Path("data/processed/sg1_final_list.json")
SG2_PATH = Path("data/processed/sg2_final_list.json")

CITE_PATTERN = re.compile(
    r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$"
)


def normalize(name):
    """Same normalize() used in sg2_step8_merge_and_finalize.py."""
    if not name:
        return name
    name = name.replace("\u2019", "'").replace("\u2018", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()


def strip_citation_only(name):
    if not name:
        return name
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()


def main():
    sg1 = json.loads(SG1_PATH.read_text(encoding="utf-8"))
    sg2 = json.loads(SG2_PATH.read_text(encoding="utf-8"))

    print(f"SG1 entries: {len(sg1)}")
    print(f"SG2 entries: {len(sg2)}")

    print("\n--- Sample SG1 entry (raw keys + values) ---")
    print(json.dumps(sg1[0], indent=2, ensure_ascii=False)[:800])

    print("\n--- Sample SG2 entry (raw keys + values) ---")
    print(json.dumps(sg2[0], indent=2, ensure_ascii=False)[:800])

    # Figure out which field on the SG2 side holds the source-Act list.
    candidate_link_fields = ["linked_from", "sources", "linked", "found_in", "cited_by"]
    link_field = None
    for f in candidate_link_fields:
        if f in sg2[0]:
            link_field = f
            break
    if link_field is None:
        print("\n!! Could not find a linked_from-style field on the SG2 entry.")
        print("Available keys on first SG2 entry:", list(sg2[0].keys()))
        return

    print(f"\nUsing link field: '{link_field}'")

    # Build sg1_names under several normalization strategies.
    sg1_raw = [a.get("act", "") for a in sg1]
    variants = {
        "raw_exact": set(sg1_raw),
        "citation_stripped": {strip_citation_only(n) for n in sg1_raw},
        "apostrophe_fixed_only": {n.replace("\u2019", "'").replace("\u2018", "'") for n in sg1_raw},
        "full_normalize": {normalize(n) for n in sg1_raw},
        "full_normalize_casefold": {normalize(n).casefold() for n in sg1_raw},
    }

    print("\n--- sg1_names set sizes per strategy ---")
    for k, v in variants.items():
        print(f"  {k}: {len(v)} unique names")
    print("\n--- Sample of 5 raw SG1 act strings ---")
    for n in sg1_raw[:5]:
        print(f"  {n!r}")

    # Now test each SG2 entry's linked_from list against each strategy.
    results = {k: 0 for k in variants}
    zero_match_examples = []

    for c in sg2:
        linked_raw = c.get(link_field, []) or []
        matched_any_strategy = False
        for strat_name, names_set in variants.items():
            if strat_name == "full_normalize_casefold":
                hits = [l for l in linked_raw if normalize(l).casefold() in names_set]
            elif strat_name == "full_normalize":
                hits = [l for l in linked_raw if normalize(l) in names_set]
            elif strat_name == "citation_stripped":
                hits = [l for l in linked_raw if strip_citation_only(l) in names_set]
            elif strat_name == "apostrophe_fixed_only":
                hits = [l for l in linked_raw if l.replace("\u2019", "'").replace("\u2018", "'") in names_set]
            else:
                hits = [l for l in linked_raw if l in names_set]
            if hits:
                results[strat_name] += 1
                matched_any_strategy = True

        if not matched_any_strategy:
            zero_match_examples.append({
                "act": c.get("act"),
                "combined_score": c.get("combined_score"),
                link_field: linked_raw,
            })

    print(f"\n--- SG2 entries (out of {len(sg2)}) with >=1 match, per strategy ---")
    for k, v in results.items():
        print(f"  {k}: {v}")

    print(f"\n--- SG2 entries with ZERO matches under ANY strategy: {len(zero_match_examples)} ---")
    for ex in zero_match_examples[:15]:
        print(json.dumps(ex, indent=2, ensure_ascii=False))

    # Also: how many entries have an EMPTY linked_from to begin with?
    empty_link = sum(1 for c in sg2 if not c.get(link_field))
    print(f"\nSG2 entries with an EMPTY '{link_field}' list: {empty_link}")


if __name__ == "__main__":
    main()