"""
stage8_leiden_communities.py -- Stage 8: community detection (Leiden) on the FROZEN typed legislative network.

Design decisions (agreed 14 Oct 2026)
  * Graph: the frozen graph (checked against outputs/GRAPH_FROZEN.json before anything runs); communities are found ONCE across
    all five layers together (not per layer), as the supervisor directed.
  * Corpora: option C. All three corpora are run: substantive_only (HEADLINE), no_artefact, full (sensitivity check).
  * Direction: the network is directed (an edge points from the amending / citing Act to the amended / cited Act).
    HEADLINE = directed modularity (null model: out-degree of i x in-degree of j). Sensitivity = the undirected version
    (reciprocal edges summed), which is the textbook form of modularity.
  * Edge weight: the same weighted view as Katz (amendment operations + citation mentions). Sensitivity: log(1 + weight).
  * Algorithm: Leiden (leidenalg, RBConfigurationVertexPartition, iterated until stable). Resolution gamma = 1 is the
    standard modularity objective and is the fixed headline value (no hand-picking); a resolution sweep is reported
    as a sensitivity analysis because modularity has a known resolution limit.
  * Reproducibility: 20 fixed random seeds (1..20) per configuration; the reported partition is the highest-quality run;
    stability = mean pairwise Adjusted Rand Index (ARI) between the 20 runs.

Needs:  pip install python-igraph leidenalg scikit-learn
Run from repo root:  python src/stage8_leiden_communities.py
Read-only on all graph data. Outputs: outputs/leiden/{summary.md, membership_<corpus>__<mode>.csv, headline_communities.csv, sweep.csv}
"""
import csv, hashlib, itertools, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import igraph as ig
import leidenalg as la
from sklearn.metrics import adjusted_rand_score as ARI, normalized_mutual_info_score as NMI

OUT = Path("outputs/leiden"); OUT.mkdir(parents=True, exist_ok=True)
CORPORA = {"full": Path("outputs/graph_typed"), "no_artefact": Path("outputs/graph_typed_no_artefact"),
           "substantive_only": Path("outputs/graph_typed_substantive_only")}
HEADLINE = ("substantive_only", "directed", "weighted")
SEED_ACT = "Education and Training Act 2020"
SEEDS = list(range(1, 21)); SWEEP = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0); SWEEP_SEEDS = list(range(1, 6))
STOP = set("act acts regulations regulation rules rule order orders amendment amendments the of and for to in on a an no sr li new zealand 2000 19 20 number".split())
L = []
def line(s=""): L.append(s); print(s)


# ---------------------------------------------------------------- freeze check
def verify_frozen():
    fz = Path("outputs/GRAPH_FROZEN.json")
    if not fz.exists(): sys.exit("!! outputs/GRAPH_FROZEN.json missing: run python src/freeze_graph.py first")
    saved = json.loads(fz.read_text(encoding="utf-8"))["corpora"]
    for k, d in CORPORA.items():
        for f, h in saved[k]["sha256"].items():
            if hashlib.sha256((d / f).read_bytes()).hexdigest() != h: sys.exit(f"!! {d/f} differs from the frozen graph; stop and tell Claude")
    line("Frozen graph verified (SHA-256 of nodes/edges/collapsed files, all three corpora).\n")


# ---------------------------------------------------------------- graph building
def load(d):
    return json.loads((d / "nodes.json").read_text(encoding="utf-8")), json.loads((d / "edges.json").read_text(encoding="utf-8"))

def build(ids, nodes, edges, mode, wview):
    """igraph graph over the common node order `ids`. mode: directed | undirected. wview: weighted | log_weighted."""
    idx = {n: i for i, n in enumerate(ids)}
    w = defaultdict(float)
    for e in edges:
        s, t = idx[e["source"]], idx[e["target"]]
        if s != t: w[(s, t)] += e["weight"]
    if wview == "log_weighted": w = {k: float(np.log1p(v)) for k, v in w.items()}
    g = ig.Graph(n=len(ids), edges=list(w.keys()), directed=True); g.es["weight"] = list(w.values())
    if mode == "undirected": g = g.as_undirected(mode="collapse", combine_edges="sum")
    g.vs["name"] = ids
    return g

def leiden(g, gamma, seed):
    p = la.find_partition(g, la.RBConfigurationVertexPartition, weights="weight", resolution_parameter=gamma, n_iterations=-1, seed=seed)
    return p.membership, p.quality()

def modularity(g, memb):
    return g.modularity(memb, weights="weight", resolution=1.0, directed=g.is_directed())

def best_of(g, gamma, seeds):
    runs = [leiden(g, gamma, s) for s in seeds]
    best = max(range(len(runs)), key=lambda i: runs[i][1])
    return runs[best][0], [r[0] for r in runs]

def stability(parts):
    v = [ARI(a, b) for a, b in itertools.combinations(parts, 2)]
    return float(np.mean(v)), float(np.min(v))

def sizes(memb): return Counter(memb)

def relabel(memb):
    """community 1 = largest"""
    order = {c: i + 1 for i, (c, _) in enumerate(Counter(memb).most_common())}
    return [order[c] for c in memb]


# ---------------------------------------------------------------- reporting helpers
def title_words(names, k=4):
    c = Counter()
    for nm in names:
        base = re.sub(r"\s*\(.*?\)", "", nm)
        for w in set(re.findall(r"[A-Za-z][A-Za-z\-]+", base)):
            if w.lower() not in STOP and len(w) > 2: c[w.lower()] += 1
    return ", ".join(w for w, _ in c.most_common(k))

def load_katz(corpus):
    p = Path(f"outputs/stage7_katz/{corpus}__weighted.csv")
    if not p.exists(): return {}
    with open(p, encoding="utf-8") as fh: return {r["node"]: int(r["rank"]) for r in csv.DictReader(fh)}


def main():
    line("# Stage 8: Leiden community detection (frozen graph)\n")
    verify_frozen()
    nodes0, _ = load(CORPORA["full"]); ids = [n["id"] for n in nodes0]; layer = {n["id"]: n["layer"] for n in nodes0}
    data = {}
    for c, d in CORPORA.items():
        nodes, edges = load(d); assert set(n["id"] for n in nodes) == set(ids), f"node set differs in {c}"
        data[c] = (nodes, edges)
    assert SEED_ACT in layer, "seed Act not found"

    # ---- main runs: 3 corpora x {directed, undirected}, weighted, gamma = 1, 20 seeds
    line("## 1. Settings\n")
    line("| Item | Value |"); line("|---|---|")
    line(f"| Algorithm | Leiden (leidenalg {la.__version__}), objective = modularity at resolution gamma = 1, iterated until stable |")
    line(f"| Nodes / layers | {len(ids)} Acts, all five layers together (SG0 to SG5) |")
    line(f"| Weight | amendment operations + citation mentions (same as Katz); sensitivity log(1 + weight) |")
    line(f"| Seeds | {SEEDS[0]} to {SEEDS[-1]} (20 runs per setting); reported partition = best run |")
    line(f"| Headline | {HEADLINE[0]}, {HEADLINE[1]} modularity, weighted |\n")

    R = {}                                   # (corpus, mode, wview) -> dict
    configs = [(c, m, "weighted") for c in ("substantive_only", "no_artefact", "full") for m in ("directed", "undirected")]
    configs += [("substantive_only", m, "log_weighted") for m in ("directed", "undirected")]
    for key in configs:
        c, m, wv = key
        g = build(ids, *data[c], m, wv)
        memb, parts = best_of(g, 1.0, SEEDS)
        memb = relabel(memb); parts = [relabel(p) for p in parts]
        sm, smin = stability(parts); sz = sizes(memb)
        R[key] = dict(g=g, memb=memb, parts=parts, Q=modularity(g, memb), n=len(sz), largest=max(sz.values()), stab=sm, stabmin=smin,
                      small=sum(1 for v in sz.values() if v < 5), single=sum(1 for v in sz.values() if v == 1))

    line("## 2. Results at gamma = 1\n")
    line("| Corpus | Direction | Weight | Communities | Modularity Q | Largest community (share) | Communities with fewer than 5 Acts | Singletons | Stability across 20 seeds (mean ARI, min ARI) |")
    line("|---|---|---|---|---|---|---|---|---|")
    for key, r in R.items():
        tag = " **(headline)**" if key == HEADLINE else ""
        line(f"| {key[0]}{tag} | {key[1]} | {key[2]} | {r['n']} | {r['Q']:.3f} | {r['largest']} ({100*r['largest']/len(ids):.1f}%) | {r['small']} | {r['single']} | {r['stab']:.3f}, {r['stabmin']:.3f} |")

    # ---- agreement between settings
    H = R[HEADLINE]
    line("\n## 3. How much do the answers depend on the choices? (agreement with the headline partition)\n")
    line("ARI = Adjusted Rand Index and NMI = Normalised Mutual Information; 1 means identical groupings, 0 means no better than chance.\n")
    line("| Setting compared with the headline | ARI | NMI |"); line("|---|---|---|")
    for key, r in R.items():
        if key == HEADLINE: continue
        line(f"| {key[0]}, {key[1]}, {key[2]} | {ARI(H['memb'], r['memb']):.3f} | {NMI(H['memb'], r['memb']):.3f} |")

    # ---- resolution sweep on the headline corpus, both directions
    line("\n## 4. Resolution sweep (substantive_only, weighted, 5 seeds each; Q is always the standard modularity of the partition)\n")
    line("| Direction | gamma | Communities | Q | Largest share | NMI vs gamma = 1 | Acts in the seed's community |"); line("|---|---|---|---|---|---|---|")
    sweep_rows = []
    for m in ("directed", "undirected"):
        g = R[("substantive_only", m, "weighted")]["g"]; ref = R[("substantive_only", m, "weighted")]["memb"]; si = ids.index(SEED_ACT)
        for gm in SWEEP:
            memb, _ = best_of(g, gm, SWEEP_SEEDS); memb = relabel(memb); sz = sizes(memb)
            row = (m, gm, len(sz), modularity(g, memb), max(sz.values()) / len(ids), NMI(ref, memb), sz[memb[si]]); sweep_rows.append(row)
            line(f"| {m} | {gm} | {row[2]} | {row[3]:.3f} | {100*row[4]:.1f}% | {row[5]:.3f} | {row[6]} |")
    with open(OUT / "sweep.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["direction", "gamma", "communities", "modularity", "largest_share", "nmi_vs_gamma1", "seed_community_size"])
        for r in sweep_rows: w.writerow([r[0], r[1], r[2], f"{r[3]:.4f}", f"{r[4]:.4f}", f"{r[5]:.4f}", r[6]])

    # ---- the seed's community in every setting
    line("\n## 5. The Education and Training Act 2020's community in each setting\n")
    si = ids.index(SEED_ACT)
    line("| Corpus | Direction | Acts in the seed's community | Share of seed's direct neighbours inside (rely on it / it relies on) | Same-members stability across seeds (mean Jaccard) |"); line("|---|---|---|---|---|")
    for key, r in R.items():
        if key[2] != "weighted": continue
        g = build(ids, *data[key[0]], "directed", "weighted"); memb = r["memb"]; cs = memb[si]
        members = {i for i, c in enumerate(memb) if c == cs}
        outn = {e.target for e in g.es if e.source == si}; inn = {e.source for e in g.es if e.target == si}
        jac = []
        for p in r["parts"]:
            pm = {i for i, c in enumerate(p) if c == p[si]}; jac.append(len(members & pm) / len(members | pm))
        line(f"| {key[0]} | {key[1]} | {len(members)} | {100*len(inn & members)/max(len(inn),1):.0f}% / {100*len(outn & members)/max(len(outn),1):.0f}% | {np.mean(jac):.3f} |")

    # ---- headline communities table
    memb = H["memb"]; g = H["g"]; strength = g.strength(weights="weight", mode="all"); katz = load_katz(HEADLINE[0])
    by = defaultdict(list)
    for i, c in enumerate(memb): by[c].append(i)
    line("\n## 6. Headline communities (substantive_only, directed, gamma = 1): the 15 largest\n")
    line("| # | Acts | Layer mix (SG0/1/2/3/4/5) | Most connected Acts (by total weight) | Frequent title words (automatic draft, not a label) |"); line("|---|---|---|---|---|")
    rows = []
    for c in sorted(by, key=lambda c: -len(by[c])):
        mem = by[c]; lc = Counter(layer[ids[i]] for i in mem); mix = "/".join(str(lc.get(f"SG{k}", 0)) for k in range(6))
        top = sorted(mem, key=lambda i: -strength[i])[:5]; topn = "; ".join(re.sub(r"\s*\(.*?\)", "", ids[i])[:40] for i in top)
        words = title_words([ids[i] for i in mem]); rows.append((c, len(mem), mix, topn, words, ("SEED" if si in mem else "")))
        if c <= 15: line(f"| {c}{' (seed)' if si in mem else ''} | {len(mem)} | {mix} | {topn} | {words} |")
    with open(OUT / "headline_communities.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["community", "acts", "layer_mix_SG0_to_SG5", "most_connected", "title_words", "contains_seed"])
        for r in rows: w.writerow(r)

    # ---- seed community detail
    cs = memb[si]; mem = by[cs]
    line(f"\n## 7. The seed's community in detail (headline setting): {len(mem)} Acts\n")
    lc = Counter(layer[ids[i]] for i in mem)
    line("| Layer | Acts in the community | Acts in the whole network | Share of that layer |"); line("|---|---|---|---|")
    tot = Counter(layer.values())
    for k in range(6):
        s = f"SG{k}"; line(f"| {s} | {lc.get(s, 0)} | {tot[s]} | {100*lc.get(s,0)/tot[s]:.0f}% |")
    line("\nThe 20 best-connected members (total weight), with their Katz rank in the same (substantive-only) corpus at alpha = 0.9, where available:\n")
    line("| Act | Layer | Katz rank, substantive-only (of 2,475) |"); line("|---|---|---|")
    for i in sorted(mem, key=lambda i: -strength[i])[:20]:
        line(f"| {ids[i][:70]} | {layer[ids[i]]} | {katz.get(ids[i], '-')} |")

    # ---- membership files
    for key, r in R.items():
        with open(OUT / f"membership_{key[0]}__{key[1]}__{key[2]}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["node", "layer", "community"])
            for i, nid in enumerate(ids): w.writerow([nid, layer[nid], r["memb"][i]])
    (OUT / "summary.md").write_text("\n".join(L), encoding="utf-8"); print("\nSaved -> outputs/leiden/")


if __name__ == "__main__":
    main()
