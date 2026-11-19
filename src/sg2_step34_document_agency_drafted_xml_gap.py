"""
sg2_step34_document_agency_drafted_xml_gap.py

Confirmed via sg2_step33 (live test, 2026-09-23): legislation.govt.nz does
NOT serve structured PCO XML for agency-drafted secondary legislation
(NZTA's Land Transport Rules, tilde-prefixed identifiers). Every tested
.../agency-drafted/~{year}/~{number}/en/latest.xml URL returns HTTP 500
with an HTML error page, not XML -- this is a genuine, confirmed gap in
what the legislation.govt.nz PCO XML corpus covers, not a wrong identifier
or a network issue. sg2_step10's original validation never actually
tested this (tilde-prefixed entries were deliberately excluded from that
check), so it went unverified until this point in the pipeline.

This does NOT remove these Acts from SG3 -- they are confirmed-real,
correctly-identified documents (Nethmi independently found matching
identifiers by hand for several of them), so they stay as valid SG3
nodes/targets. What changes is documentation only: each agency-drafted
entry with no XML gets an explicit xml_available=False flag and a note,
so:
  (a) this is citable precisely in the methodology/limitations chapter
      (X of 899 SG3 documents -- agency-drafted secondary legislation --
      have no machine-readable text available from the standard
      legislation.govt.nz PCO XML corpus, a structural gap in that data
      source rather than an extraction-pipeline failure), and
  (b) any future re-run or SG4-building script can see at a glance which
      entries to skip rather than re-discovering the same 500 error.

resolved stays True for these entries (the document IS correctly
identified) -- only xml_available changes to False. This is a different,
narrower flag than "resolved", by design.
"""
import json
from pathlib import Path

IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")

with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

n_flagged = 0
for d in identifiers:
    if d.get("resolved") and d.get("subtype") == "agency-drafted":
        d["xml_available"] = False
        d["xml_note"] = (
            "Confirmed via live test (sg2_step33, 2026-09-23): legislation.govt.nz "
            "returns HTTP 500 (HTML error page) for the agency-drafted XML endpoint "
            "pattern (.../agency-drafted/~{year}/~{number}/en/latest.xml). This "
            "document type has no structured PCO XML available from this data "
            "source -- a confirmed gap in the corpus, not an identifier or "
            "extraction error. The document itself is correctly identified "
            "(resolved=True) and remains a valid SG3 node/target; it simply cannot "
            "serve as a source for XML-based amendment/citation extraction."
        )
        n_flagged += 1

with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(identifiers, f, indent=2, ensure_ascii=False)

n_resolved = sum(1 for d in identifiers if d.get("resolved"))
n_xml_available = sum(1 for d in identifiers if d.get("resolved") and d.get("xml_available", True))

print(f"Flagged {n_flagged} agency-drafted entries as xml_available=False")
print(f"Saved -> {IDENTIFIERS_PATH}")
print(f"\nFor the methodology chapter:")
print(f"  {n_resolved}/{len(identifiers)} SG3 Acts correctly identified (resolved=True)")
print(f"  {n_xml_available}/{n_resolved} of those have machine-readable XML available")
print(f"  {n_flagged}/{n_resolved} (agency-drafted secondary legislation) do not -- "
      f"a confirmed corpus limitation, not an extraction-pipeline error")