"""
sg2_step31_remove_final_exclusions.py

Two final SG3 exclusion decisions, confirmed with Nethmi on 2026-09-23,
each for a DIFFERENT reason -- kept distinct here deliberately, since
this is the record to cite in the thesis methodology chapter and
misreporting one as the other would misstate what the pipeline actually
found.

1. "Health Reforms (Transitional Provisions) Act 1993"
   Category: EXTRACTION ARTIFACT (not a real document)
   Evidence: No matching title anywhere on legislation.govt.nz's title
   search, and no match anywhere on the wider web. The closest real
   candidate, "Health Sector (Transfers) Act 1993" (No 23), has a
   different name entirely. Reads as a mis-captured descriptive phrase
   about the 1990s health-sector reforms generally, not a real,
   separately-citable document -- the same class of issue as the
   invalid_name exclusion category already applied earlier in the
   pipeline (sg2_step4/step14), just one that slipped through because it
   syntactically resembles a valid "X Act YYYY" name.

2. "Transport (Driving Hours Logbook Exemption) Notice 2003"
   Category: CONFIRMED REAL DOCUMENT, OUT OF PIPELINE SCOPE
   Evidence: Confirmed via web search to be a real NZ Gazette notice
   (gazette.govt.nz/notice/id/2003-au5133), published on the Gazette
   system rather than legislation.govt.nz. No structured PCO XML exists
   for it to fetch, so it cannot be processed by this pipeline's
   XML-based amendment/citation extraction regardless of whether an
   identifier is assigned. This is NOT a data-quality problem with the
   citation extraction -- the candidate is genuine and correctly found;
   it's a scope limitation (one data source among possibly several
   NZ legislative-instrument systems) worth naming explicitly as a
   limitation in the methodology chapter, distinct from an extraction
   error.

Removes both entries from:
  data/processed/sg3_final_list.json           (901 -> 899)
  data/processed/sg3_combined_final_list.json  (pre-threshold pool)
  data/processed/sg3_act_identifiers.json

Writes a dedicated audit record:
  data/processed/sg3_manual_exclusions.json    -- both exclusions with
  full justification text, for direct reference in the thesis.
"""
import json
from pathlib import Path

SG3_PATH = Path("data/processed/sg3_final_list.json")
SG3_COMBINED_PATH = Path("data/processed/sg3_combined_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")
EXCLUSIONS_OUT = Path("data/processed/sg3_manual_exclusions.json")

EXCLUSIONS = [
    {
        "act": "Health Reforms (Transitional Provisions) Act 1993",
        "category": "extraction_artifact",
        "justification": (
            "No matching title found on legislation.govt.nz's title search or "
            "anywhere on the wider web. The closest real candidate, 'Health Sector "
            "(Transfers) Act 1993' (No 23), has a different name entirely. Assessed "
            "as a mis-captured descriptive phrase from the original citation "
            "extraction (about the 1990s health-sector reforms generally), not a "
            "real, separately-citable document -- the same class of issue as the "
            "invalid_name exclusion category applied earlier in the pipeline "
            "(sg2_step4/step14)."
        ),
        "decided": "2026-09-23",
    },
    {
        "act": "Transport (Driving Hours Logbook Exemption) Notice 2003",
        "category": "confirmed_real_but_out_of_pipeline_scope",
        "justification": (
            "Confirmed via web search to be a real NZ Gazette notice "
            "(gazette.govt.nz/notice/id/2003-au5133), published on the Gazette "
            "system rather than legislation.govt.nz. No structured PCO XML exists "
            "for it, so this pipeline's XML-based amendment/citation extraction "
            "cannot process it regardless of identifier assignment. This is a "
            "pipeline scope limitation (Gazette notices are outside the "
            "legislation.govt.nz PCO XML corpus), NOT an extraction error -- the "
            "candidate itself is genuine and was correctly identified as relevant."
        ),
        "decided": "2026-09-23",
    },
]
target_names = {e["act"] for e in EXCLUSIONS}


def remove_from(path, key="act"):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    before = len(data)
    new_data = [c for c in data if c.get(key) not in target_names]
    removed = before - len(new_data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print(f"{path}: {before} -> {len(new_data)} ({removed} removed)")
    return new_data


sg3_after = remove_from(SG3_PATH)
remove_from(SG3_COMBINED_PATH)
identifiers_after = remove_from(IDENTIFIERS_PATH)

with open(EXCLUSIONS_OUT, "w", encoding="utf-8") as f:
    json.dump(EXCLUSIONS, f, indent=2, ensure_ascii=False)
print(f"\nSaved audit record -> {EXCLUSIONS_OUT}")

n_resolved = sum(1 for d in identifiers_after if d.get("resolved"))
print(f"\nSG3 now {len(sg3_after)} Acts.")
print(f"Identifiers: {n_resolved}/{len(identifiers_after)} resolved ({n_resolved/len(identifiers_after):.1%})")

print("\nSummary for the methodology chapter:")
for e in EXCLUSIONS:
    print(f"  [{e['category']}] {e['act']!r}")