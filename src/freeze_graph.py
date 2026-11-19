"""
freeze_graph.py  (read-only on graph data)

Declares the graph FROZEN for Stage 8 (Leiden) and all later stages. Verifies the three corpora
(full, no_artefact, substantive_only) against the expected counts, fingerprints their files with
SHA-256, and writes outputs/GRAPH_FROZEN.json. Later stages can re-run this with --check to prove
they are still working on the same graph. Run from repo root:
    python src/freeze_graph.py          # write the manifest
    python src/freeze_graph.py --check  # verify nothing changed since
"""
import hashlib, json, sys
from collections import Counter
from pathlib import Path

CORPORA = {"full": "outputs/graph_typed", "no_artefact": "outputs/graph_typed_no_artefact",
           "substantive_only": "outputs/graph_typed_substantive_only"}
EXPECT = {"full": (2475, 14805, 24183), "no_artefact": (2475, 14805, 22952), "substantive_only": (2475, 14805, 22399)}
FILES = ("nodes.json", "edges.json", "edges_collapsed.json")
OUT = Path("outputs/GRAPH_FROZEN.json")

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def snapshot():
    snap, ok = {}, True
    for k, d in CORPORA.items():
        nodes = json.loads((Path(d) / "nodes.json").read_text(encoding="utf-8"))
        edges = json.loads((Path(d) / "edges.json").read_text(encoding="utf-8"))
        coll = json.loads((Path(d) / "edges_collapsed.json").read_text(encoding="utf-8"))
        c = Counter(e["edge_type"] for e in edges)
        got = (len(nodes), c["amendment"], c["citation"])
        good = got == EXPECT[k]; ok &= good
        print(f"{k:17s} nodes {got[0]}  amendment {got[1]}  citation {got[2]}  collapsed {len(coll)}  expected-match: {good}")
        snap[k] = {"dir": d, "nodes": got[0], "amendment_edges": got[1], "citation_edges": got[2],
                   "collapsed_edges": len(coll), "sha256": {f: sha(Path(d) / f) for f in FILES}}
    return snap, ok

if "--check" in sys.argv:
    saved = json.loads(OUT.read_text(encoding="utf-8"))["corpora"]
    snap, ok = snapshot()
    same = all(snap[k]["sha256"] == saved[k]["sha256"] for k in snap)
    print("\nFROZEN GRAPH UNCHANGED" if same and ok else "\n!! GRAPH DIFFERS FROM THE FROZEN VERSION"); sys.exit(0 if same and ok else 1)

snap, ok = snapshot()
if not ok: sys.exit("!! counts differ from the expected frozen figures; nothing written")
OUT.write_text(json.dumps({"frozen_on": "2026-10-14", "decision": "graph frozen after audit_fix_12, body-gap audit and SLM spot-check; Stage 8 corpus option C (run full, no_artefact, substantive_only; substantive_only is the Leiden headline, full is the sensitivity check)", "corpora": snap}, indent=1), encoding="utf-8")
print(f"\nWrote {OUT}")
