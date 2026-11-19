# Stage 8b: semantic labels for the 34 Leiden communities (SLM: qwen2.5:7b-instruct)

- Same broad domain in all 3 prompts: **31 of 34** groups
- SLM domain matches the draft domain: **26 of 34** groups
- Flagged for researcher review: **11 of 34**

| # | Acts | SLM label | SLM domain | Prompts agreeing | Draft label | Match | Review reason |
|---|---|---|---|---|---|---|---|
| 1 | 325 | Environment and natural resources | Environment and natural resources | 2/3 | Land, environment, conservation and fisheries | yes | domain differs between prompts |
| 2 | 278 | Justice and policing | Justice and policing | 3/3 | Criminal justice, policing and border control | yes |  |
| 3 | 217 | Justice and policing | Justice and policing | 3/3 | Family, children and the courts | yes |  |
| 4 | 202 | Business and finance | Business and finance | 3/3 | Company and financial-markets law | yes |  |
| 5 | 191 | Public administration and governance | Public administration and governance | 3/3 | Public sector, public finance, privacy and of | yes |  |
| 6 | 168 | Public administration and governance | Public administration and governance | 3/3 | Local government, building and water services | yes |  |
| 7 | 142 | Social policy and welfare | Social policy and welfare | 3/3 | Social support, ACC, employment, housing and  | yes |  |
| 8 | 138 | Transport and infrastructure | Transport and infrastructure | 3/3 | Land and maritime transport | yes |  |
| 9 | 130 | Health and safety | Health and safety | 3/3 | Biosecurity, food, telecommunications and haz | NO | differs from draft domain |
| 10 | 86 | Education | Education | 3/3 | Education and training | yes |  |
| 11 | 71 | Health and safety | Health and safety | 2/3 | Workplace safety, gas and electricity | yes | domain differs between prompts |
| 12 | 67 | Tax and revenue | Tax and revenue | 3/3 | Tax and KiwiSaver | yes |  |
| 13 | 54 | Environment and natural resources | Environment and natural resources | 3/3 | Fisheries regulations | yes |  |
| 14 | 51 | Climate change and environment | Environment and natural resources | 3/3 | Climate change | yes |  |
| 15 | 50 | International and trade | International and trade | 3/3 | Overseas investment, trade and intellectual p | yes |  |
| 16 | 46 | Maori affairs | Maori affairs | 2/3 | Maori land and affairs | yes | domain differs between prompts |
| 17 | 44 | Social policy and welfare | Social policy and welfare | 3/3 | Government superannuation (mixed with older A | NO | differs from draft domain |
| 18 | 41 | Defence and security | Defence and security | 3/3 | Defence, military justice, coroners and buria | yes |  |
| 19 | 39 | Business and finance | Business and finance | 3/3 | Professional regulation (lawyers, real estate | yes |  |
| 20 | 37 | Electoral and jury systems | Public administration and governance | 3/3 | Elections and juries | yes |  |
| 21 | 19 | Defence and security | Defence and security | 3/3 | Firearms | NO | differs from draft domain |
| 22 | 13 | Cook Islands governance | Public administration and governance | 3/3 | Cook Islands | NO | differs from draft domain |
| 23 | 10 | Communications and technology | Communications and technology | 3/3 | Radiocommunications and signals intelligence | yes |  |
| 24 | 9 | Health and safety | Health and safety | 3/3 | Smokefree and regulated products | yes |  |
| 25 | 9 | Weights and measures regulation | Other or mixed | 3/3 | Weights and measures | NO | SLM says mixed or low confidence; differs from draft domain |
| 26 | 8 | Social policy and welfare | Social policy and welfare | 3/3 | War pensions | yes |  |
| 27 | 6 | Criminal justice and policing | Justice and policing | 3/3 | Anti-money laundering | NO | differs from draft domain |
| 28 | 6 | Energy efficiency | Environment and natural resources | 3/3 | Energy efficiency | yes |  |
| 29 | 5 | Justice and policing | Justice and policing | 3/3 | Court of Appeal rules | yes |  |
| 30 | 4 | Child protection | Social policy and welfare | 3/3 | Child protection | yes |  |
| 31 | 3 | Public administration and governance | Public administration and governance | 3/3 | Patriotic and canteen funds | NO | differs from draft domain |
| 32 | 2 | Public administration and governance | Public administration and governance | 3/3 | Gas governance | NO | differs from draft domain |
| 33 | 2 | Public administration and governance | Public administration and governance | 3/3 | Greater Christchurch regeneration | yes |  |
| 34 | 2 | Māori affairs | Maori affairs | 3/3 | Maori Purposes Acts | yes |  |

## SLM descriptions (plain English)

- **1 Environment and natural resources** (325 Acts): Laws governing land use, conservation, fisheries, and resource management.
- **2 Justice and policing** (278 Acts): Laws related to criminal justice, law enforcement, and border control.
- **3 Justice and policing** (217 Acts): Laws related to family courts, district courts, and child protection.
- **4 Business and finance** (202 Acts): Regulates financial markets, companies, and related services.
- **5 Public administration and governance** (191 Acts): Laws governing public entities and services.
- **6 Public administration and governance** (168 Acts): Laws governing local government operations and infrastructure.
- **7 Social policy and welfare** (142 Acts): Laws related to social security, employment, housing, and health services.
- **8 Transport and infrastructure** (138 Acts): Regulates land, maritime, and rail transport systems.
- **9 Health and safety** (130 Acts): Laws regulating food safety, animal welfare, and biosecurity.
- **10 Education** (86 Acts): Laws governing education and training systems.
- **11 Health and safety** (71 Acts): Regulations for workplace and public safety.
- **12 Tax and revenue** (67 Acts): Laws related to taxation and income management.
- **13 Environment and natural resources** (54 Acts): These laws regulate fishing activities and related food safety.
- **14 Climate change and environment** (51 Acts): Laws related to climate change response and environmental protection.
- **15 International and trade** (50 Acts): Laws related to international trade agreements and foreign investment.
- **16 Maori affairs** (46 Acts): Laws related to Māori land and community development.
- **17 Social policy and welfare** (44 Acts): These laws regulate the Government Superannuation Fund for public servants.
- **18 Defence and security** (41 Acts): Laws related to military discipline, court martial procedures, and defense regulations.
- **19 Business and finance** (39 Acts): Regulates professionals and businesses involved in real estate, legal services, and construction.
- **20 Electoral and jury systems** (37 Acts): Laws governing elections, referenda, juries, and public health responses.
- **21 Defence and security** (19 Acts): Regulates arms and firearms in New Zealand.
- **22 Cook Islands governance** (13 Acts): These acts amend provisions related to the Cook Islands.
- **23 Communications and technology** (10 Acts): Regulates radio communications and related security measures.
- **24 Health and safety** (9 Acts): Laws regulating smoke-free environments and products.
- **25 Weights and measures regulation** (9 Acts): Laws and regulations governing weights and measures standards.
- **26 Social policy and welfare** (8 Acts): These laws provide regulations for war pensions.
- **27 Criminal justice and policing** (6 Acts): These laws aim to prevent money laundering and terrorism financing.
- **28 Energy efficiency** (6 Acts): Regulations governing energy efficiency standards and practices.
- **29 Justice and policing** (5 Acts): These laws amend rules for the Court of Appeal.
- **30 Child protection** (4 Acts): Laws related to protecting children from harm and abuse.
- **31 Public administration and governance** (3 Acts): Amendments to canteen funds management.
- **32 Public administration and governance** (2 Acts): Regulations governing the management of gas resources.
- **33 Public administration and governance** (2 Acts): These acts relate to the regeneration of Christchurch after natural disasters.
- **34 Māori affairs** (2 Acts): These acts relate to Māori purposes and interests.