"""
assemble_typed_multiedge_graph.py

Assembles the combined five-layer (seed + SG1..SG5) multi-edge directed graph
from the TYPED edge files, replacing assemble_multiedge_graph.py's coarse
"linked_from" / internal-link edges for Stage 7 (Katz centrality) and Stage 8
(Leiden communities). The old script is left untouched; this one writes to
outputs/graph_typed/ so the two can be compared.

Edge source of truth (verified exact partition, no pair appears twice):
  sg1_typed_*  : seed + SG1 pairs
  sg2_typed_*  : SG2-internal + (seed/SG1)<->SG2
  sg3_typed_*  : SG3-internal + (seed..SG2)<->SG3
  sg4_typed_*  : SG4-internal + (seed..SG3)<->SG4
  sg5_typed_*  : SG5-internal + (seed..SG4)<->SG5
Every edge is directed source -> target and is either "amendment" (with
operation counts) or "citation". An amendment and a citation between the same
pair stay as two separate edges (multi-edge); a collapsed simple digraph with
summed weights is written separately for algorithms that need one.

Nodes: seed + every final-list member of SG1..SG5 (2,484), identified by the
same normalised name key the edge builders use (NBSP/whitespace/trailing-period
folded, trailing citation stripped). Each node carries layer, identifier where
known, and has_xml (False = leaf-capable: no source text; can still be an edge
target and, for amendments, a source via the target's history notes).
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "src")
from sg3_filenames import filename_for_sg3
from sg4_filenames import filename_for_sg4

DATA = Path("data/processed")
RAW = Path("data/raw")
OUT = Path("outputs/graph_typed")
OUT.mkdir(parents=True, exist_ok=True)
SEED = "Education and Training Act 2020"

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
NAME_VARIANT_ALIASES = {
    "land transport rule: frontal impact 2001 (32006/1)": "land transport rule 32006/1: frontal impact 2001",
}


def normalize(name):
    name = name.replace("’", "'").replace("‘", "'").replace("\xa0", " ")
    name = re.sub(r"\s+", " ", name).strip().rstrip(".").strip()
    m = CITE_PATTERN.match(name)
    base = (m.group(1).strip() if m else name).lower()
    return NAME_VARIANT_ALIASES.get(base, base)


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


# ---------------- nodes ----------------
nodes = {}  # key -> dict


def add_node(name, layer, has_xml, year=None, number=None, doc_type=None, resolved=True):
    key = normalize(name)
    assert key not in nodes, f"duplicate node key: {name!r}"
    nodes[key] = {"id": name, "layer": layer, "has_xml": has_xml, "resolved": resolved,
                  "year": year, "number": number, "doc_type": doc_type}


add_node(SEED, "SG0", True)

for a in load("sg1_final_list.json"):
    m = CITE_PATTERN.match(a["act"].strip())
    year = number = None
    if m:
        cite = m.group(2)
        mm = re.match(r"(?:SR|LI)\s+(\d{4})/(\d+)", cite) or re.match(r"(\d{4})\s+No\s+(\d+)", cite)
        if mm:
            year, number = int(mm.group(1)), mm.group(2)
    add_node(a["act"], "SG1", True, year, number)  # all 37 SG1 documents have XML (checked by edge builders)

sg2_ids = {a["act"]: a for a in load("sg2_act_identifiers.json")}
for a in load("sg2_final_list.json"):
    i = sg2_ids.get(a["act"], {})
    fn = f"{i['year']}_{i['number']}.xml" if i.get("resolved") else None
    has_xml = bool(fn and (RAW / "sg2_targets" / fn).exists())
    add_node(a["act"], "SG2", has_xml, i.get("year"), i.get("number"), i.get("type"), bool(i.get("resolved")))

sg3_ids = {a["act"]: a for a in load("sg3_act_identifiers.json")}
for a in load("sg3_final_list.json"):
    i = sg3_ids.get(a["act"], {})
    fn = filename_for_sg3(i) if i else None
    has_xml = bool(fn and (RAW / "sg3_targets" / fn).exists())
    add_node(a["act"], "SG3", has_xml, i.get("year"), i.get("number"), i.get("type"), bool(i.get("resolved")))

sg4_ids = {a["act"]: a for a in load("sg4_act_identifiers.json")}
for a in load("sg4_final_list.json"):
    i = sg4_ids.get(a["act"], {})
    resolved = bool(i.get("resolved"))
    has_xml = resolved and i.get("xml_available") is not False
    add_node(a["act"], "SG4", has_xml, i.get("year"), i.get("number"), i.get("type"), resolved)

sg5_ids = {a["act"]: a for a in load("sg5_act_identifiers.json")}
for a in load("sg5_final_list.json"):
    i = sg5_ids.get(a["act"], {})
    resolved = bool(i.get("resolved"))
    has_xml = resolved and i.get("subtype") != "agency-drafted"
    add_node(a["act"], "SG5", has_xml, i.get("year"), i.get("number"), i.get("type"), resolved)

# ---------------- audit_fix_12: merge duplicate nodes (alias map) ----------------
FIX12 = DATA / "audit_fix_12_node_merges.json"
amap, merge_log = {}, {"merged_nodes": [], "self_loops_dropped": [], "collisions": []}
if FIX12.exists():
    for m in json.loads(FIX12.read_text(encoding="utf-8"))["merges"]:
        ak = normalize(m["alias"])
        assert ak in nodes, m["alias"]
        if m["kind"] == "merge":
            ck = normalize(m["canonical"]); assert ck in nodes and ck != ak, m["canonical"]
            merge_log["merged_nodes"].append({"alias": nodes[ak]["id"], "alias_layer": nodes[ak]["layer"],
                                              "into": nodes[ck]["id"], "into_layer": nodes[ck]["layer"]})
            del nodes[ak]; amap[ak] = ck
        else:  # rename
            ck = normalize(m["canonical"]); assert ck not in nodes, m["canonical"]
            node = nodes.pop(ak); merge_log["merged_nodes"].append({"alias": node["id"], "renamed_to": m["canonical"]})
            node["id"] = m["canonical"]; nodes[ck] = node; amap[ak] = ck

# ---------------- edges ----------------
edges = []
seen = set()
raw_edges = []
for n in range(1, 6):
    layer = f"SG{n}"
    for etype in ("amendment", "citation"):
        for e in load(f"sg{n}_typed_{etype}_edges.json"):
            sk0, tk0 = normalize(e["source"]), normalize(e["target"])
            assert sk0 != tk0, f"self-loop {e['source']}"
            dedup = (sk0, tk0, etype)
            assert dedup not in seen, f"pair appears in two layer files: {e['source']} -> {e['target']} ({etype})"
            seen.add(dedup)
            sk, tk = amap.get(sk0, sk0), amap.get(tk0, tk0)
            assert sk in nodes and tk in nodes, (e["source"], e["target"])
            raw_edges.append((sk0, sk, tk, etype, layer, e))

# Merge policy "dedupe" (see audit_fix_12_merge_duplicate_nodes.py):
#   self-loops created by a merge are dropped; amendment edges: larger count; citation edges: sum the references
#   made by one original source document, then, if several original documents of a merged node cite the same
#   target, keep the larger (they are the same text).
groups = defaultdict(list)
for sk0, sk, tk, etype, layer, e in raw_edges:
    if sk == tk:
        merge_log["self_loops_dropped"].append({"source": nodes[sk]["id"], "target": nodes[tk]["id"], "type": etype, "count": e["count"]})
        continue
    groups[(sk, tk, etype)].append((sk0, layer, e))
for (sk, tk, etype), mem in groups.items():
    if etype == "amendment":
        pick = max(mem, key=lambda m: m[2]["count"]); count = pick[2]["count"]; layer, e = pick[1], pick[2]
    else:
        per_src = defaultdict(list)
        for m in mem: per_src[m[0]].append(m)
        totals = {k: sum(x[2]["count"] for x in v) for k, v in per_src.items()}
        best = max(totals, key=totals.get); count = totals[best]
        layer, e = per_src[best][0][1], per_src[best][0][2]
    if len(mem) > 1:
        merge_log["collisions"].append({"source": nodes[sk]["id"], "target": nodes[tk]["id"], "type": etype,
                                        "counts": [m[2]["count"] for m in mem], "kept": count})
    edges.append({
        "source": nodes[sk]["id"], "target": nodes[tk]["id"],
        "edge_type": etype, "layer": layer, "scope": e.get("scope"),
        "weight": count,
        "operations": e.get("operations") if etype == "amendment" else None,
        "operation_source": e.get("operation_source"),
        "confirmed_by_outgoing_schedule": e.get("confirmed_by_outgoing_schedule"),
        "source_layer": nodes[sk]["layer"], "target_layer": nodes[tk]["layer"],
    })

# ---------------- collapsed simple digraph ----------------
coll = defaultdict(lambda: {"amend": 0, "cite": 0})
for e in edges:
    k = (e["source"], e["target"])
    coll[k]["amend" if e["edge_type"] == "amendment" else "cite"] += e["weight"]
collapsed = [{"source": s, "target": t, "amendment_weight": v["amend"], "citation_weight": v["cite"],
              "total_weight": v["amend"] + v["cite"]} for (s, t), v in coll.items()]

# ---------------- degree / components ----------------
deg = Counter()
adj = defaultdict(set)
for e in edges:
    deg[e["source"]] += 1
    deg[e["target"]] += 1
    adj[e["source"]].add(e["target"])
    adj[e["target"]].add(e["source"])
ids = [v["id"] for v in nodes.values()]
isolated = [i for i in ids if deg[i] == 0]
seen_n, comps = set(), []
for i in ids:
    if i in seen_n:
        continue
    stack, comp = [i], 0
    seen_n.add(i)
    while stack:
        x = stack.pop(); comp += 1
        for y in adj[x]:
            if y not in seen_n:
                seen_n.add(y); stack.append(y)
    comps.append(comp)
comps.sort(reverse=True)

# ---------------- write ----------------
node_rows = []
for v in nodes.values():
    node_rows.append({**v, "degree_multi": deg[v["id"]], "degree_distinct": len(adj[v["id"]])})
node_rows.sort(key=lambda r: (r["layer"], r["id"]))
(OUT / "nodes.json").write_text(json.dumps(node_rows, indent=2, ensure_ascii=False), encoding="utf-8")
(OUT / "edges.json").write_text(json.dumps(edges, indent=2, ensure_ascii=False), encoding="utf-8")
(OUT / "edges_collapsed.json").write_text(json.dumps(collapsed, indent=2, ensure_ascii=False), encoding="utf-8")
with open(OUT / "nodes.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id", "layer", "has_xml", "resolved", "year", "number", "doc_type", "degree_multi", "degree_distinct"])
    for r in node_rows:
        w.writerow([r["id"], r["layer"], r["has_xml"], r["resolved"], r["year"], r["number"], r["doc_type"], r["degree_multi"], r["degree_distinct"]])
with open(OUT / "edges.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["source", "target", "edge_type", "layer", "scope", "weight", "source_layer", "target_layer", "operations"])
    for e in sorted(edges, key=lambda e: (e["layer"], e["edge_type"], e["source"], e["target"])):
        w.writerow([e["source"], e["target"], e["edge_type"], e["layer"], e["scope"], e["weight"], e["source_layer"], e["target_layer"],
                    json.dumps(e["operations"], ensure_ascii=False) if e["operations"] else ""])
with open(OUT / "edges_collapsed.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["source", "target", "amendment_weight", "citation_weight", "total_weight"])
    for c in collapsed:
        w.writerow([c["source"], c["target"], c["amendment_weight"], c["citation_weight"], c["total_weight"]])

by_layer = Counter(v["layer"] for v in nodes.values())
am = [e for e in edges if e["edge_type"] == "amendment"]
ci = [e for e in edges if e["edge_type"] == "citation"]
summary = {
    "nodes": len(nodes), "nodes_by_layer": dict(sorted(by_layer.items())),
    "nodes_without_xml": sum(1 for v in nodes.values() if not v["has_xml"]),
    "nodes_unresolved": sum(1 for v in nodes.values() if not v["resolved"]),
    "multi_edges": len(edges), "amendment_edges": len(am), "citation_edges": len(ci),
    "amendment_operations_total": sum(e["weight"] for e in am), "citation_weight_total": sum(e["weight"] for e in ci),
    "collapsed_edges": len(collapsed), "isolated_nodes": len(isolated),
    "weakly_connected_components": len(comps), "largest_component": comps[0], "component_sizes_top10": comps[:10],
    "edges_by_layer": {l: Counter(e["layer"] for e in edges)[l] for l in sorted({e["layer"] for e in edges})},
}
(OUT / "graph_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
if FIX12.exists():
    (OUT / "merge_log.json").write_text(json.dumps(merge_log, indent=2, ensure_ascii=False), encoding="utf-8")
    summary["audit_fix_12"] = {"nodes_merged_or_renamed": len(merge_log["merged_nodes"]),
                               "self_loops_dropped": len(merge_log["self_loops_dropped"]),
                               "edge_collisions_resolved": len(merge_log["collisions"])}
(OUT / "graph_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
if isolated:
    print("Isolated nodes:", isolated[:20])
print(f"\nSaved -> {OUT}/ (nodes, edges, edges_collapsed as .json and .csv; graph_summary.json)")
