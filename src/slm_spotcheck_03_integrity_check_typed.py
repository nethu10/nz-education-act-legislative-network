"""
slm_spotcheck_03_integrity_check_typed.py

Option-3 integrity check: confirm every one of the 75 pairs in the original
SLM spot-check sample (outputs/spotcheck/sample.json) still exists in the
typed graph (outputs/graph_typed/edges.json), in the expected direction/type.

Old sample edges: for history_note snippets, source = the amended Act and
target = the amending Act (typed amendment edge runs target -> source);
for schedule_amendment snippets, source = amending Act, target = amended
(typed edge runs source -> target). Both directions are tested and reported.
Name variants in the old sample ("(RS Vol .., p ..)", "(YYYY No N (L))",
"Ratings" vs "Rating") are folded before matching.
Run from repo root: python src/slm_spotcheck_03_integrity_check_typed.py
"""
import json, re, collections
from pathlib import Path

def norm(n):
    n = n.replace("\xa0", " ").replace("’", "'")
    n = re.sub(r"\s*\(RS Vol[^)]*\)", "", n)
    n = re.sub(r"\s*\((?:SR|LI)\s*\d{4}/\d+\)\s*$", "", n)
    n = re.sub(r"\s*\(\d{4} No \d+[^)]*\)(\s*\(L\))?\s*$", "", n)
    n = re.sub(r"\s*\(\d{4} No \d+ \(L\)\)\s*$", "", n)
    n = re.sub(r"\s+", " ", n).strip().rstrip(".").strip().lower()
    return n.replace("ratings valuations", "rating valuations")

sample = json.load(open("outputs/spotcheck/sample.json"))
edges = json.load(open("outputs/graph_typed/edges.json"))
idx = collections.defaultdict(list)
for e in edges:
    idx[(norm(e["source"]), norm(e["target"]))].append(e)

rows, c = [], collections.Counter()
for x in sample:
    a, b = norm(x["source"]), norm(x["target"])
    exp_fwd = x["snippet_source"] != "history_note"   # expected typed direction
    exp = idx.get((a, b) if exp_fwd else (b, a), [])
    other = idx.get((b, a) if exp_fwd else (a, b), [])
    exp_am = [e for e in exp if e["edge_type"] == "amendment"]
    status = ("amendment edge present, expected direction" if exp_am else
              "pair present (citation only), expected direction" if exp else
              "pair present, opposite direction only" if other else "MISSING")
    c[status] += 1
    rows.append({"layer": x["layer"], "snippet_source": x["snippet_source"], "source": x["source"],
                 "target": x["target"], "status": status,
                 "typed_edge_types": sorted({e["edge_type"] for e in exp + other})})
for k, v in c.most_common(): print(f"{v:3d}  {k}")
by = collections.defaultdict(collections.Counter)
for r in rows: by[r["layer"]][r["status"]] += 1
for l in sorted(by): print(l, dict(by[l]))
Path("outputs/spotcheck/integrity_check_typed.json").write_text(json.dumps(rows, indent=1))
