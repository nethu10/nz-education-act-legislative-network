# Stage 7b: seed-centred Katz on the cleaned graph (after audit_fix_12)

Graph: 2475 nodes, 30,515 collapsed edges. alpha = 0.9/lambda_max = 0.00120. Seed = Education and Training Act 2020.

## 1. Global Katz: before and after audit_fix_12 (full corpus, weighted)

| Graph | Nodes | Seed rank | Top-5 |
|---|---|---|---|
| before (unmerged) | 2481 | 20 of 2481 | Tax Administration Act 1994; Income Tax Act 2007; Legislation Act 2019; Goods and Services Tax Act 1985; Resource Management Act 1991 |
| after (cleaned, dedupe) | 2475 | 19 of 2475 | Tax Administration Act 1994; Income Tax Act 2007; Legislation Act 2019; Goods and Services Tax Act 1985; Resource Management Act 1991 |
| upper bracket (duplicates summed) | 2475 | 13 of 2475 | Tax Administration Act 1994; Income Tax Act 2007; Legislation Act 2019; Goods and Services Tax Act 1985; Resource Management Act 1991 |

| Merged Act | Rank before | Rank after |
|---|---|---|
| Crown Entities Act 2004 | 13 | 17 |
| Education and Training Act 2020 | 20 | 19 |
| Financial Markets Supervisors Act 2011 | 378 | 339 |
| Government Superannuation Fund Act 1956 | 15 | 16 |
| Health Sector | 232 | 221 |
| Social Security Act 2018 | 21 | 21 |

## 2. Seed-centred Katz (full corpus, weighted)

### 2a. DOWNSTREAM: Acts that rely on the Education and Training Act 2020 (would need review if it changed)

| Seed-rank | Act | Layer | Seed-centred | Global rank | Lift |
|---|---|---|---|---|---|
| 1 | Education and Training (Vocational Education and Training Sy | SG2 | 1.000 | 954 | +953 |
| 2 | Education and Training Amendment Act 2022 | SG2 | 0.948 | 1307 | +1305 |
| 3 | Education and Training Amendment Act 2024 | SG2 | 0.909 | 903 | +900 |
| 4 | Taxation (International Taxation, Life Insurance, and Remedi | SG4 | 0.791 | 202 | +198 |
| 5 | Education and Training (System Reform) Amendment Act 2026 | SG2 | 0.598 | 1307 | +1302 |
| 6 | Secondary Legislation Act 2021 | SG4 | 0.563 | 576 | +570 |
| 7 | Education and Training Amendment Act 2023 | SG2 | 0.388 | 1483 | +1476 |
| 8 | Income Tax Act 2007 (2007 No 97) | SG1 | 0.294 | 2 | -6 |
| 9 | Education (Name Change for NZIST) Order 2020 | SG2 | 0.248 | 1671 | +1662 |
| 10 | Taxation (Annual Rates for 2024–25, Emergency Response, and  | SG4 | 0.244 | 482 | +472 |
| 11 | Taxation (Annual Rates for 2025–26, Compliance Simplificatio | SG4 | 0.221 | 305 | +294 |
| 12 | Tax Administration Act 1994 (1994 No 166) | SG1 | 0.209 | 1 | -11 |
| 13 | Education and Training Amendment Act 2025 | SG2 | 0.208 | 954 | +941 |
| 14 | Taxation (Tax Administration and Remedial Matters) Act 2011 | SG4 | 0.190 | 326 | +312 |
| 15 | Income Tax Act 2004 | SG2 | 0.176 | 11 | -4 |

### 2b. UPSTREAM: Acts the Education and Training Act 2020 relies on

| Seed-rank | Act | Layer | Seed-centred | Global rank | Lift |
|---|---|---|---|---|---|
| 1 | Tax Administration Act 1994 (1994 No 166) | SG1 | 1.000 | 1 | +0 |
| 2 | Legislation Act 2019 (2019 No 58) | SG1 | 0.934 | 3 | +1 |
| 3 | Income Tax Act 2007 (2007 No 97) | SG1 | 0.787 | 2 | -1 |
| 4 | Crown Entities Act 2004 (2004 No 115) | SG1 | 0.421 | 17 | +13 |
| 5 | Government Superannuation Fund Act 1956 (1956 No 47) | SG1 | 0.230 | 16 | +11 |
| 6 | Goods and Services Tax Act 1985 | SG2 | 0.213 | 4 | -2 |
| 7 | Accident Compensation Act 2001 | SG2 | 0.174 | 7 | +0 |
| 8 | Employment Relations Act 2000 (2000 No 24) | SG1 | 0.173 | 39 | +31 |
| 9 | State Sector Act 1988 | SG2 | 0.167 | 133 | +124 |
| 10 | Teaching Council Rules 2016 (LI 2016/122) | SG1 | 0.157 | 357 | +347 |
| 11 | Social Security Act 2018 (2018 No 32) | SG1 | 0.134 | 21 | +10 |
| 12 | Privacy Act 2020 (2020 No 31) | SG1 | 0.121 | 38 | +26 |
| 13 | Education (Stand-Down, Suspension, Exclusion, and Expulsion) | SG1 | 0.116 | 412 | +399 |
| 14 | KiwiSaver Act 2006 | SG2 | 0.115 | 8 | -6 |
| 15 | Education Act 1989 (1989 No 80) | SG1 | 0.114 | 12 | -3 |

### 2c. Most SEED-SPECIFIC downstream (top-100 seed-centred, sorted by lift over global rank)

| Act | Layer | Seed-rank | Global rank | Lift |
|---|---|---|---|---|
| Legislation Act (Amendments to Legislation) Regulations 2021 | SG3 | 33 | 2225 | +2192 |
| Taxation (KiwiSaver) Act 2007 | SG4 | 39 | 2225 | +2186 |
| Education (Name Change for NZIST) Order 2020 | SG2 | 9 | 1671 | +1662 |
| COVID-19 Response (Taxation and Other Regulatory Urgent Meas | SG2 | 48 | 1698 | +1650 |
| Education and Training Amendment Act 2023 | SG2 | 7 | 1483 | +1476 |
| Education and Training (Early Childhood Education Reform) Am | SG2 | 22 | 1483 | +1461 |
| Education and Training Amendment Act 2022 | SG2 | 2 | 1307 | +1305 |
| Education and Training (System Reform) Amendment Act 2026 | SG2 | 5 | 1307 | +1302 |
| Student Loan Scheme Amendment Act 2013 | SG3 | 97 | 1330 | +1233 |
| Social Security (Modernisation) Amendment Act 2026 | SG4 | 87 | 1281 | +1194 |

Generic hubs (global top-5) and their seed-centred rank, downstream: Tax Administration Act 1994 -> 12; Income Tax Act 2007 -> 8; Legislation Act 2019 -> 105; Goods and Services Tax Act 1985 -> 27; Resource Management Act 1991 -> 215

### 2c. Most SEED-SPECIFIC upstream (top-100 seed-centred, sorted by lift over global rank)

| Act | Layer | Seed-rank | Global rank | Lift |
|---|---|---|---|---|
| Teaching Council of Aotearoa New Zealand Election Rules 2018 | SG1 | 97 | 829 | +732 |
| Education (2020 School Staffing) Order 2019 (LI 2019/180) | SG1 | 71 | 801 | +730 |
| International Student Contract Dispute Resolution Scheme Rul | SG1 | 70 | 749 | +679 |
| Education (Registration of Early Childhood Services Teachers | SG1 | 51 | 676 | +625 |
| Education (Surrender, Retention, and Search) Rules 2013 (SR  | SG1 | 45 | 668 | +623 |
| Education (School Risk Management Scheme) Regulations 2003 ( | SG1 | 43 | 648 | +605 |
| Education (School Trustee Elections) Regulations 2000 (SR 20 | SG1 | 34 | 627 | +593 |
| Lincoln University Act 1961 (1961 No 52) | SG1 | 95 | 582 | +487 |
| Education (Playgroups) Regulations 2008 (SR 2008/205) | SG1 | 26 | 509 | +483 |
| Massey University Act 1963 (1963 No 7) | SG1 | 91 | 574 | +483 |

Generic hubs (global top-5) and their seed-centred rank, upstream: Tax Administration Act 1994 -> 1; Income Tax Act 2007 -> 3; Legislation Act 2019 -> 2; Goods and Services Tax Act 1985 -> 6; Resource Management Act 1991 -> 25

## 3. Is it just the layers / direct links?

| Direction | Spearman(seed score, layer number) | Top-50 that are direct neighbours | Spearman(seed score, global Katz), non-neighbours |
|---|---|---|---|
| downstream | -0.584 | 32/50 | 0.575 |
| upstream | -0.684 | 41/50 | 0.939 |

Direct neighbours of the seed: 182 Acts rely on it directly; it directly relies on 219.

| Layer | Acts | Downstream top-50 | Upstream top-50 |
|---|---|---|---|
| SG1 | 37 | 12 | 23 |
| SG2 | 419 | 21 | 24 |
| SG3 | 845 | 5 | 2 |
| SG4 | 1126 | 11 | 1 |
| SG5 | 47 | 1 | 0 |

## 4. Sensitivity to alpha

| Variation | Direction | Spearman vs primary | Top-10 overlap |
|---|---|---|---|
| alpha = 0.1/lambda_max | downstream | 0.9606 | 7/10 |
| alpha = 0.1/lambda_max | upstream | 0.9888 | 7/10 |
| alpha = 0.5/lambda_max | downstream | 0.9867 | 7/10 |
| alpha = 0.5/lambda_max | upstream | 0.9959 | 8/10 |

## 5. Boilerplate effect (substantive_only vs full)

| Direction | Spearman vs full | Top-10 overlap | Legislation Act 2019 seed-rank (full -> substantive) | Legislation Act 2019 global rank (full -> substantive) |
|---|---|---|---|---|
| downstream | 0.9865 | 10/10 | 105 -> 104 | 3 -> 76 |
| upstream | 0.9489 | 9/10 | 2 -> 45 | 3 -> 76 |

Top-5 upstream, substantive only: Tax Administration Act 1994; Income Tax Act 2007; Crown Entities Act 2004; Government Superannuation Fund Act 1956; Goods and Services Tax Act 1985
Top-5 downstream, substantive only: Education and Training; Education and Training Amendment Act 2022; Education and Training Amendment Act 2024; Taxation; Education and Training

## 6. Merge-policy bracket: cleaned (dedupe) vs duplicates summed

| Direction | Spearman | Top-10 overlap |
|---|---|---|
| downstream | 0.9964 | 9/10 |
| upstream | 0.9989 | 9/10 |

Seed global rank: dedupe 19, summed 13.