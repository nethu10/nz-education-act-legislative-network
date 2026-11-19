"""
seed_katz_diagnostic.py -- READ-ONLY diagnostic. Writes only to outputs/seed_katz/.

1. Duplicate-node impact: five nodes duplicate a real Act (3 "Schedule N of the X" structural references that resolve to the parent Act's own XML,
   2 former-title duplicates sharing year/number with the current Act). The base graph is NOT modified; the diagnostic builds in-memory variants:
     base            as published (2,481 nodes)
     merged_dedupe   alias nodes redirected to the canonical Act. Amendment edges and all edges OUT of a merged node take the MAX of the
                     duplicates (same history note / same XML text); citation edges INTO a merged node are SUMMED (different mentions).
     merged_sum      alias edges simply added (upper bracket).
2. Global Katz (incoming walks, alpha = f/lambda_max, weighted collapsed graph), as in Stage 7.
3. Seed-centred Katz index, both directions, same alpha:
     downstream  y = (I - alpha A)^-1 e_seed   : Acts that RELY ON the seed (walks j -> ... -> seed; edge u->v means u amends/cites v)
     upstream    z = (I - alpha A^T)^-1 e_seed : Acts the seed RELIES ON (walks seed -> ... -> j)
4. Specificity (seed-centred rank vs global rank) and layer/direct-link checks.
Run from repo root:  python src/seed_katz_diagnostic.py
"""
import csv, json
from collections import defaultdict
from pathlib import Path
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigs, spsolve
from scipy.stats import spearmanr, rankdata

OUT = Path("outputs/seed_katz"); OUT.mkdir(parents=True, exist_ok=True)
CORPORA = {"full": Path("outputs/graph_typed"), "substantive_only": Path("outputs/graph_typed_substantive_only")}
SEED = "Education and Training Act 2020"
ALIAS = {
    "Schedule 9 of the Education and Training Act 2020": SEED,
    "Schedule 1 of the Social Security Act 2018": "Social Security Act 2018 (2018 No 32)",
    "Schedule 5 of the Crown Entities Act 2004": "Crown Entities Act 2004 (2004 No 115)",
    "Health Reforms (Transitional Provisions) Act 1993": "Health Sector (Transfers) Act 1993",
    "Securities Trustees and Statutory Supervisors Act 2011": "Financial Markets Supervisors Act 2011",
}
LAYER_NUM = {"SG0": 0, "SG1": 1, "SG2": 2, "SG3": 3, "SG4": 4, "SG5": 5}
F_MAIN = 0.5


def load(d):
    return (json.loads((d / "nodes.json").read_text(encoding="utf-8")), json.loads((d / "edges.json").read_text(encoding="utf-8")))


def collapsed(nodes, edges, policy):
    """Return (kept nodes, dict (s,t)->weight, stats). policy: base | dedupe | sum"""
    alias = ALIAS if policy != "base" else {}
    canon = set(alias.values())
    kept = [n for n in nodes if n["id"] not in alias]
    grp, loops = defaultdict(list), 0
    for e in edges:
        s, t = e["source"], e["target"]; s2, t2 = alias.get(s, s), alias.get(t, t)
        if s2 == t2:
            if s != t: loops += 1
            continue
        grp[(s2, t2, e["edge_type"])].append(e["weight"])
    w = defaultdict(float)
    for (s, t, et), ws in grp.items():
        if policy == "dedupe" and (et == "amendment" or s in canon): v = max(ws)   # same history note / same XML text
        else: v = sum(ws)                                                           # incoming citations: different mentions
        w[(s, t)] += v
    return kept, w, {"self_loops_dropped": loops}


def matrix(kept, w):
    idx = {n["id"]: i for i, n in enumerate(kept)}
    r, c, v = zip(*[(idx[s], idx[t], x) for (s, t), x in w.items()])
    n = len(kept)
    return sp.csr_matrix((v, (r, c)), shape=(n, n)), idx


def lam(A): return float(np.real(eigs(A, k=1, which="LR", return_eigenvectors=False, maxiter=5000)[0]))


def solve(M, b): return spsolve(M.tocsc(), b)


def global_katz(A, f=F_MAIN):
    n = A.shape[0]; a = f / lam(A)
    x = solve(sp.identity(n, format="csc") - a * A.T, np.ones(n)); return x / x.max(), a


def seed_katz(A, s, f=F_MAIN):
    n = A.shape[0]; a = f / lam(A); e = np.zeros(n); e[s] = 1
    down = solve(sp.identity(n, format="csc") - a * A, e)      # j -> ... -> seed  (j relies on seed)
    up = solve(sp.identity(n, format="csc") - a * A.T, e)      # seed -> ... -> j  (seed relies on j)
    for v in (down, up): v[s] = 0
    return down / down.max(), up / up.max()


def ranks(x): return rankdata(-np.round(x, 12), method="min").astype(int)


def main():
    L = []
    def line(s=""): L.append(s); print(s)
    line("# Seed-centred Katz diagnostic (read-only; base graph untouched)\n")
    res = {}
    for cname, d in CORPORA.items():
        nodes, edges = load(d)
        for pol in (["base", "dedupe", "sum"] if cname == "full" else ["base", "dedupe"]):
            kept, w, st = collapsed(nodes, edges, pol)
            A, idx = matrix(kept, w); s = idx[SEED]
            xg, a = global_katz(A); dn, up = seed_katz(A, s)
            res[(cname, pol)] = dict(kept=kept, A=A, idx=idx, s=s, xg=xg, dn=dn, up=up, alpha=a, stats=st, w=w)

    line("## 1. Impact of the five duplicate nodes on the global ranking (full corpus, weighted, alpha = 0.5/lambda_max)\n")
    line("| Graph | Nodes | Seed Katz rank | Top-5 global |"); line("|---|---|---|---|")
    for pol in ("base", "dedupe", "sum"):
        r = res[("full", pol)]; rk = ranks(r["xg"]); top5 = [r["kept"][i]["id"].split(" (")[0] for i in np.argsort(-r["xg"])[:5]]
        line(f"| {pol} | {len(r['kept'])} | {rk[r['s']]} of {len(r['kept'])} | {'; '.join(top5)} |")
    b, m = res[("full", "base")], res[("full", "dedupe")]
    common = [n["id"] for n in m["kept"]]; xb = np.array([b["xg"][b["idx"][k]] for k in common]); xm = np.array([m["xg"][m["idx"][k]] for k in common])
    line(f"\nSpearman(base, merged_dedupe) over {len(common)} common nodes: {spearmanr(xb, xm).correlation:.4f}")
    rb, rm = ranks(xb), ranks(xm)
    line("\n| Merged Act | Rank base | Rank merged (dedupe) | Katz base | Katz merged |"); line("|---|---|---|---|---|")
    for k in sorted(set(ALIAS.values())):
        i = common.index(k); line(f"| {k.split(' (')[0]} | {rb[i]} | {rm[i]} | {xb[i]:.3f} | {xm[i]:.3f} |")
    line(f"\nSelf-loops dropped when redirecting alias nodes: {m['stats']['self_loops_dropped']}")
    sb = b["idx"][SEED]; line(f"Seed direct edges base: in {int(b['A'][:, sb].nnz)} / out {int(b['A'][sb, :].nnz)}; merged: in {int(m['A'][:, m['s']].nnz)} / out {int(m['A'][m['s'], :].nnz)}")

    def table(r, key, title, n=15):
        k = r["kept"]; sc = r[key]; rg, rs = ranks(r["xg"]), ranks(sc)
        line(f"\n{title}\n"); line("| Seed-rank | Act | Layer | Seed-centred | Global rank | Lift (global rank - seed rank) |"); line("|---|---|---|---|---|---|")
        for i in np.argsort(-sc)[:n]: line(f"| {rs[i]} | {k[i]['id'][:60]} | {k[i]['layer']} | {sc[i]:.3f} | {rg[i]} | {rg[i]-rs[i]:+d} |")

    for pol in ("dedupe",):
        r = res[("full", pol)]
        line(f"\n## 2. Seed-centred Katz, full corpus, merged_dedupe graph (alpha = 0.5/lambda_max = {r['alpha']:.5f})")
        table(r, "dn", "### 2a. DOWNSTREAM: Acts that rely on the Education and Training Act 2020 (would need review if it changed)")
        table(r, "up", "### 2b. UPSTREAM: Acts the Education and Training Act 2020 relies on")
        k = r["kept"]; rg = ranks(r["xg"])
        for key, nm in (("dn", "downstream"), ("up", "upstream")):
            sc = r[key]; rs = ranks(sc); cand = [i for i in range(len(k)) if rs[i] <= 100 and i != r["s"]]
            line(f"\n### 2c. Most SEED-SPECIFIC {nm} (top-100 seed-centred, sorted by lift over global rank)\n")
            line("| Act | Layer | Seed-rank | Global rank | Lift |"); line("|---|---|---|---|---|")
            for i in sorted(cand, key=lambda i: -(rg[i] - rs[i]))[:10]: line(f"| {k[i]['id'][:60]} | {k[i]['layer']} | {rs[i]} | {rg[i]} | {rg[i]-rs[i]:+d} |")
            line("\nGeneric hubs (global top-5) and their seed-centred rank, " + nm + ": " + "; ".join(f"{k[i]['id'].split(' (')[0]} -> {rs[i]}" for i in np.argsort(-r['xg'])[:5]))

    line("\n## 3. Is it just the layers / direct links? (merged_dedupe, full)\n")
    r = res[("full", "dedupe")]; k = r["kept"]; s = r["s"]; A = r["A"]
    lay = np.array([LAYER_NUM[n["layer"]] for n in k]); others = np.array([i != s for i in range(len(k))])
    direct_in = np.asarray(A[:, s].todense()).ravel() > 0; direct_out = np.asarray(A[s, :].todense()).ravel() > 0
    line("| Direction | Spearman(seed score, layer number) | Top-50 that are direct neighbours | Spearman(seed score, global Katz) on non-neighbours |"); line("|---|---|---|---|")
    for key, nm, nb in (("dn", "downstream", direct_in), ("up", "upstream", direct_out)):
        sc = r[key]; t50 = np.argsort(-sc)[:50]
        mask = others & ~nb
        line(f"| {nm} | {spearmanr(sc[others], lay[others]).correlation:.3f} | {int(nb[t50].sum())}/50 | {spearmanr(sc[mask], r['xg'][mask]).correlation:.3f} |")
    line(f"\nDirect neighbours of the seed: {int(direct_in.sum())} Acts rely on it directly; it directly relies on {int(direct_out.sum())}.")
    line("\nShare of the top-50 by layer:\n"); line("| Layer | Acts | Downstream top-50 | Upstream top-50 |"); line("|---|---|---|---|")
    td, tu = np.argsort(-r["dn"])[:50], np.argsort(-r["up"])[:50]
    for ly in ("SG1", "SG2", "SG3", "SG4", "SG5"):
        n_l = sum(1 for n in k if n["layer"] == ly); line(f"| {ly} | {n_l} | {sum(1 for i in td if k[i]['layer']==ly)} | {sum(1 for i in tu if k[i]['layer']==ly)} |")

    line("\n## 4. Sensitivity of the seed-centred scores (merged_dedupe, full)\n")
    line("| Variation | Direction | Spearman vs primary | Top-10 overlap |"); line("|---|---|---|---|")
    for f in (0.1, 0.9):
        dn2, up2 = seed_katz(r["A"], s, f)
        for key, v, nm in (("dn", dn2, "downstream"), ("up", up2, "upstream")):
            line(f"| alpha = {f}/lambda_max | {nm} | {spearmanr(r[key][others], v[others]).correlation:.4f} | {len(set(np.argsort(-r[key])[:10]) & set(np.argsort(-v)[:10]))}/10 |")
    rs_ = res[("substantive_only", "dedupe")]; ks = rs_["kept"]
    line("\n## 5. Boilerplate effect on the seed view (substantive_only vs full, merged_dedupe)\n")
    common = [n["id"] for n in ks]
    line("| Direction | Spearman vs full | Top-10 overlap | Legislation Act 2019 seed-rank (full -> substantive) | Legislation Act 2019 global rank (full -> substantive) |"); line("|---|---|---|---|---|")
    ix = lambda rr: {n["id"]: i for i, n in enumerate(rr["kept"])}
    ia, ib = ix(r), ix(rs_)
    la = [n for n in common if n.startswith("Legislation Act 2019")][0]
    for key, nm in (("dn", "downstream"), ("up", "upstream")):
        xa = np.array([r[key][ia[c]] for c in common]); xb_ = np.array([rs_[key][ib[c]] for c in common]); msk = np.array([c != SEED for c in common])
        ra_, rb_ = ranks(r[key]), ranks(rs_[key]); gA, gB = ranks(r["xg"]), ranks(rs_["xg"])
        line(f"| {nm} | {spearmanr(xa[msk], xb_[msk]).correlation:.4f} | {len(set(np.argsort(-xa)[:10]) & set(np.argsort(-xb_)[:10]))}/10 | {ra_[ia[la]]} -> {rb_[ib[la]]} | {gA[ia[la]]} -> {gB[ib[la]]} |")

    line("\n## 6. Bracket: merged_sum vs merged_dedupe (seed-centred top-10 overlap)\n")
    r2 = res[("full", "sum")]
    line("| Direction | Spearman | Top-10 overlap |"); line("|---|---|---|")
    c2 = [n["id"] for n in r2["kept"]]; assert c2 == [n["id"] for n in r["kept"]]
    for key, nm in (("dn", "downstream"), ("up", "upstream")):
        line(f"| {nm} | {spearmanr(r[key][others], r2[key][others]).correlation:.4f} | {len(set(np.argsort(-r[key])[:10]) & set(np.argsort(-r2[key])[:10]))}/10 |")
    line(f"\nSeed global rank: dedupe {ranks(r['xg'])[s]}, sum {ranks(r2['xg'])[r2['s']]}.")

    # per-node CSV (merged_dedupe, full)
    rg, rd, ru = ranks(r["xg"]), ranks(r["dn"]), ranks(r["up"])
    with open(OUT / "full_merged_dedupe__seed_scores.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh); wr.writerow(["node", "layer", "global_katz", "global_rank", "downstream", "downstream_rank", "upstream", "upstream_rank"])
        for i in np.argsort(-r["dn"]):
            wr.writerow([k[i]["id"], k[i]["layer"], f"{r['xg'][i]:.6f}", rg[i], f"{r['dn'][i]:.6f}", rd[i], f"{r['up'][i]:.6f}", ru[i]])
    (OUT / "summary.md").write_text("\n".join(L), encoding="utf-8"); print("\nSaved -> outputs/seed_katz/")


if __name__ == "__main__":
    main()
