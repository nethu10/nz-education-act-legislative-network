"""
sg2_step28_deduplicate_sg3_violence_acts_2025.py

Found by the sg2_step27 "violence" audit: two 2025 companion Acts are each
being cited two ways in the SG3 pool -- their full formal title, and a
shortened form dropping "Victims of". Confirmed via web search (Ministry
of Justice / vLex / legislation.govt.nz) that these are two real, distinct
Acts (sexual violence protections and family violence protections were
passed as companion legislation), each independently suffering the same
citation-text inconsistency:

  Victims of Sexual Violence (Strengthening Legal Protections)
    Legislation Act 2025            <- Sexual Violence (Strengthening
                                        Legal Protections) Legislation
                                        Act 2025               (14 + 2 = 16)
  Victims of Family Violence (Strengthening Legal Protections)
    Legislation Act 2025            <- Family Violence (Strengthening
                                        Legal Protections) Legislation
                                        Act 2025               (13 + 5 = 18)

Same class of issue as sg2_step20's Court/Courts fix (a real citation-text
naming inconsistency, not an extraction bug -- some source Acts' cross-
references drop "Victims of"), but structurally simpler here: both
shortened-form variants score below the SG3 threshold (>=6) on their own,
so they were never admitted to sg3_final_list.json (901 Acts) as separate
rows -- only sg3_combined_final_list.json (the pre-threshold pool) has
both variant and canonical as separate rows. That means:

  - sg3_combined_final_list.json: a normal merge (accumulate both rows
    under the canonical name, drop the variant row) -- 5435 -> 5433.
  - sg3_final_list.json: no rows to merge (the variants were never here),
    just update the two canonical Acts' combined_score in place to match
    the corrected combined-pool totals. Still 901 rows -- nothing crosses
    the threshold either way, since both canonical entries already
    qualified on their own.
  - sg3_act_identifiers.json: untouched -- the variants were never part of
    the 901-row identifiers file to begin with (built from
    sg3_final_list.json), so there's nothing to reconcile there, unlike
    the Court/Courts case.
"""
import json
from pathlib import Path

SG3_FINAL_PATH = Path("data/processed/sg3_final_list.json")
SG3_COMBINED_PATH = Path("data/processed/sg3_combined_final_list.json")

MERGE_PAIRS = [
    ("Victims of Sexual Violence (Strengthening Legal Protections) Legislation Act 2025",
     "Sexual Violence (Strengthening Legal Protections) Legislation Act 2025"),
    ("Victims of Family Violence (Strengthening Legal Protections) Legislation Act 2025",
     "Family Violence (Strengthening Legal Protections) Legislation Act 2025"),
]
name_to_canonical = {variant: canonical for canonical, variant in MERGE_PAIRS}
canonicals = {canonical for canonical, _ in MERGE_PAIRS}


def merge_combined_pool(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"{path}: {len(data)} entries before")

    merged = {}
    for c in data:
        name = c["act"]
        canonical = name_to_canonical.get(name, name)
        if canonical not in merged:
            merged[canonical] = {
                "act": canonical,
                "amendment_score": 0,
                "citation_score": 0,
                "combined_score": 0,
                "linked_from": set(),
            }
        merged[canonical]["amendment_score"] += c.get("amendment_score", 0)
        merged[canonical]["citation_score"] += c.get("citation_score", 0)
        merged[canonical]["combined_score"] += c.get("combined_score", 0)
        merged[canonical]["linked_from"].update(c.get("linked_from", []))

    new_data = []
    for d in merged.values():
        d["linked_from"] = sorted(d["linked_from"])
        new_data.append(d)
    new_data.sort(key=lambda c: -c["combined_score"])

    print(f"{path}: {len(new_data)} entries after (merged {len(data) - len(new_data)})")
    for canonical, _ in MERGE_PAIRS:
        c = merged.get(canonical)
        if c:
            print(f"  {canonical!r}: combined_score now {c['combined_score']}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print()
    return {c["act"]: c["combined_score"] for c in new_data}


def update_final_list_scores(path, corrected_scores):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"{path}: {len(data)} entries before")
    n_updated = 0
    for c in data:
        if c["act"] in canonicals and c["act"] in corrected_scores:
            old = c["combined_score"]
            new = corrected_scores[c["act"]]
            if old != new:
                print(f"  {c['act']!r}: combined_score {old} -> {new}")
                c["combined_score"] = new
                n_updated += 1

    data.sort(key=lambda c: -c["combined_score"])
    print(f"{path}: {len(data)} entries after ({n_updated} score(s) updated, row count unchanged)\n")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


corrected_scores = merge_combined_pool(SG3_COMBINED_PATH)
update_final_list_scores(SG3_FINAL_PATH, corrected_scores)

print("Done. sg3_act_identifiers.json not touched -- the shortened-form variants")
print("were never part of it (both canonical Acts were already separately resolved).")