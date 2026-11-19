# SG2 "420/421" XML gap — investigation findings (2026-10-04)

## The gap

SG2's final list has 421 Acts; only 420 have local XML. The 421st is:

- **Land Transport Rule 32006/1: Frontal Impact 2001**
  `https://legislation.govt.nz/secondary-legislation/agency-drafted/~2025/~275499/en/latest/`
  `type: secondary-legislation`, `status: agency-drafted`, `resolved_via: manual_lookup`

## Re-verified live (2026-10-04): the XML gap is real and permanent

- The page on legislation.govt.nz is explicitly an **"agency published"** record — a pilot
  collection of secondary legislation hosted on agency websites, not PCO-drafted. It says so
  directly: *"Get this legislation from agency website"*, linking to NZTA's own site.
- The only full text available anywhere is a PDF on NZTA's own website:
  `https://www.nzta.govt.nz/assets/resources/rules/docs/frontal-impact-2001-as-at-1-may-2021.pdf`
  — the same PDF reprint already manually obtained per the identifier's existing note.
- Direct fetch of the standard agency-drafted XML endpoint pattern
  (`.../agency-drafted/~2025/~275499/en/latest.xml`) returns **HTTP 500** with an HTML error
  page, not XML — re-confirmed live, same failure mode as the 22-entry SG3 agency-drafted gap
  (`sg2_step33`/`sg2_step34`, originally tested 2026-09-23).
- Conclusion: no structured PCO XML exists for this document from this data source. This is a
  genuine corpus limitation, not a fetch bug — nothing to retry.

## But: two real edges into this Rule were sitting unextracted

`sg2_step35`'s member-building loop only added an entry to the member list (and therefore to
the name-matching universe, `all_norms`) when its own local XML file existed. Because this Rule
has no XML, it was **excluded from `all_norms` entirely** — not just skipped as a parse source.
That silently discarded any *other* Act's real, taggable reference to it, even though the
outgoing-fallback extraction path (for amendment targets named only in a `schedule.amendments.
group2` heading, with no incoming `history-note` on the target's own side) already existed and
was designed for exactly this case.

Grepping the raw XML for "Frontal Impact" turned up two real, previously-unextracted outgoing
amendment signals naming this Rule:

| Source (own XML has the schedule heading) | Layer | Heading text found |
|---|---|---|
| Immigration Act 2009 (2009 No 51) | SG1 | `Land Transport Rule 32006/1: Frontal Impact 2001` |
| Land Transport Management Amendment Act 2008 (2008 No 47) | SG2 | `Land Transport Rule: Frontal Impact 2001 (32006/1)` |

The second one uses a different word order for the same document, so even after fixing the
registration gap it still didn't resolve as the same entity under plain `normalize()`. Fixed
with one narrow, hand-verified alias (`NAME_VARIANT_ALIASES`), scoped to only this confirmed
case — same philosophy as `SG3_FILENAME_OVERRIDES` in `sg3_filenames.py`: the simplest fix that
matches what's really there, not a general fuzzy-match rule.

(Two further plain-text mentions of "Frontal Impact 2001" turned up in SG3 XML —
`1999_27.xml` and `2014_291.xml` — but both are prose inside a fees provision, not a
`<citation>` tag or schedule heading, so they correctly stay untagged, consistent with how
every other untagged prose mention is treated throughout this pipeline.)

## Fix applied

`sg2_step36_build_typed_edges_v2.py` supersedes `sg2_step35_build_typed_edges.py`:

1. Registers every final-list member's name in `all_norms` regardless of whether local XML
   exists (`has_xml` flag per member). A no-XML member can never be a parse **source** (there's
   no file to read) but can now correctly resolve as an edge **target**.
2. Adds the one narrow name-variant alias above.
3. Re-verified the fix doesn't disturb the already-published `sg1_typed_*.json` (seed/SG1-only
   subset): 85/85 amendment pairs, 230/230 citation pairs, 0 mismatches — safe to apply.

## Result

- `sg2_typed_amendment_edges.json`: **4,251 → 4,253** amendment edges (+2, both recovered
  boundary/internal edges into the Rule — both `operation_source: "outgoing_fallback"`,
  `confirmed_by_outgoing_schedule: true`).
- `sg2_typed_citation_edges.json`: unchanged (7,461 — neither recovered reference was a
  `<citation>` tag).
- The Rule itself (`resolved: true`, `no_xml_available: true`) remains correctly excluded as a
  possible **source** everywhere downstream (SG3/SG4/SG5 edge-building): it has two confirmed
  real incoming edges and zero possible outgoing ones, which is exactly right for a document
  whose text is genuinely unavailable in structured form.

## Follow-on: this investigation surfaced 4 more cross-layer duplicates

Checking whether this exact document also existed under a different name in SG3's own list
(it did — see below) led to a full systematic audit, which turned up 4 more real cross-layer
duplicates beyond this investigation's original scope:

- **`audit_fix_04`**: SG3 had independently re-discovered this exact same no-XML Rule under its
  own name variant, `"Land Transport Rule: Frontal Impact 2001 (32006/1)"` — same URL, same
  year/number. Removed from SG3 (872 → 871); SG2's entry stays canonical.
- **`audit_fix_05`**: a systematic normalized-name audit across all layer pairs (catching
  citation-suffix, NBSP, macron, and bare-name variants at once) found 3 more, this time
  confirmed via **MD5-identical raw XML content**, not just matching metadata:
  - SG1 `"Legislation Act 2019 (2019 No 58)"` == SG3 `"Legislation Act 2019"`
  - SG2 `"Financial Markets Conduct Act 2013"` == SG3 `"Financial Markets Conduct Act 2013"`
  - SG2 `"Territorial Sea, Contiguous Zone, and Exclusive Economic Zone Act 1977"` == SG3 (same)

  All 3 share `resolved_via: "schedule_of_parent"` — they entered SG3's list through a later
  resolution path that never re-checked against the already-finalized SG1/SG2 name sets,
  unlike the earlier NBSP/word-order dupes which slipped through `sg2_step26`'s normalize()
  gap. Removed from SG3 (871 → 868); SG1/SG2's entries stay canonical.

**3 orphaned duplicate XML files remain in `data/raw/sg3_targets/` on the Mac**, exact
byte-for-byte copies of files already in `sg1_targets/`/`sg2_targets/` (same situation as the
2 earlier stray files Nethmi deleted herself) — flagged for the same treatment, not deleted
here:
  - `data/raw/sg3_targets/2019_58.xml`
  - `data/raw/sg3_targets/2013_69.xml`
  - `data/raw/sg3_targets/1977_28.xml`

**SG3 final count: 872 → 868** (6 cross-layer duplicates found and removed in total across this
project: audit_fix_03's 2 + audit_fix_04's 1 + audit_fix_05's 3). `sg3_typed_amendment_edges.json`
(7,566 edges) and `sg3_typed_citation_edges.json` (13,565 edges) were built from the fully
corrected 868-Act list, with a 0-mismatch correctness check against the union of the published
`sg1_typed_*.json` + the corrected `sg2_typed_*.json`.
