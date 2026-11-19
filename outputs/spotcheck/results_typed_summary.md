# SLM spot-check on the final typed graph

Model: qwen2.5:7b-instruct; classified 150/150 sampled edges

## Headline

| Edge type | Agreement | Lenient agreement |
|---|---|---|
| amendment | 73/75 (97.3%, 95% CI 91-99%) | n/a |
| citation | 62/75 (82.7%, 95% CI 73-90%) | 67/75 (89.3%, 95% CI 80-94%) |
| **all** | 135/150 (90.0%, 95% CI 84-94%) | |

## By layer and edge type (strict)

| Layer | Amendment | Citation |
|---|---|---|
| SG1 | 14/15 | 12/15 |
| SG2 | 15/15 | 13/15 |
| SG3 | 15/15 | 14/15 |
| SG4 | 14/15 | 11/15 |
| SG5 | 15/15 | 12/15 |

## By evidence source (strict)

| Evidence | Agreement |
|---|---|
| amendment / history_note | 44/44 (100.0%, 95% CI 92-100%) |
| amendment / schedule_amendment | 29/31 (93.5%, 95% CI 79-98%) |
| citation / citation_context | 62/75 (82.7%, 95% CI 73-90%) |

## By SLM confidence (strict)

| Confidence | Agreement |
|---|---|
| high | 132/144 (91.7%, 95% CI 86-95%) |
| low | 3/6 (50.0%, 95% CI 19-81%) |

## What the SLM called the disagreements

| Rule-based | SLM type | Count |
|---|---|---|
| citation | definition_reference | 5 |
| citation | cross_reference | 4 |
| citation | amendment | 4 |
| amendment | definition_reference | 1 |
| amendment | citation | 1 |