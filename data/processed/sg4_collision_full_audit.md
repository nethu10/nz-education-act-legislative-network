# SG4 filename-collision audit — all 66 pairs (2026-10-04)

> **CORRECTION (2026-10-04, same day):** The classification table below is accurate
> about which of the 66 pairs are the same document vs genuinely different documents
> vs a misresolution. But the write-up below originally implied all 66 pairs were
> colliding on filenames *within SG4 itself*. That's wrong — the 66 were found by
> checking filename collisions across the **combined SG2+SG3+SG4** identifier sets,
> not SG4 alone. Since each layer stores its raw XML in its own directory
> (`sg2_targets/`, `sg3_targets/`, `sg4_targets/`), only pairs where **both** names
> live in SG4 are a real storage collision — the rest either don't collide at all
> (different directories) or are cross-layer duplicates the SG2↔SG3 audit
> (audit_fix_03/04/05) missed. See `audit_fix_08_cross_layer_duplicates_missed_in_sg4_audit.py`
> and the "Resolution" section at the end of this document for the corrected
> breakdown and what was actually done about each group.

Each of SG4's 1,135 candidate identifiers computes a filename from `{year}_{number}.xml`.
66 of those filenames were claimed by **two different candidate names**. This audit
classifies every pair by live-verifying against legislation.govt.nz (canonical
`/act/public/{year}/{number}/en/latest/` and `/act/local/{year}/{number}/en/latest/`
page titles, the `title_autocomplete` endpoint's `[Previous title: ...]` annotation,
and — where a name looked like a sub-part — a direct anchor/URL check).

## Classification key

- **SAME_DOCUMENT** — both names refer to the exact same real document. Sub-reasons:
  - *rename*: an official previous title (confirmed via `[Previous title: ...]` on live search)
  - *fragment*: one name is a Schedule/Part of the other's parent Act (not a separate document)
  - *variant*: truncated citation, word-reordering, or a "Department of"/"Ministry of"-style
    prefix difference — same Act, same number, different extraction of the title string
- **GENUINE_COLLISION** — two different real documents that legitimately share a
  `{year}_{number}` by coincidence, because they come from **different numbering series**
  (Public Act vs Local Act, or Act vs secondary legislation/Regulations/Rules/Order — each
  series numbers independently within a year).
- **MISRESOLUTION** — not a real collision at all: one of the two names was resolved to the
  *wrong* year/number by the pipeline. The two real documents have different real numbers;
  one candidate needs re-resolving, not deduplicating.

## Results (66/66 classified)

| # | fname | Name A | Name B | Classification | Basis |
|---|---|---|---|---|---|
| 1 | 2011_5.xml | Financial Markets Authority Act 2011 | Schedule 1 of the Financial Markets Authority Act 2011 | SAME_DOCUMENT (fragment) | User-confirmed: `#DLM3231023` anchor redirects into the same Act page |
| 2 | 1991_69.xml | Resource Management Act 1991 | Schedule 1 of the Resource Management Act 1991 | SAME_DOCUMENT (fragment) | Same "Schedule N of X" pattern as #1 |
| 3 | 2018_59.xml | Education Council Amendment Rules 2018 | Reserve Bank of New Zealand (Monetary Policy) Amendment Act 2018 | GENUINE_COLLISION | Rules vs Act — different series. Two distinct real documents (batch_0 verification) |
| 4 | 1989_75.xml | Government Roading Powers Act 1989 | Transit New Zealand Act 1989 | SAME_DOCUMENT (rename) | User-confirmed via screenshot: `[Previous title: Transit New Zealand Act 1989]` |
| 5 | 2002_84.xml | Local Government Act 2002 | Schedule 7 of the Local Government Act 2002 | SAME_DOCUMENT (fragment) | Same "Schedule N of X" pattern as #1 |
| 6 | 1957_87.xml | Summary Proceedings Act 1957 | Summary Proceedings Act 1957 (1957 No 87) (RS Vol 9, p 583) | SAME_DOCUMENT (variant) | Identical core title + bibliographic citation suffix |
| 7 | 2002_9.xml | Sentencing Act 2002 | Energy Efficiency (Energy Using Products) Regulations 2002 | GENUINE_COLLISION | Act vs Regulations — different series |
| 8 | 2019_38.xml | Trusts Act 2019 | Accident Compensation (Experience Rating) Regulations 2019 | GENUINE_COLLISION | Act vs Regulations — different series |
| 9 | 1988_4.xml | Protection of Personal and Property Rights Act 1988 | Personal and Property Rights Act 1988 | SAME_DOCUMENT (variant) | Confirmed identical href (batch_0) |
| 10 | 1995_16.xml | Births, Deaths, Marriages, and Relationships Registration Act 1995 | Births, Deaths, and Marriages Registration Act 1995 | SAME_DOCUMENT (rename) | Canonical title = Name A; Name B is the pre-2021 name |
| 11 | 1974_66.xml | Local Government Act 1974 | Local Government Act 1974 (1974 No 66) (RS Vol 25, p 1) | SAME_DOCUMENT (variant) | Identical core title + citation suffix |
| 12 | 1978_103.xml | Securities Act 1978 | Securities Act 1978 (1978 No 103) (RS Vol 15, p 533) | SAME_DOCUMENT (variant) | Identical core title + citation suffix |
| 13 | 1995_39.xml | Department of Justice (Restructuring) Act 1995 | Justice (Restructuring) Act 1995 | SAME_DOCUMENT (variant) | Confirmed identical href (batch_0) |
| 14 | 1975_9.xml | Ombudsmen Act 1975 | Ombudsmen Act 1975 (1975 No 9) (RS Vol 21, p 657) | SAME_DOCUMENT (variant) | Identical core title + citation suffix |
| 15 | 2025_34.xml | Oversight of Oranga Tamariki System Legislation Amendment Act 2025 | Fisheries (Kaimoana Customary Fishing) Amendment Regulations 2025 | GENUINE_COLLISION | Act vs Regulations — different series |
| 16 | 2008_64.xml | Disability (United Nations Convention on the Rights of Persons with Disabilities) Act 2008 | Persons with Disabilities) Act 2008 | SAME_DOCUMENT (fragment) | User-confirmed: `#DLM1404012` anchor is inside the same Act page |
| 17 | 2012_44.xml | State-Owned Enterprises Amendment Act 2012 | Social Security (Long-term Residential Care) Amendment Regulations (No 3) 2012 | GENUINE_COLLISION | Act vs Regulations — different series |
| 18 | 2002_54.xml | Remuneration Authority (Members of Parliament) Amendment Act 2002 | Parliament) Amendment Act 2002 | SAME_DOCUMENT (variant) | Canonical title = Name A; Name B is a truncated fragment of it |
| 19 | 2017_24.xml | Care and Support Workers (Pay Equity) Settlement Act 2017 | Support Workers (Pay Equity) Settlements Act 2017 (previously named the Care and Support Workers (Pay Equity) Settlement Act 2017) | SAME_DOCUMENT (rename) | User-confirmed via screenshot: `[Previous title: Care and Support Workers (Pay Equity) Settlement Act]` |
| 20 | 2005_53.xml | Corrections Regulations 2005 | Forest and Rural Fires Amendment Act 2005 | GENUINE_COLLISION | Regulations vs Act — different series |
| 21 | 2018_45.xml | Vulnerable Children (Regulated Services) Regulations 2018 | Social Assistance (Residency Qualification) Legislation Act 2018 | GENUINE_COLLISION | Regulations vs Act — different series |
| 22 | 2013_101.xml | Financial Reporting Act 2013 | Land Transport (Road User) Amendment Rule 2013 | GENUINE_COLLISION | Act vs Rule — different series |
| 23 | 2002_38.xml | Sport and Recreation New Zealand Act 2002 | New Zealand Act 2002 | SAME_DOCUMENT (variant) | Canonical title = Name A; Name B is a truncated fragment of it |
| 24 | 1999_82.xml | Department of Child, Youth and Family Services Act 1999 | Child, Youth and Family Services Act 1999 | SAME_DOCUMENT (variant) | Same "Department of" pattern as #13 |
| 25 | 2004_90.xml | Care of Children Act 2004 | Children Act 2004 | SAME_DOCUMENT (variant) | Truncated fragment of the canonical title |
| 26 | 1994_3.xml | National Bank of New Zealand Limited Act 1994 | National Bank of New Zealand Limited Act 1994 (1994 No 3(P)) | SAME_DOCUMENT (variant) | Identical core title + citation suffix |
| 27 | 1989_157.xml | Banking (Prudential Supervision) Act 1989 | Reserve Bank of New Zealand Act 1989 | SAME_DOCUMENT (rename) | Live autocomplete: `[Previous title: Reserve Bank of New Zealand Act 1989]`, current = Banking (Prudential Supervision) Act 1989, both at 1989/157 |
| 28 | 2025_39.xml | Budapest Convention and Related Matters Legislation Amendment Act 2025 | Fisheries (South Island Customary Fishing) Amendment Regulations 2025 | GENUINE_COLLISION | Act vs Regulations — different series |
| 29 | 2018_47.xml | Family Violence (Amendments) Act 2018 | Cremation Amendment Regulations 2018 | GENUINE_COLLISION | Act vs Regulations — different series |
| 30 | 2000_17.xml | Parliamentary Service Act 2000 | Mental Health (Forms) Amendment Regulations 2000 | GENUINE_COLLISION | Act vs Regulations — different series |
| 31 | 2010_36.xml | Electricity (Safety) Regulations 2010 | Local Government (Auckland Council) Amendment Act 2010 | GENUINE_COLLISION | Regulations vs Act — different series |
| 32 | 2014_3.xml | Airports (Cost Recovery for Processing of International Travellers) Act 2014 | Family Courts Amendment Rules 2014 | GENUINE_COLLISION | Act vs Rules — different series |
| 33 | 2023_18.xml | Counter-Terrorism Acts (Designations and Control Orders) Amendment Act 2023 | Witnesses and Interpreters Fees, Allowances, and Expenses Regulations 2023 | GENUINE_COLLISION | Act vs Regulations — different series |
| 34 | 1988_2.xml | Independent Police Conduct Authority Act 1988 | Palmerston North Reserves Empowering Amendment Act 1988 | GENUINE_COLLISION | Public Act 1988/2 vs Local Act 1988/2 — confirmed both resolve live, different series |
| 35 | 2023_14.xml | Organic Products and Production Act 2023 | District Court (Electronic Filing) Amendment Rules 2023 | GENUINE_COLLISION | Act vs Rules — different series |
| 36 | 2016_17.xml | Te Ture mō Te Reo Māori 2016/the Māori Language Act 2016 | Te Ture mō Te Reo Māori 2016 | SAME_DOCUMENT (variant) | Name B is a literal substring of Name A (bilingual vs short title) |
| 37 | 1972_3.xml | Wellington Regional Water Board Act 1972 | Ministry of Agriculture and Fisheries Amendment Act 1972 (1972 No 3) | GENUINE_COLLISION | Public Act 1972/3 vs Local Act 1972/3 — confirmed both resolve live, different series |
| 38 | 2024_47.xml | Contracts of Insurance (Repeals and Amendments) Act 2024 | Overseas Investment (PACER Plus) Amendment Regulations 2024 | GENUINE_COLLISION | Act vs Regulations — different series |
| 39 | 2026_43.xml | Regulatory Systems (Occupational Regulation) Amendment Act 2026 | Fast-track Approvals (Wairakei South and Other Projects) Amendment Order 2026 | GENUINE_COLLISION | Act vs Order — different series |
| 40 | 1996_39.xml | New Zealand Institute of Chartered Accountants Act 1996 | Institute of Chartered Accountants of New Zealand Act 1996 | SAME_DOCUMENT (variant) | Canonical title = Name A; Name B is a word-reordering of it, same number |
| 41 | 1992_55.xml | Industry Training and Apprenticeships Act 1992 | Industry Training Act 1992 | SAME_DOCUMENT (variant) | Canonical title = Name A; Name B is an informal short form (no official previous-title record, but same number) |
| 42 | 2024_36.xml | Gangs Act 2024 | Accident Compensation (Liability to Pay or Contribute to Cost of Treatment) Amendment Regulations 2024 | GENUINE_COLLISION | Act vs Regulations — different series |
| 43 | 1956_7.xml | War Pensions Regulations 1956 | Land Drainage Amendment Act 1956 | GENUINE_COLLISION | Regulations vs Act — different series |
| 44 | 2020_40.xml | Schedule 8 of the Public Service Act 2020 | Public Service Act 2020 | SAME_DOCUMENT (fragment) | Same "Schedule N of X" pattern as #1 |
| 45 | 2016_15.xml | Health and Safety at Work (Asbestos) Regulations 2016 | Sale and Supply of Alcohol (Anzac Day Trading Hours for Licensed RNZRSA Clubs) Amendment Act 2016 | GENUINE_COLLISION | Regulations vs Act — different series |
| 46 | 2026_19.xml | Ngāti Tara Tokanui Claims Settlement Act 2026 | Family Court Amendment Rules 2026 | GENUINE_COLLISION | Act vs Rules — different series |
| 47 | 1992_42.xml | United Nations Sanctions (Somalia) Regulations 1992 | Local Government Amendment Act 1992 | GENUINE_COLLISION | Regulations vs Act — different series |
| 48 | 1996_93.xml | Electoral Regulations 1996 | Airport Authorities Amendment Act 1996 | GENUINE_COLLISION | Regulations vs Act — different series |
| 49 | 2016_19.xml | Health and Safety at Work (Adventure Activities) Regulations 2016 | Local Government (Auckland Council) Amendment Act 2016 | GENUINE_COLLISION | Regulations vs Act — different series |
| 50 | 1995_31.xml | Agriculture and Fisheries (Restructuring) Act 1995 | Ministry of Agriculture and Fisheries (Restructuring) Act 1995 | SAME_DOCUMENT (variant) | Canonical title = Name B; Name A drops the "Ministry of" prefix |
| 51 | 2024_27.xml | Māori Fisheries Amendment Act 2024 | Fisheries (Amateur Fishing) Amendment Regulations 2024 | GENUINE_COLLISION | Act vs Regulations — different series |
| 52 | 2024_35.xml | Family Court Amendment Rules 2024 | Fair Trading (Gift Card Expiry) Amendment Act 2024 | GENUINE_COLLISION | Rules vs Act — different series |
| 53 | 2025_78.xml | Fast-track Approvals Amendment Act 2025 | Criminal Procedure Amendment Rules 2025 | GENUINE_COLLISION | Act vs Rules — different series |
| 54 | 2004_444.xml | Traffic Amendment Regulations (No 3) 2004 | Regulation 3 | SAME_DOCUMENT (fragment) | "Regulation 3" is a clause within the Regulations, not a separate document |
| 55 | 2008_405.xml | Fisheries (Challenger Area Commercial Fishing) Amendment Regulations 2008 | Fisheries (Challenger Area Commercial Fishing) Amendment Regulations (No 2) 2008 | **MISRESOLUTION** | Live autocomplete: Name A is really **2008/271** (`/secondary-legislation/pco-drafted/2008/271/`); Name B really is 2008/405. Name A was resolved to the wrong number by the pipeline |
| 56 | 2014_16.xml | Industry Training and Apprenticeships Amendment Act 2014 | Fisheries (Amateur Fishing) Amendment Regulations 2014 | GENUINE_COLLISION | Act vs Regulations — different series |
| 57 | 2016_13.xml | Health and Safety at Work (General Risk and Workplace Management) Regulations 2016 | Radio New Zealand Amendment Act 2016 | GENUINE_COLLISION | Regulations vs Act — different series |
| 58 | 2026_6.xml | Social Security (Accident Compensation and Calculation of Weekly Income) Amendment Act 2026 | Public Service (Ministry for Cities, Environment, Regions, and Transport) Order 2026 | GENUINE_COLLISION | Act vs Order — different series |
| 59 | 2012_73.xml | Biosecurity Law Reform Act 2012 | Electricity Industry (Enforcement) Amendment Regulations 2012 | GENUINE_COLLISION | Act vs Regulations — different series |
| 60 | 2010_86.xml | Statistics Amendment Act 2010 | War Pensions Amendment Regulations (No 2) 2010 | GENUINE_COLLISION | Act vs Regulations — different series |
| 61 | 1979_3.xml | Bills of Exchange Amendment Act 1979 | Christchurch District Drainage Amendment Act 1979 | GENUINE_COLLISION | Public Act 1979/3 vs Local Act 1979/3 — confirmed both resolve live, different series |
| 62 | 2002_44.xml | Land Transport (Offences and Penalties) Amendment Regulations 2002 | Securities Markets Amendment Act 2002 | GENUINE_COLLISION | Regulations vs Act — different series |
| 63 | 2016_101.xml | Sale and Supply of Alcohol (Display of Low-alcohol Beverages and Other Remedial Matters) Amendment Act 2016 | Overseas Investment Amendment Regulations 2016 | GENUINE_COLLISION | Act vs Regulations — different series |
| 64 | 2014_59.xml | Kaikōura (Te Tai o Marokura) Marine Management Act 2014 | War Pensions Amendment Regulations 2014 | GENUINE_COLLISION | Act vs Regulations — different series |
| 65 | 1996_122.xml | State-Owned Enterprises (Crown Forestry Management Limited) Order 1996 | Fire Service Amendment Act 1996 | GENUINE_COLLISION | Order vs Act — different series |
| 66 | 2016_89.xml | Patents (Trans-Tasman Patent Attorneys and Other Matters) Amendment Act 2016 | Misuse of Drugs (Classification and Presumption of Supply—25B-NBOMe, 25C-NBOMe, and 25I-NBOMe) Order 2016 | GENUINE_COLLISION | Act vs Order — different series |

## Summary

| Classification | Count |
|---|---|
| SAME_DOCUMENT (rename) | 4 (#4, #10, #19, #27) |
| SAME_DOCUMENT (fragment) | 6 (#1, #2, #5, #16, #44, #54) |
| SAME_DOCUMENT (variant) | 15 (#6, #9, #11, #12, #13, #14, #18, #23, #24, #25, #26, #36, #40, #41, #50) |
| **SAME_DOCUMENT total** | **25** |
| GENUINE_COLLISION | **40** |
| MISRESOLUTION | **1** (#55) |
| **Total** | **66** |

## What each category means for the pipeline

- **The 25 SAME_DOCUMENT pairs**: one candidate name is a duplicate/variant string for a
  document SG4 already has correctly under its other name. These resolve the same way the
  6 SG3 cross-layer duplicates did — keep one, drop the other's identifier entry (and its
  XML file, if it has a separate one on disk from a second download).
- **The 40 GENUINE_COLLISION pairs**: two *real, different* documents that legitimately
  share a `{year}_{number}` because they come from independent numbering series (Public
  Act / Local Act / Regulations / Rules / Order each number separately within a year).
  Both belong in SG4 — neither should be dropped. The underlying problem is that SG4's
  `{year}_{number}.xml` filename scheme can't tell them apart, so whichever was
  downloaded/written second may have overwritten the first on disk. This needs a
  type-qualified filename scheme (e.g. include series: `act-public`, `act-local`,
  `sr`/`regulation`) before SG4 can be synced and built — the same kind of fix
  `sg3_filenames.py`'s `SG3_FILENAME_OVERRIDES` made for SG3's 6 cleaner collisions.
- **The 1 MISRESOLUTION pair (#55)**: "Fisheries (Challenger Area Commercial Fishing)
  Amendment Regulations 2008" (without "No 2") was resolved to 2008/405 — the *(No 2)*
  version's real number. Its real number is 2008/271. This one candidate needs
  re-resolving to the correct identifier; it isn't a dedup or a filename-scheme issue.

## Resolution (corrected breakdown and actions taken, 2026-10-04)

Re-checked all 66 pairs against which layer(s) each of the two names actually lives
in (`sg1_final_list.json` / `sg2_...` / `sg3_...` / `sg4_...`). Four groups:

| Group | Count | What it is | Action |
|---|---|---|---|
| A — Genuine intra-SG4 collision | 14 | Both names only in SG4; two real different documents on the same `{year}_{number}.xml` (public Act / local Act / regulation / rule / order each number independently) | Disambiguated via `sg4_filenames.py`'s `SG4_FILENAME_OVERRIDES` — same pattern as `sg3_filenames.py`. 0 remaining collisions across all 1,130 SG4 entries, verified by `find_collisions()`. |
| B — Already resolved, intra-SG4 | 2 | `2004_444.xml` (Regulation 3 fragment) and `2008_405.xml` (the misresolution) | Already fixed earlier today (`audit_fix_07`'s dedup, `audit_fix_06`'s re-resolution to SR 2008/271). No further action. |
| C — Cross-layer, different real documents | 26 | One name in SG2/SG3, the other in SG3/SG4 — genuinely different documents that happen to share a `{year}_{number}` *across different layers' directories*. Not a real collision at all. | None needed. |
| D — Cross-layer duplicate, missed by the SG2↔SG3 audit | 21 | Same real document independently rediscovered under a different name string in a later layer (mostly SG3 rediscovering something SG2 already had; one SG4 rediscovering an SG3 entry) | Removed via `audit_fix_08_cross_layer_duplicates_missed_in_sg4_audit.py`. SG3 final list: 868 → 848. SG4 final list: 1,131 → 1,130. |
| E — Already resolved, cross-layer | 3 | `1994_3.xml`, `1996_39.xml`, `1992_55.xml` — SG4 had independently rediscovered a document SG2/SG3 already had | Removed by `audit_fix_07` (the SG4-side copy was what got dropped in each case, so the "SG4 dedup" framing happened to give the right answer even though the original reasoning was wrong about why). |

14 + 2 + 26 + 21 + 3 = 66. ✓

**Orphaned raw XML files** (exact duplicate content now belonging to a removed
identifier, same situation as the earlier 5 stray/duplicate files found this
session) — safe to delete once confirmed:
- In `data/raw/sg3_targets/`: the 20 files behind Group D's SG3-side removals
  (`2011_5.xml`, `1991_69.xml`, `1989_75.xml`, `2002_84.xml`, `1957_87.xml`,
  `1988_4.xml`, `1995_16.xml`, `1974_66.xml`, `1978_103.xml`, `1995_39.xml`,
  `1975_9.xml`, `2008_64.xml`, `2002_54.xml`, `2017_24.xml`, `2002_38.xml`,
  `1999_82.xml`, `2004_90.xml`, `1989_157.xml`, `2020_40.xml`, `1995_31.xml`) —
  all confirmed present in the container's `sg3_targets/` (850 files total).
- In `data/raw/sg4_targets/` (on the Mac — not yet synced to the container):
  `2016_17.xml`, orphaned by Group D's one SG4-side removal. SG3 already holds
  the real content for this Act under its own `2016_17.xml`.

**SG3 typed edges rebuilt** from the corrected 848-Act list (`sg3_step02_build_typed_edges.py`,
re-run): `sg3_typed_amendment_edges.json` 7,566 → 6,613 edges; `sg3_typed_citation_edges.json`
13,565 → 12,448 edges. Correctness check against `sg1_typed_*.json` + `sg2_typed_*.json`
still passes 0 mismatches. SG2 itself was untouched by this round (Group D only removed
SG3/SG4-side copies, never an SG2 entry), so SG2's typed edges are unchanged.
