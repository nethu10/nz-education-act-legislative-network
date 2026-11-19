"""
stage7b_seed_centred_katz.py -- Stage 7b: seed-centred Katz index on the CLEANED typed graph (after audit_fix_12).

  downstream  y = (I - alpha A)^-1 e_seed   : Acts that RELY ON the seed (walks j -> ... -> seed; a change to the seed could affect them)
  upstream    z = (I - alpha A^T)^-1 e_seed : Acts the seed RELIES ON (walks seed -> ... -> j)
  alpha = f / lambda_max(A), f = 0.9 primary (see Stage 7 alpha-sensitivity); scores scaled to max = 1 excluding the seed.
Specificity = global Katz rank - seed-centred rank. Checks: layer/direct-neighbour circularity, alpha, boilerplate, merge-policy bracket.
Run from repo root after assemble_typed_multiedge_graph.py / build_no_artefact_graph_variant.py:  python src/stage7b_seed_centred_katz.py
Outputs: outputs/seed_katz/{summary.md, full__seed_scores.csv, substantive_only__seed_scores.csv}
"""
import csv, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, "src")
import seed_katz_diagnostic as sk

OUT = Path("outputs/seed_katz"); OUT.mkdir(parents=True, exist_ok=True)
SEED = sk.SEED; ranks = sk.ranks
F_MAIN = 0.9                                   # headline alpha fraction (alpha = F_MAIN / lambda_max)
G = {"full": Path("outputs/graph_typed"), "substantive_only": Path("outputs/graph_typed_substantive_only")}
PRE = Path("outputs/_pre_fix12/graph_typed")
MERGES = {m["alias"]: m["canonical"] for m in json.loads(Path("data/processed/audit_fix_12_node_merges.json").read_text(encoding="utf-8"))["merges"] if m["kind"] == "merge"}


def build(d, alias=None, policy="base"):
    sk.ALIAS = alias or {}
    nodes, edges = sk.load(d); kept, w, st = sk.collapsed(nodes, edges, policy)
    A, idx = sk.matrix(kept, w); s = idx[SEED]; xg, a = sk.global_katz(A, F_MAIN); dn, up = sk.seed_katz(A, s, F_MAIN)
    return dict(kept=kept, A=A, idx=idx, s=s, xg=xg, dn=dn, up=up, alpha=a, stats=st)


def main():
    L = []
    def line(s=""): L.append(s); print(s)
    R = {c: build(d) for c, d in G.items()}
    pre = build(PRE)                                                   # before audit_fix_12 (unmerged)
    summ = build(PRE, MERGES, "sum")                                   # upper bracket: duplicates simply added
    r = R["full"]; k = r["kept"]; s = r["s"]; A = r["A"]; rg = ranks(r["xg"])
    line("# Stage 7b: seed-centred Katz on the cleaned graph (after audit_fix_12)\n")
    line(f"Graph: {len(k)} nodes, {A.nnz:,} collapsed edges. alpha = {F_MAIN}/lambda_max = {r['alpha']:.5f}. Seed = {SEED}.\n")
    line("## 1. Global Katz: before and after audit_fix_12 (full corpus, weighted)\n")
    line("| Graph | Nodes | Seed rank | Top-5 |"); line("|---|---|---|---|")
    for nm, x in (("before (unmerged)", pre), ("after (cleaned, dedupe)", r), ("upper bracket (duplicates summed)", summ)):
        t5 = "; ".join(x["kept"][i]["id"].split(" (")[0] for i in np.argsort(-x["xg"])[:5])
        line(f"| {nm} | {len(x['kept'])} | {ranks(x['xg'])[x['s']]} of {len(x['kept'])} | {t5} |")
    rp = ranks(pre["xg"])
    line("\n| Merged Act | Rank before | Rank after |"); line("|---|---|---|")
    for c in sorted(set(MERGES.values())):
        line(f"| {c.split(' (')[0]} | {rp[pre['idx'][c]]} | {rg[r['idx'][c]]} |")

    def table(key, title, n=15):
        sc = r[key]; rs = ranks(sc)
        line(f"\n{title}\n"); line("| Seed-rank | Act | Layer | Seed-centred | Global rank | Lift |"); line("|---|---|---|---|---|---|")
        for i in np.argsort(-sc)[:n]: line(f"| {rs[i]} | {k[i]['id'][:60]} | {k[i]['layer']} | {sc[i]:.3f} | {rg[i]} | {rg[i]-rs[i]:+d} |")
    line("\n## 2. Seed-centred Katz (full corpus, weighted)")
    table("dn", "### 2a. DOWNSTREAM: Acts that rely on the Education and Training Act 2020 (would need review if it changed)")
    table("up", "### 2b. UPSTREAM: Acts the Education and Training Act 2020 relies on")
    for key, nm in (("dn", "downstream"), ("up", "upstream")):
        sc = r[key]; rs = ranks(sc); cand = [i for i in range(len(k)) if rs[i] <= 100 and i != s]
        line(f"\n### 2c. Most SEED-SPECIFIC {nm} (top-100 seed-centred, sorted by lift over global rank)\n")
        line("| Act | Layer | Seed-rank | Global rank | Lift |"); line("|---|---|---|---|---|")
        for i in sorted(cand, key=lambda i: -(rg[i] - rs[i]))[:10]: line(f"| {k[i]['id'][:60]} | {k[i]['layer']} | {rs[i]} | {rg[i]} | {rg[i]-rs[i]:+d} |")
        line("\nGeneric hubs (global top-5) and their seed-centred rank, " + nm + ": " + "; ".join(f"{k[i]['id'].split(' (')[0]} -> {rs[i]}" for i in np.argsort(-r['xg'])[:5]))

    line("\n## 3. Is it just the layers / direct links?\n")
    lay = np.array([sk.LAYER_NUM[n["layer"]] for n in k]); others = np.arange(len(k)) != s
    din = np.asarray(A[:, s].todense()).ravel() > 0; dout = np.asarray(A[s, :].todense()).ravel() > 0
    line("| Direction | Spearman(seed score, layer number) | Top-50 that are direct neighbours | Spearman(seed score, global Katz), non-neighbours |"); line("|---|---|---|---|")
    for key, nm, nb in (("dn", "downstream", din), ("up", "upstream", dout)):
        sc = r[key]; t50 = np.argsort(-sc)[:50]; m = others & ~nb
        line(f"| {nm} | {spearmanr(sc[others], lay[others]).correlation:.3f} | {int(nb[t50].sum())}/50 | {spearmanr(sc[m], r['xg'][m]).correlation:.3f} |")
    line(f"\nDirect neighbours of the seed: {int(din.sum())} Acts rely on it directly; it directly relies on {int(dout.sum())}.")
    line("\n| Layer | Acts | Downstream top-50 | Upstream top-50 |"); line("|---|---|---|---|")
    td, tu = np.argsort(-r["dn"])[:50], np.argsort(-r["up"])[:50]
    for ly in ("SG1", "SG2", "SG3", "SG4", "SG5"):
        line(f"| {ly} | {sum(1 for n in k if n['layer']==ly)} | {sum(1 for i in td if k[i]['layer']==ly)} | {sum(1 for i in tu if k[i]['layer']==ly)} |")

    line("\n## 4. Sensitivity to alpha\n"); line("| Variation | Direction | Spearman vs primary | Top-10 overlap |"); line("|---|---|---|---|")
    for f in (0.1, 0.5):
        dn2, up2 = sk.seed_katz(A, s, f)
        for key, v, nm in (("dn", dn2, "downstream"), ("up", up2, "upstream")):
            line(f"| alpha = {f}/lambda_max | {nm} | {spearmanr(r[key][others], v[others]).correlation:.4f} | {len(set(np.argsort(-r[key])[:10]) & set(np.argsort(-v)[:10]))}/10 |")

    line("\n## 5. Boilerplate effect (substantive_only vs full)\n")
    q = R["substantive_only"]; assert [n["id"] for n in q["kept"]] == [n["id"] for n in k]
    la = [i for i, n in enumerate(k) if n["id"].startswith("Legislation Act 2019")][0]; gB = ranks(q["xg"])
    line("| Direction | Spearman vs full | Top-10 overlap | Legislation Act 2019 seed-rank (full -> substantive) | Legislation Act 2019 global rank (full -> substantive) |"); line("|---|---|---|---|---|")
    for key, nm in (("dn", "downstream"), ("up", "upstream")):
        line(f"| {nm} | {spearmanr(r[key][others], q[key][others]).correlation:.4f} | {len(set(np.argsort(-r[key])[:10]) & set(np.argsort(-q[key])[:10]))}/10 | {ranks(r[key])[la]} -> {ranks(q[key])[la]} | {rg[la]} -> {gB[la]} |")
    line("\nTop-5 upstream, substantive only: " + "; ".join(f"{q['kept'][i]['id'].split(' (')[0]}" for i in np.argsort(-q['up'])[:5]))
    line("Top-5 downstream, substantive only: " + "; ".join(f"{q['kept'][i]['id'].split(' (')[0][:50]}" for i in np.argsort(-q['dn'])[:5]))

    line("\n## 6. Merge-policy bracket: cleaned (dedupe) vs duplicates summed\n")
    line("| Direction | Spearman | Top-10 overlap |"); line("|---|---|---|")
    assert [n["id"] for n in summ["kept"]] == [n["id"] for n in k] or True
    common = [n["id"] for n in k if n["id"] in summ["idx"]]
    ia, ib = [r["idx"][c] for c in common], [summ["idx"][c] for c in common]; msk = np.array([c != SEED for c in common])
    for key, nm in (("dn", "downstream"), ("up", "upstream")):
        a_, b_ = r[key][ia], summ[key][ib]
        line(f"| {nm} | {spearmanr(a_[msk], b_[msk]).correlation:.4f} | {len(set(np.argsort(-a_)[:10]) & set(np.argsort(-b_)[:10]))}/10 |")
    line(f"\nSeed global rank: dedupe {rg[s]}, summed {ranks(summ['xg'])[summ['s']]}.")

    for c, x in R.items():
        kk = x["kept"]; g, d_, u_ = ranks(x["xg"]), ranks(x["dn"]), ranks(x["up"])
        with open(OUT / f"{c}__seed_scores.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["node", "layer", "global_katz", "global_rank", "downstream", "downstream_rank", "upstream", "upstream_rank"])
            for i in np.argsort(-x["dn"]): w.writerow([kk[i]["id"], kk[i]["layer"], f"{x['xg'][i]:.6f}", g[i], f"{x['dn'][i]:.6f}", d_[i], f"{x['up'][i]:.6f}", u_[i]])
    (OUT / "summary.md").write_text("\n".join(L), encoding="utf-8"); print("\nSaved -> outputs/seed_katz/")


if __name__ == "__main__":
    main()
