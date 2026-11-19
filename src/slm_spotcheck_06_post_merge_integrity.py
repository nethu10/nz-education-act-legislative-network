"""
slm_spotcheck_06_post_merge_integrity.py   (read-only)

After audit_fix_12 (6 duplicate nodes merged, 1 renamed), is the SLM spot-check still valid?
The SLM judged the TEXT evidence behind each sampled edge, so an edge whose two Acts are not
touched by the merge has an unchanged result. This script checks all sampled edges in
outputs/spotcheck/sample_typed.json against the FINAL graph (outputs/graph_typed/edges.json):

  unchanged   : neither Act was merged/renamed and the edge (same type) is still in the graph
  merged      : an Act in the pair was merged/renamed; edge looked up under the merged node
  merged_ok   : ... and the edge (same type) exists under the merged name
  missing     : the edge (same type) is no longer in the graph  <-- would need investigation

It then recomputes the agreement rate from results_typed.json for the unchanged set and the
whole sample, using the same definitions as slm_spotcheck_05. Writes
outputs/spotcheck/post_merge_integrity.{json,md}. Run from repo root:
    python src/slm_spotcheck_06_post_merge_integrity.py
"""
import importlib.util, json, math, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
spec = importlib.util.spec_from_file_location("ba", "src/boilerplate_citation_audit.py")
ba = importlib.util.module_from_spec(spec); spec.loader.exec_module(ba)
normalize = ba.normalize

OUT = Path("outputs/spotcheck")
sample = json.loads((OUT / "sample_typed.json").read_text(encoding="utf-8"))
edges = json.loads(Path("outputs/graph_typed/edges.json").read_text(encoding="utf-8"))
have = {(normalize(e["source"]), normalize(e["target"]), e["edge_type"]) for e in edges}
amap = {normalize(m["alias"]): normalize(m["canonical"])
        for m in json.loads(Path("data/processed/audit_fix_12_node_merges.json").read_text(encoding="utf-8"))["merges"]}
rp = OUT / "results_typed.json"
results = {(r["layer"], r["source"], r["target"], r["rule_based_edge_type"]): r
           for r in json.loads(rp.read_text(encoding="utf-8"))} if rp.exists() else {}

def agree(r):
    t = r["slm_type"]
    if r["rule_based_edge_type"] == "amendment": return t == "amendment"
    return t in ("citation", "definition_reference")        # lenient, as in script 05

def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)

rows = []
for s in sample:
    sk, tk, et = normalize(s["source"]), normalize(s["target"]), s["rule_based_edge_type"] if "rule_based_edge_type" in s else s.get("edge_type")
    touched = sk in amap or tk in amap
    present = (amap.get(sk, sk), amap.get(tk, tk), et) in have
    cls = ("merged_ok" if present else "missing") if touched else ("unchanged" if present else "missing")
    rows.append({"layer": s["layer"], "source": s["source"], "target": s["target"], "edge_type": et, "class": cls,
                 "result": results.get((s["layer"], s["source"], s["target"], et))})
cnt = Counter(r["class"] for r in rows)
L = []
def line(x=""): L.append(x); print(x)
line(f"\n## SLM spot-check vs the final (merged) graph: {len(rows)} sampled edges\n")
line("| Class | Edges |"); line("|---|---|")
for k in ("unchanged", "merged_ok", "missing"): line(f"| {k} | {cnt.get(k, 0)} |")
if results:
    line("\n| Agreement (lenient for citation) | Agree / n | Rate | Wilson 95% CI |"); line("|---|---|---|---|")
    for lab, sel in (("amendment, all sampled", lambda r: r["edge_type"] == "amendment"),
                     ("citation, all sampled", lambda r: r["edge_type"] == "citation"),
                     ("amendment, unaffected by merge", lambda r: r["edge_type"] == "amendment" and r["class"] == "unchanged"),
                     ("citation, unaffected by merge", lambda r: r["edge_type"] == "citation" and r["class"] == "unchanged")):
        rs = [r["result"] for r in rows if sel(r) and r["result"]]
        k = sum(agree(r) for r in rs); lo, hi = wilson(k, len(rs))
        line(f"| {lab} | {k}/{len(rs)} | {100*k/max(len(rs),1):.1f}% | {100*lo:.1f}-{100*hi:.1f}% |")
aff = [r for r in rows if r["class"] != "unchanged"]
if aff:
    line("\n### Sampled edges touched by the merge, or no longer in the graph\n"); line("| Layer | Type | Source | Target | Class |"); line("|---|---|---|---|---|")
    for r in aff: line(f"| {r['layer']} | {r['edge_type']} | {r['source'][:45]} | {r['target'][:45]} | {r['class']} |")
(OUT / "post_merge_integrity.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
(OUT / "post_merge_integrity.md").write_text("\n".join(L), encoding="utf-8")
