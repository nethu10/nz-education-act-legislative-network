"""
Before fetching XML for all 437 SG2 Acts to check their internal
connectivity (the SG2 analogue of check_sg1_internal_citations.py /
check_sg1_internal_amendments.py), check how many of them actually have
a parseable citation suffix -- needed to build the legislation.govt.nz
fetch URL, the same way sg2_step1_fetch_targets.py did for SG1. SG2
entries came out of the citation-text extraction pipeline rather than
being hand-verified like SG1, so bare names without a citation suffix
(the same issue "Education Act 1989" had even at the SG1 stage) are
likely more common here -- better to know the real coverage now than
discover it mid-fetch.
"""
import json
import re
from pathlib import Path

SG2_PATH = Path("data/processed/sg2_final_list.json")

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")

def main():
    sg2 = json.loads(SG2_PATH.read_text(encoding="utf-8"))
    print(f"Total SG2 Acts: {len(sg2)}")

    has_citation = []
    missing_citation = []
    for c in sg2:
        name = c["act"]
        if CITE_PATTERN.match(name.strip()):
            has_citation.append(c)
        else:
            missing_citation.append(c)

    print(f"With a parseable citation (fetchable directly): {len(has_citation)}")
    print(f"WITHOUT a parseable citation (need manual/alternate lookup): {len(missing_citation)}")

    print("\nSample of Acts missing a citation suffix (by score, highest first):")
    for c in sorted(missing_citation, key=lambda x: -x.get("combined_score", 0))[:30]:
        print(f"  {c['act']!r}  (score {c.get('combined_score')})")

    Path("data/processed/sg2_missing_citation.json").write_text(
        json.dumps(missing_citation, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nSaved full missing-citation list -> data/processed/sg2_missing_citation.json")

if __name__ == "__main__":
    main()