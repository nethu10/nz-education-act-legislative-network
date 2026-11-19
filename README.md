# Mapping the Reach of the Education and Training Act 2020 - Small Language Model-Assisted Network Analysis of New Zealand Legislation

Code and frozen outputs for the Master of Applied Technology (Data Analytics and Intelligence) thesis by Nethmi Weerasingha, Unitec Institute of Technology, Auckland, New Zealand. Supervisor: Assoc. Prof. Iman Ardekani.

The study builds a directed, weighted network of New Zealand legislation around the **Education and Training Act 2020** (the "seed" Act) and asks how far changes to that Act reach. A local small language model (SLM) is used to read provisions and to check the extracted relations, but the graph itself is built from the official XML and deterministic rules. The frozen graph is then analysed with Katz centrality and Leiden community detection.

## Key numbers (frozen graph)

| Item | Value |
|---|---|
| Instruments (nodes) | 2,475 |
| Amendment edges / citation edges (multi-edges) | 14,805 / 24,183 |
| Weighted directed edges after collapsing | 30,515 |
| Layers | Seed, then SG1 to SG5 |
| SLM | Qwen2.5-7B-Instruct (`qwen2.5:7b-instruct`) served locally with Ollama, temperature 0, JSON output |
| Centrality | Katz on incoming walks, alpha = 0.9 / lambda_max |
| Communities | Leiden, directed modularity, gamma = 1, 20 fixed seeds (1 to 20) |

The graph is frozen on 2026-10-14. File hashes (SHA-256) for all three corpora are stored in `outputs/GRAPH_FROZEN.json`.

## Repository layout

```
src/        numbered pipeline scripts and checks (Python)
data/       raw XML and intermediate files (see "Data" below)
outputs/    graphs, Katz and Leiden results, spot-check results, GRAPH_FROZEN.json
reports/    figures used in the thesis
notebooks/  exploratory notebooks
```

## Requirements

- Python 3.13 (used for the thesis runs) and a virtual environment
- [Ollama](https://ollama.com) with the model pulled: `ollama pull qwen2.5:7b-instruct`
- Python packages: `requests`, `lxml`, `numpy`, `scipy`, `networkx`, `python-igraph`, `leidenalg`, `scikit-learn`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run every script from the repository root, for example `python src/stage1_acquisition.py`.

## Pipeline

Scripts are named by stage. Each reads the outputs of the stage before it. Diagnostic and exploratory scripts (`check_*`, `diagnose_*`, `explore_*`, `view_*`, `test_*`) are not needed to rebuild the graph.

| Stage | What it does | Main scripts |
|---|---|---|
| 1. Acquisition | Downloads the XML of the seed Act (version pinned to 2026-07-01) from legislation.govt.nz | `stage1_acquisition.py` |
| 2. Segmentation | Splits the XML into provisions and definitions; extracts incoming and outgoing amendment records | `stage2_segmentation.py` |
| 3. SLM extraction | Runs the SLM over each provision (resumable, raw responses stored) | `extraction_utils.py`, `stage3_extraction_sample.py`, `stage3_extraction_full.py` |
| 4. Validation | Structural cross-check against the XML tags (recall) and manual sample (precision) | `stage4_structural_crosscheck.py`, `stage4_manual_sample.py`, `analyze_precision.py` |
| 5 and 6. First graph and expansion | First graph and the two-ring expansion that was later replaced by layers | `stage5_*.py`, `stage6_*.py` |
| Layers SG1 to SG5 | Candidate selection with layer-specific cutoffs, identifier resolution against the register, internal links, typed edges | `sg1_step*.py`, `sg2_step*.py`, `sg3_*.py`, `sg4_step*.py`, `sg5_step01_build_typed_edges.py` |
| Audit and de-duplication | Collision audit, node merges, renames, placeholder removal | `audit_fix_01` to `audit_fix_12`, `body_amendment_gap_audit.py` |
| Graph assembly | Builds the typed multi-edge graph and the two variants (no publication artefacts; substantive citations only) | `assemble_typed_multiedge_graph.py`, `build_no_artefact_graph_variant.py`, `boilerplate_citation_audit.py` |
| Freeze | Writes or checks the SHA-256 manifest | `freeze_graph.py` (`--check` to verify) |
| Edge spot-check | Independent SLM check of a stratified sample of 150 edges | `slm_spotcheck_04_build_sample_typed.py`, `slm_spotcheck_05_classify_typed.py`, `slm_spotcheck_06_post_merge_integrity.py` |
| 7. Katz centrality | Katz on three corpora and several weight views, with alpha sensitivity | `stage7_katz_centrality.py`, `stage7b_seed_centred_katz.py`, `seed_katz_diagnostic.py` |
| 8. Communities | Leiden on the frozen graph, resolution sweep and stability | `stage8_leiden_communities.py` |
| 8b. Labels | SLM as a second reader for community names (titles only, three prompts per community) | `stage8b_semantic_labels.py` |

Corpora produced by assembly:

- `outputs/graph_typed/`: full graph
- `outputs/graph_typed_no_artefact/`: publication-artefact citations removed
- `outputs/graph_typed_substantive_only/`: artefact and drafting-template citations removed (headline corpus for Leiden)

### Reproducing the analysis from the frozen graph

If you only want the results, you do not need to rebuild the graph or run the SLM for the graph itself:

```bash
python src/freeze_graph.py --check          # confirms the graph files match the stored hashes
python src/stage7_katz_centrality.py        # Katz centrality (outputs/stage7_katz/)
python src/stage7b_seed_centred_katz.py     # seed-centred Katz
python src/stage8_leiden_communities.py     # Leiden communities (outputs/leiden/)
```

Katz and Leiden outputs matched exactly in a second computing environment. SLM outputs are the exception: temperature 0 does not guarantee identical output across hardware, so the stored raw responses (for example in `outputs/spotcheck/` and `outputs/leiden_labels/`) are the record for the SLM runs.

## Data

The legislation text comes from the New Zealand Parliamentary Counsel Office, https://legislation.govt.nz. The XML for the seed Act is downloaded by `stage1_acquisition.py` and the other instruments are fetched by the `sg*_step*` scripts. Please check the website's terms of use before redistributing any of the downloaded text. Set a descriptive `User-Agent` and keep the request rate low when re-running the downloads.

## How the SLM is used

The SLM reads provisions to extract candidate relations and acts as an independent second reader when checking the rule-based edges and the community names. It does **not** build the graph. Edges come from XML tags (`<history-note>`, `<intref>`, `<extref>`) and deterministic rules.

## Citation

If you use this code, please cite the thesis:

> N. Weerasingha, "Mapping the Reach of the Education and Training Act 2020 - Small Language Model-Assisted Network Analysis of New Zealand Legislation," Master's thesis, Unitec Institute of Technology, Auckland, New Zealand, 2026.

Archived version: DOI to be added after the Zenodo release.

## Licence

Code: MIT (see `LICENSE`). Derived data and figures: CC BY 4.0, subject to the terms of the source legislation website.

## Contact

Nethmi Weerasingha, Unitec Institute of Technology.
