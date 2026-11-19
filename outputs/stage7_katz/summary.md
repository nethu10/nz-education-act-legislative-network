# Stage 7: Katz centrality

Primary setting: alpha = 0.9 / lambda_max; incoming walks (cited/amended = important); scores scaled to max = 1.

## Spectral radius and alpha

| Corpus | View | lambda_max | alpha |
|---|---|---|---|
| full | weighted | 749.02 | 0.00120 |
| full | log_weighted | 73.83 | 0.01219 |
| full | binary | 50.26 | 0.01791 |
| full | amend_only | 8.50 | 0.10588 |
| full | cite_only | 53.17 | 0.01693 |
| no_artefact | weighted | 748.48 | 0.00120 |
| no_artefact | log_weighted | 72.64 | 0.01239 |
| no_artefact | binary | 49.81 | 0.01807 |
| no_artefact | amend_only | 8.50 | 0.10588 |
| no_artefact | cite_only | 52.82 | 0.01704 |
| substantive_only | weighted | 747.38 | 0.00120 |
| substantive_only | log_weighted | 69.67 | 0.01292 |
| substantive_only | binary | 48.28 | 0.01864 |
| substantive_only | amend_only | 8.50 | 0.10588 |
| substantive_only | cite_only | 52.12 | 0.01727 |

## Top 15 by Katz, full corpus, weighted view

| Rank | Node | Layer | Katz | In-strength rank | PageRank rank |
|---|---|---|---|---|---|
| 1 | Tax Administration Act 1994 (1994 No 166) | SG1 | 1.000 | 4 | 11 |
| 2 | Income Tax Act 2007 (2007 No 97) | SG1 | 0.792 | 1 | 7 |
| 3 | Legislation Act 2019 (2019 No 58) | SG1 | 0.386 | 2 | 1 |
| 4 | Goods and Services Tax Act 1985 | SG2 | 0.201 | 44 | 53 |
| 5 | Resource Management Act 1991 | SG2 | 0.159 | 3 | 2 |
| 6 | Local Government Act 1974 | SG2 | 0.152 | 5 | 4 |
| 7 | Accident Compensation Act 2001 | SG2 | 0.145 | 28 | 46 |
| 8 | KiwiSaver Act 2006 | SG2 | 0.123 | 39 | 108 |
| 9 | Companies Act 1993 | SG2 | 0.110 | 13 | 3 |
| 10 | Social Security Act 1964 | SG2 | 0.087 | 16 | 33 |
| 11 | Income Tax Act 2004 | SG2 | 0.086 | 29 | 118 |
| 12 | Education Act 1989 (1989 No 80) | SG1 | 0.081 | 9 | 50 |
| 13 | Local Government Act 2002 | SG2 | 0.078 | 15 | 13 |
| 14 | Climate Change Response Act 2002 | SG3 | 0.076 | 7 | 59 |
| 15 | Child Support Act 1991 | SG2 | 0.076 | 78 | 75 |

## Top 15 by Katz, no_artefact corpus, weighted view

| Rank | Node | Layer | Katz | In-strength rank | PageRank rank |
|---|---|---|---|---|---|
| 1 | Tax Administration Act 1994 (1994 No 166) | SG1 | 1.000 | 4 | 10 |
| 2 | Income Tax Act 2007 (2007 No 97) | SG1 | 0.791 | 1 | 6 |
| 3 | Legislation Act 2019 (2019 No 58) | SG1 | 0.321 | 3 | 1 |
| 4 | Goods and Services Tax Act 1985 | SG2 | 0.201 | 43 | 42 |
| 5 | Resource Management Act 1991 | SG2 | 0.158 | 2 | 2 |
| 6 | Local Government Act 1974 | SG2 | 0.152 | 5 | 5 |
| 7 | Accident Compensation Act 2001 | SG2 | 0.144 | 28 | 50 |
| 8 | KiwiSaver Act 2006 | SG2 | 0.123 | 38 | 103 |
| 9 | Companies Act 1993 | SG2 | 0.110 | 13 | 3 |
| 10 | Social Security Act 1964 | SG2 | 0.087 | 16 | 27 |
| 11 | Income Tax Act 2004 | SG2 | 0.086 | 29 | 115 |
| 12 | Education Act 1989 (1989 No 80) | SG1 | 0.081 | 9 | 45 |
| 13 | Local Government Act 2002 | SG2 | 0.077 | 15 | 13 |
| 14 | Child Support Act 1991 | SG2 | 0.076 | 77 | 70 |
| 15 | Climate Change Response Act 2002 | SG3 | 0.075 | 7 | 67 |

## Top 15 by Katz, substantive_only corpus, weighted view

| Rank | Node | Layer | Katz | In-strength rank | PageRank rank |
|---|---|---|---|---|---|
| 1 | Tax Administration Act 1994 (1994 No 166) | SG1 | 1.000 | 3 | 7 |
| 2 | Income Tax Act 2007 (2007 No 97) | SG1 | 0.790 | 1 | 4 |
| 3 | Goods and Services Tax Act 1985 | SG2 | 0.201 | 42 | 38 |
| 4 | Resource Management Act 1991 | SG2 | 0.156 | 2 | 2 |
| 5 | Local Government Act 1974 | SG2 | 0.149 | 4 | 5 |
| 6 | Accident Compensation Act 2001 | SG2 | 0.143 | 27 | 53 |
| 7 | KiwiSaver Act 2006 | SG2 | 0.123 | 37 | 96 |
| 8 | Companies Act 1993 | SG2 | 0.110 | 12 | 1 |
| 9 | Social Security Act 1964 | SG2 | 0.087 | 15 | 26 |
| 10 | Income Tax Act 2004 | SG2 | 0.086 | 28 | 105 |
| 11 | Education Act 1989 (1989 No 80) | SG1 | 0.081 | 8 | 50 |
| 12 | Child Support Act 1991 | SG2 | 0.075 | 76 | 71 |
| 13 | Local Government Act 2002 | SG2 | 0.075 | 14 | 11 |
| 14 | Climate Change Response Act 2002 | SG3 | 0.074 | 6 | 76 |
| 15 | Crown Entities Act 2004 (2004 No 115) | SG1 | 0.073 | 17 | 6 |

## Effect of removing boilerplate citations (weighted view)

| Corpus | Spearman vs full | Top-10 overlap vs full | Legislation Act 2019 rank (Katz score) | Legislation Act 2012 rank |
|---|---|---|---|---|
| full | 1.0000 | 10/10 | 3 (0.386) | 45 |
| no_artefact | 0.9742 | 10/10 | 3 (0.321) | 113 |
| substantive_only | 0.9676 | 9/10 | 76 (0.031) | 201 |

Largest rank changes among nodes in the top 100 of either corpus (full vs no_artefact; tied scores share a rank):

| Node | Rank (full) | Rank (no artefact) | Change |
|---|---|---|---|
| Legislation Act 2012 | 45 | 113 | -68 |
| Armed Forces Discipline Act 1971 | 48 | 54 | -6 |
| Contract and Commercial Law Act 2017 | 93 | 96 | -3 |
| Land Act 1948 | 32 | 35 | -3 |
| Anti-Money Laundering and Countering Financing of Terroris | 65 | 62 | +3 |
| Financial Markets Conduct Regulations 2014 | 92 | 89 | +3 |
| Fire Service Act 1975 | 96 | 93 | +3 |
| Banking (Prudential Supervision) Act 1989 | 51 | 49 | +2 |
| Charities Act 2005 | 52 | 50 | +2 |
| Civil Aviation Act 1990 | 70 | 68 | +2 |

## Sensitivity: alpha fraction (full corpus, weighted)

Primary = 0.9. 'Indirect share' = share of the total score that comes from walks of length 2 or more (the part Katz adds beyond counting direct citations).

| alpha = f/lambda_max | Spearman vs in-strength | Spearman vs primary | Top-10 overlap with primary | Top-50 overlap with primary | Seed rank | Indirect share |
|---|---|---|---|---|---|---|
| 0.1 | 0.993 | 0.977 | 5/10 | 41/50 | 13 | 0.1% |
| 0.3 | 0.989 | 0.986 | 6/10 | 41/50 | 15 | 0.6% |
| 0.5 | 0.984 | 0.992 | 6/10 | 42/50 | 15 | 2.0% |
| 0.7 | 0.976 | 0.997 | 8/10 | 43/50 | 19 | 5.1% |
| 0.9 (primary) | 0.961 | 1.000 | 10/10 | 50/50 | 19 | 15.5% |
| 0.99 | 0.916 | 0.986 | 7/10 | 37/50 | 19 | 63.2% |

## Sensitivity: view (Spearman vs primary)

| Variation | Spearman vs primary | Top-10 overlap |
|---|---|---|
| view = log_weighted | 0.9632 | 3/10 |
| view = binary | 0.9270 | 3/10 |
| view = amend_only | 0.8285 | 1/10 |
| view = cite_only | 0.8820 | 3/10 |

## Katz vs simpler measures (full, weighted)

| Spearman(Katz, in-strength) | 0.9607 |
|---|---|
| Spearman(Katz, PageRank) | 0.8929 |

## Where the top-50 sit, by layer (full, weighted)

| Layer | Nodes in layer | In top 50 |
|---|---|---|
| SG0 | 1 | 1 |
| SG1 | 37 | 12 |
| SG2 | 419 | 33 |
| SG3 | 845 | 3 |
| SG4 | 1126 | 1 |
| SG5 | 47 | 0 |

Seed (Education and Training Act 2020): Katz rank 19 of 2475 (full, weighted).