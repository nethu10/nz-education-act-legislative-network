"""
build_no_artefact_graph_variant.py

Sensitivity variant of the typed graph with PUBLICATION-ARTEFACT citations removed (PCO reprint-note /
issue-authority text -- see boilerplate_citation_audit.py). The base graph is NOT modified.
  * citation edge weight -= publication_artefact count for that pair (edge dropped if weight reaches 0)
  * amendment edges untouched
  * drafting-template citations are KEPT (they are enacted text)
Run from repo root after boilerplate_citation_audit.py:  python src/build_no_artefact_graph_variant.py
  Substantive-only variant:  python src/build_no_artefact_graph_variant.py --drop publication_artefact,drafting_template --out outputs/graph_typed_substantive_only
Outputs: outputs/graph_typed_no_artefact/{nodes,edges,edges_collapsed}.json|csv, graph_summary.json
"""
import argparse, csv, json
from collections import defaultdict, Counter
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--drop", default="publication_artefact", help="comma list of kinds to remove: publication_artefact,drafting_template")
ap.add_argument("--out", default="outputs/graph_typed_no_artefact")
args = ap.parse_args()
DROP = args.drop.split(",")
BASE, AUD, OUT = Path("outputs/graph_typed"), Path("outputs/boilerplate_audit"), Path(args.out)
OUT.mkdir(parents=True, exist_ok=True)
edges = json.loads((BASE / "edges.json").read_text(encoding="utf-8"))
nodes = json.loads((BASE / "nodes.json").read_text(encoding="utf-8"))
art = {(r["source"], r["target"]): sum(r.get(k, 0) for k in DROP)
       for r in json.loads((AUD / "pair_counts.json").read_text(encoding="utf-8"))}

new, dropped, reduced, removed_w = [], 0, 0, 0
for e in edges:
    if e["edge_type"] == "citation":
        a = art.get((e["source"], e["target"]), 0)
        if a:
            assert a <= e["weight"], (e["source"], e["target"], a, e["weight"])
            removed_w += a
            if a == e["weight"]: dropped += 1; continue
            e = {**e, "weight": e["weight"] - a}; reduced += 1
    new.append(e)

coll = defaultdict(lambda: {"amend": 0, "cite": 0})
for e in new: coll[(e["source"], e["target"])]["amend" if e["edge_type"] == "amendment" else "cite"] += e["weight"]
collapsed = [{"source": s, "target": t, "amendment_weight": v["amend"], "citation_weight": v["cite"],
              "total_weight": v["amend"] + v["cite"]} for (s, t), v in coll.items()]

adj, deg = defaultdict(set), Counter()
for e in new:
    adj[e["source"]].add(e["target"]); adj[e["target"]].add(e["source"]); deg[e["source"]] += 1; deg[e["target"]] += 1
ids = [n["id"] for n in nodes]; seen, comps = set(), []
for i in ids:
    if i in seen: continue
    st, c = [i], 0; seen.add(i)
    while st:
        x = st.pop(); c += 1
        for y in adj[x]:
            if y not in seen: seen.add(y); st.append(y)
    comps.append(c)
for n in nodes: n["degree_multi"], n["degree_distinct"] = deg[n["id"]], len(adj[n["id"]])
summary = {"nodes": len(nodes), "multi_edges": len(new), "amendment_edges": sum(e["edge_type"] == "amendment" for e in new),
           "citation_edges": sum(e["edge_type"] == "citation" for e in new), "collapsed_edges": len(collapsed),
           "citation_edges_dropped_entirely": dropped, "citation_edges_reduced": reduced,
           "citation_weight_removed": removed_w, "citation_weight_total": sum(e["weight"] for e in new if e["edge_type"] == "citation"),
           "isolated_nodes": sum(1 for i in ids if deg[i] == 0), "weakly_connected_components": len(comps), "largest_component": max(comps)}
(OUT / "nodes.json").write_text(json.dumps(nodes, indent=2, ensure_ascii=False), encoding="utf-8")
(OUT / "edges.json").write_text(json.dumps(new, indent=2, ensure_ascii=False), encoding="utf-8")
(OUT / "edges_collapsed.json").write_text(json.dumps(collapsed, indent=2, ensure_ascii=False), encoding="utf-8")
(OUT / "graph_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
for name, rows in (("nodes", nodes), ("edges", new), ("edges_collapsed", collapsed)):
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader()
        for r in rows: w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for k, v in r.items()})
print(json.dumps(summary, indent=2)); print("Saved ->", OUT)
