"""
stage7_katz_centrality.py  --  Stage 7: Katz centrality on the typed legislative network.

Corpora (both run, both reported):
  full          outputs/graph_typed/              (all citations)
  no_artefact   outputs/graph_typed_no_artefact/  (PCO publication-artefact citations removed; see boilerplate audit)
  substantive_only outputs/graph_typed_substantive_only/ (artefact AND drafting-template citations removed)
Views of each corpus (directed; an edge u->v means u amends / cites v, so a node is important when it is
amended / cited by important nodes -- Katz is computed on INCOMING walks):
  weighted      collapsed edge weight = total_weight (amendment operations + citation count)   [primary]
  log_weighted  log(1 + total_weight)                                                           [tames heavy tails]
  binary        1 per connected ordered pair                                                    [topology only]
  amend_only    log(1 + amendment weight), amendment edges only
  cite_only     log(1 + citation weight),  citation edges only
Katz:  x = (I - alpha * A^T)^-1 * 1   with alpha = f / lambda_max(A);  primary f = 0.9 (chosen on the alpha-sensitivity evidence in the summary:
  the highest setting that keeps rankings stable while adding real indirect-walk information); sensitivity f in {0.1, 0.5, 0.9, 0.99}.
x is scaled so that its maximum is 1. Baselines reported alongside: weighted in-strength and PageRank.

Run from repo root:  python src/stage7_katz_centrality.py
Outputs: outputs/stage7_katz/<corpus>__<view>.csv, outputs/stage7_katz/summary.md, summary.json
"""
import csv, json
from collections import defaultdict
from pathlib import Path
import numpy as np
import networkx as nx
import scipy.sparse as sp
from scipy.sparse.linalg import eigs, spsolve
from scipy.stats import spearmanr, rankdata

OUT = Path("outputs/stage7_katz"); OUT.mkdir(parents=True, exist_ok=True)
CORPORA = {"full": Path("outputs/graph_typed"), "no_artefact": Path("outputs/graph_typed_no_artefact"),
           "substantive_only": Path("outputs/graph_typed_substantive_only")}
F_MAIN, F_SENS = 0.9, (0.1, 0.3, 0.5, 0.7, 0.9, 0.99)


def load(d):
    nodes = json.loads((d / "nodes.json").read_text(encoding="utf-8"))
    edges = json.loads((d / "edges.json").read_text(encoding="utf-8"))
    return nodes, edges


def build(nodes, edges, view):
    idx = {n["id"]: i for i, n in enumerate(nodes)}
    w = defaultdict(float)
    for e in edges:
        k = (idx[e["source"]], idx[e["target"]])
        if view == "amend_only" and e["edge_type"] != "amendment": continue
        if view == "cite_only" and e["edge_type"] != "citation": continue
        w[k] += e["weight"]
    rows, cols, vals = [], [], []
    for (i, j), x in w.items():
        v = {"weighted": x, "log_weighted": np.log1p(x), "binary": 1.0, "amend_only": np.log1p(x), "cite_only": np.log1p(x)}[view]
        rows.append(i); cols.append(j); vals.append(v)
    n = len(nodes)
    return sp.csr_matrix((vals, (rows, cols)), shape=(n, n)), idx


def katz(A, f):
    lam = float(np.real(eigs(A, k=1, which="LR", return_eigenvectors=False, maxiter=5000)[0]))
    alpha = f / lam
    n = A.shape[0]
    x = spsolve(sp.identity(n, format="csc") - alpha * A.T.tocsc(), np.ones(n))
    return x / x.max(), lam, alpha


def ranks(x): return rankdata(-np.round(x, 9), method="min").astype(int)   # tied scores share a rank


def main():
    res, L = {}, []
    def line(s=""): L.append(s); print(s)
    views = ["weighted", "log_weighted", "binary", "amend_only", "cite_only"]
    store = {}
    for cname, d in CORPORA.items():
        nodes, edges = load(d)
        for view in views:
            A, idx = build(nodes, edges, view)
            x, lam, alpha = katz(A, F_MAIN)
            G = nx.from_scipy_sparse_array(A, create_using=nx.DiGraph)
            prd = nx.pagerank(G, weight="weight"); pr = np.array([prd[i] for i in range(len(nodes))])
            instr = np.asarray(A.sum(axis=0)).ravel()
            store[(cname, view)] = {"x": x, "lam": lam, "alpha": alpha, "pr": pr, "instr": instr, "nodes": nodes, "A": A}
            with open(OUT / f"{cname}__{view}.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh); w.writerow(["rank", "node", "layer", "katz", "in_strength", "pagerank"])
                for r, i in enumerate(np.argsort(-x), 1):
                    w.writerow([r, nodes[i]["id"], nodes[i]["layer"], f"{x[i]:.6f}", f"{instr[i]:.4f}", f"{pr[i]:.6f}"])

    line("# Stage 7: Katz centrality\n")
    line(f"Primary setting: alpha = {F_MAIN} / lambda_max; incoming walks (cited/amended = important); scores scaled to max = 1.\n")
    line("## Spectral radius and alpha\n"); line("| Corpus | View | lambda_max | alpha |"); line("|---|---|---|---|")
    for (c, v), s in store.items(): line(f"| {c} | {v} | {s['lam']:.2f} | {s['alpha']:.5f} |")

    for c in CORPORA:
        s = store[(c, "weighted")]; nodes = s["nodes"]
        line(f"\n## Top 15 by Katz, {c} corpus, weighted view\n")
        line("| Rank | Node | Layer | Katz | In-strength rank | PageRank rank |"); line("|---|---|---|---|---|---|")
        rk_in, rk_pr = ranks(s["instr"]), ranks(s["pr"])
        for r, i in enumerate(np.argsort(-s["x"])[:15], 1):
            line(f"| {r} | {nodes[i]['id'][:58]} | {nodes[i]['layer']} | {s['x'][i]:.3f} | {rk_in[i]} | {rk_pr[i]} |")

    line("\n## Effect of removing boilerplate citations (weighted view)\n")
    a = store[("full", "weighted")]; nodes = a["nodes"]; ra = ranks(a["x"])
    line("| Corpus | Spearman vs full | Top-10 overlap vs full | Legislation Act 2019 rank (Katz score) | Legislation Act 2012 rank |"); line("|---|---|---|---|---|")
    la = [i for i, n in enumerate(nodes) if n["id"].startswith("Legislation Act 2019")][0]
    l12 = [i for i, n in enumerate(nodes) if n["id"].startswith("Legislation Act 2012")][0]
    for c in CORPORA:
        b = store[(c, "weighted")]; rb = ranks(b["x"])
        line(f"| {c} | {spearmanr(a['x'], b['x']).correlation:.4f} | {len(set(np.argsort(-a['x'])[:10]) & set(np.argsort(-b['x'])[:10]))}/10 | {rb[la]} ({b['x'][la]:.3f}) | {rb[l12]} |")
    line("\nLargest rank changes among nodes in the top 100 of either corpus (full vs no_artefact; tied scores share a rank):\n")
    b = store[("no_artefact", "weighted")]; rb = ranks(b["x"])
    cand = [i for i in range(len(nodes)) if ra[i] <= 100 or rb[i] <= 100]
    line("| Node | Rank (full) | Rank (no artefact) | Change |"); line("|---|---|---|---|")
    for i in sorted(cand, key=lambda i: -abs(ra[i] - rb[i]))[:10]:
        line(f"| {nodes[i]['id'][:58]} | {ra[i]} | {rb[i]} | {ra[i]-rb[i]:+d} |")
    line("\n## Sensitivity: alpha fraction (full corpus, weighted)\n")
    base = store[("full", "weighted")]; A0 = base["A"]; n0 = A0.shape[0]; sA = A0.sum()
    seed0 = [i for i, n in enumerate(nodes) if n["layer"] == "SG0"][0]
    line(f"Primary = {F_MAIN}. 'Indirect share' = share of the total score that comes from walks of length 2 or more (the part Katz adds beyond counting direct citations).\n")
    line("| alpha = f/lambda_max | Spearman vs in-strength | Spearman vs primary | Top-10 overlap with primary | Top-50 overlap with primary | Seed rank | Indirect share |"); line("|---|---|---|---|---|---|---|")
    top = lambda x, k=10: set(np.argsort(-x)[:k])
    for f in F_SENS:
        x2, lam2, a2 = katz(A0, f)
        raw = spsolve(sp.identity(n0, format="csc") - a2 * A0.T.tocsc(), np.ones(n0)); share = 1 - (n0 + a2 * sA) / raw.sum()
        tag = " (primary)" if f == F_MAIN else ""
        line(f"| {f}{tag} | {spearmanr(x2, base['instr']).correlation:.3f} | {spearmanr(base['x'], x2).correlation:.3f} | {len(top(base['x']) & top(x2))}/10 | {len(top(base['x'], 50) & top(x2, 50))}/50 | {ranks(x2)[seed0]} | {100*share:.1f}% |")
    line("\n## Sensitivity: view (Spearman vs primary)\n")
    line("| Variation | Spearman vs primary | Top-10 overlap |"); line("|---|---|---|")
    for v in views[1:]:
        s = store[("full", v)]
        line(f"| view = {v} | {spearmanr(base['x'], s['x']).correlation:.4f} | {len(top(base['x']) & top(s['x']))}/10 |")
    line("\n## Katz vs simpler measures (full, weighted)\n")
    line(f"| Spearman(Katz, in-strength) | {spearmanr(base['x'], base['instr']).correlation:.4f} |\n|---|---|\n| Spearman(Katz, PageRank) | {spearmanr(base['x'], base['pr']).correlation:.4f} |")

    line("\n## Where the top-50 sit, by layer (full, weighted)\n")
    line("| Layer | Nodes in layer | In top 50 |"); line("|---|---|---|")
    t50 = np.argsort(-base["x"])[:50]
    for lyr in ("SG0", "SG1", "SG2", "SG3", "SG4", "SG5"):
        n_l = sum(1 for n in nodes if n["layer"] == lyr); k = sum(1 for i in t50 if nodes[i]["layer"] == lyr)
        line(f"| {lyr} | {n_l} | {k} |")
    seed = [i for i, n in enumerate(nodes) if n["layer"] == "SG0"][0]
    line(f"\nSeed (Education and Training Act 2020): Katz rank {ranks(base['x'])[seed]} of {len(nodes)} (full, weighted).")
    (OUT / "summary.md").write_text("\n".join(L), encoding="utf-8")
    print("\nSaved -> outputs/stage7_katz/")

if __name__ == "__main__":
    main()
