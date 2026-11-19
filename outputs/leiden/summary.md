# Stage 8: Leiden community detection (frozen graph)

Frozen graph verified (SHA-256 of nodes/edges/collapsed files, all three corpora).

## 1. Settings

| Item | Value |
|---|---|
| Algorithm | Leiden (leidenalg 0.12.0), objective = modularity at resolution gamma = 1, iterated until stable |
| Nodes / layers | 2475 Acts, all five layers together (SG0 to SG5) |
| Weight | amendment operations + citation mentions (same as Katz); sensitivity log(1 + weight) |
| Seeds | 1 to 20 (20 runs per setting); reported partition = best run |
| Headline | substantive_only, directed modularity, weighted |

## 2. Results at gamma = 1

| Corpus | Direction | Weight | Communities | Modularity Q | Largest community (share) | Communities with fewer than 5 Acts | Singletons | Stability across 20 seeds (mean ARI, min ARI) |
|---|---|---|---|---|---|---|---|---|
| substantive_only **(headline)** | directed | weighted | 34 | 0.651 | 325 (13.1%) | 5 | 0 | 0.762, 0.628 |
| substantive_only | undirected | weighted | 32 | 0.650 | 320 (12.9%) | 6 | 0 | 0.719, 0.558 |
| no_artefact | directed | weighted | 34 | 0.640 | 321 (13.0%) | 6 | 0 | 0.721, 0.581 |
| no_artefact | undirected | weighted | 34 | 0.641 | 322 (13.0%) | 7 | 0 | 0.721, 0.544 |
| full | directed | weighted | 36 | 0.632 | 314 (12.7%) | 9 | 0 | 0.737, 0.589 |
| full | undirected | weighted | 35 | 0.631 | 297 (12.0%) | 6 | 0 | 0.716, 0.557 |
| substantive_only | directed | log_weighted | 13 | 0.437 | 387 (15.6%) | 0 | 0 | 0.662, 0.450 |
| substantive_only | undirected | log_weighted | 14 | 0.436 | 427 (17.3%) | 1 | 0 | 0.660, 0.450 |

## 3. How much do the answers depend on the choices? (agreement with the headline partition)

ARI = Adjusted Rand Index and NMI = Normalised Mutual Information; 1 means identical groupings, 0 means no better than chance.

| Setting compared with the headline | ARI | NMI |
|---|---|---|
| substantive_only, undirected, weighted | 0.819 | 0.881 |
| no_artefact, directed, weighted | 0.844 | 0.896 |
| no_artefact, undirected, weighted | 0.799 | 0.880 |
| full, directed, weighted | 0.817 | 0.885 |
| full, undirected, weighted | 0.742 | 0.849 |
| substantive_only, directed, log_weighted | 0.479 | 0.656 |
| substantive_only, undirected, log_weighted | 0.423 | 0.614 |

## 4. Resolution sweep (substantive_only, weighted, 5 seeds each; Q is always the standard modularity of the partition)

| Direction | gamma | Communities | Q | Largest share | NMI vs gamma = 1 | Acts in the seed's community |
|---|---|---|---|---|---|---|
| directed | 0.25 | 19 | 0.398 | 65.0% | 0.436 | 1609 |
| directed | 0.5 | 33 | 0.602 | 36.7% | 0.692 | 89 |
| directed | 0.75 | 30 | 0.647 | 16.7% | 0.774 | 88 |
| directed | 1.0 | 32 | 0.650 | 12.3% | 0.879 | 88 |
| directed | 1.5 | 42 | 0.641 | 7.2% | 0.775 | 44 |
| directed | 2.0 | 53 | 0.633 | 6.2% | 0.778 | 40 |
| directed | 3.0 | 69 | 0.616 | 5.3% | 0.744 | 34 |
| undirected | 0.25 | 18 | 0.406 | 64.6% | 0.459 | 1600 |
| undirected | 0.5 | 29 | 0.587 | 39.1% | 0.652 | 94 |
| undirected | 0.75 | 26 | 0.645 | 20.0% | 0.830 | 91 |
| undirected | 1.0 | 32 | 0.650 | 12.9% | 0.908 | 82 |
| undirected | 1.5 | 44 | 0.641 | 8.6% | 0.784 | 38 |
| undirected | 2.0 | 54 | 0.636 | 6.0% | 0.788 | 38 |
| undirected | 3.0 | 68 | 0.617 | 5.3% | 0.740 | 34 |

## 5. The Education and Training Act 2020's community in each setting

| Corpus | Direction | Acts in the seed's community | Share of seed's direct neighbours inside (rely on it / it relies on) | Same-members stability across seeds (mean Jaccard) |
|---|---|---|---|---|
| substantive_only | directed | 86 | 21% / 24% | 0.950 |
| substantive_only | undirected | 82 | 21% / 24% | 0.925 |
| no_artefact | directed | 88 | 21% / 24% | 0.913 |
| no_artefact | undirected | 88 | 21% / 24% | 0.631 |
| full | directed | 112 | 22% / 25% | 0.805 |
| full | undirected | 101 | 21% / 25% | 0.697 |

## 6. Headline communities (substantive_only, directed, gamma = 1): the 15 largest

| # | Acts | Layer mix (SG0/1/2/3/4/5) | Most connected Acts (by total weight) | Frequent title words (automatic draft, not a label) |
|---|---|---|---|---|
| 1 | 325 | 0/3/41/156/117/8 | Resource Management Act 1991; Conservation Act 1987; Reserves Act 1977; Land Transfer Act 2017; Fisheries Act 1996 | settlement, claims, management, resource |
| 2 | 278 | 0/1/44/111/121/1 | Criminal Procedure Act 2011; Search and Surveillance Act 2012; Summary Proceedings Act 1957; Customs and Excise Act 2018; Sentencing Act 2002 | nations, united, sanctions, criminal |
| 3 | 217 | 0/0/27/87/103/0 | District Court Act 2016; Oranga Tamariki Act 1989; Family Court Rules 2002; Senior Courts Act 2016; Children, Young Persons, and Their Famil | family, court, courts, children |
| 4 | 202 | 0/1/34/82/82/3 | Companies Act 1993; Financial Markets Conduct Act 2013; Financial Markets Conduct Regulations 20; Financial Markets Act 2013; Financial Markets Authority Act 2011 | financial, markets, securities, conduct |
| 5 | 191 | 0/2/49/75/63/2 | Crown Entities Act 2004; Public Service Act 2020; Public Finance Act 1989; Privacy Act 2020; Gambling Act 2003 | service, fire, public, commission |
| 6 | 168 | 0/1/22/39/96/10 | Local Government Act 2002; Local Government Act 1974; Local Government Act 2025; Commerce Act 1986; Building Act 2004 | local, government, building, drainage |
| 7 | 142 | 0/4/79/37/22/0 | Social Security Act 2018; Social Security Act 1964; Accident Compensation Act 2001; Employment Relations Act 2000; Public and Community Housing Management  | social, security, compensation, employment |
| 8 | 138 | 0/0/12/51/70/5 | Land Transport Act 1998; Maritime Transport Act 1994; Land Transport Management Amendment Act ; Land Transport Management Act 2003; Transport Act 1962 | transport, land, road, charges |
| 9 | 130 | 0/1/11/42/68/8 | Secondary Legislation Act 2021; Biosecurity Act 1993; Animal Products Act 1999; Telecommunications Act 2001; Legislation Act 2019 | medicines, animal, energy, biosecurity |
| 10 (seed) | 86 | 1/20/28/21/16/0 | Education and Training Act 2020; Education Act 1989; Education Amendment Act 1990; State Sector Act 1988; Education Amendment Act 2017 | education, training, children, university |
| 11 | 71 | 0/0/9/19/42/1 | Gas Act 1992; Health and Safety at Work Act 2015; Electricity Act 1992; Electricity Regulations 2010; WorkSafe New Zealand Act 2013 | safety, health, electricity, employment |
| 12 | 67 | 0/3/23/17/23/1 | Income Tax Act 2007; Tax Administration Act 1994; Income Tax Act 2004; Taxation Act 2009; KiwiSaver Act 2006 | taxation, savings, ownership, tax |
| 13 | 54 | 0/0/1/7/45/1 | Fisheries Regulations 2013; Fisheries Regulations 1986; Fisheries Regulations 1986; Fisheries Regulations 2001; Fisheries Amendment Act 2022 | fisheries, food, legislation, revocation |
| 14 | 51 | 0/0/2/12/35/2 | Climate Change Response Act 2002; Climate Change Response Amendment Act 20; Environmental Protection Authority Act 2; Climate Change Response Amendment Act 20; Climate Change Response Amendment Act 20 | change, climate, response, protection |
| 15 | 50 | 0/0/5/14/30/1 | Overseas Investment Act 2005; Overseas Investment Regulations 2005; European Union Free Trade Agreement Legi; Geographical Indications Registration Ac; Dairy Industry Restructuring Act 2001 | overseas, investment, trade, patents |

## 7. The seed's community in detail (headline setting): 86 Acts

| Layer | Acts in the community | Acts in the whole network | Share of that layer |
|---|---|---|---|
| SG0 | 1 | 1 | 100% |
| SG1 | 20 | 37 | 54% |
| SG2 | 28 | 419 | 7% |
| SG3 | 21 | 845 | 2% |
| SG4 | 16 | 1126 | 1% |
| SG5 | 0 | 47 | 0% |

The 20 best-connected members (total weight), with their Katz rank in the same (substantive-only) corpus at alpha = 0.9, where available:

| Act | Layer | Katz rank, substantive-only (of 2,475) |
|---|---|---|
| Education and Training Act 2020 | SG0 | 17 |
| Education Act 1989 (1989 No 80) | SG1 | 11 |
| Education Amendment Act 1990 | SG4 | 1066 |
| State Sector Act 1988 | SG2 | 127 |
| Education (Update) Amendment Act 2017 | SG3 | 647 |
| Education and Training (Vocational Education and Training System) Amen | SG2 | 1282 |
| Education and Training Amendment Act 2024 | SG2 | 1283 |
| Education (Vocational Education and Training Reform) Amendment Act 202 | SG4 | 1015 |
| Education and Training Amendment Act 2022 | SG2 | 1386 |
| Education Act 1964 | SG2 | 80 |
| Education and Training (System Reform) Amendment Act 2026 | SG2 | 1387 |
| Education Amendment Act 2015 | SG2 | 524 |
| Education Amendment Act 2011 | SG2 | 1083 |
| Children’s Act 2014 (2014 No 40) | SG1 | 369 |
| Education Amendment Act 2006 | SG2 | 885 |
| Private Schools Conditional Integration Act 1975 | SG3 | 189 |
| Industry Training and Apprenticeships Act 1992 | SG3 | 431 |
| Education (Early Childhood Services) Regulations 2008 (SR 2008/204) | SG1 | 352 |
| Education Legislation Act 2016 | SG4 | 1098 |
| Education Standards Act 2001 | SG3 | 841 |