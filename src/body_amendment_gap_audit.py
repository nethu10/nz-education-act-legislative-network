"""
body_amendment_gap_audit.py

Do amendments that an Act states in its OWN body text ("This Act amends the X Act 2000.",
"This section amends ...", "Part 2 amends ...") appear as amendment edges in the typed graph?
Amendment edges are built from (a) the target's <history-note> entries and (b) the source's
<schedule.amendments.group2>. A body-text-only amendment would be missed if the target's history
note does not name the source.

For every citation that resolves to a graph node and whose enclosing text says the SOURCE amends it
("<This Act|This Part|This section|These regulations|Schedule N> ... amends [the] <cited Act>"),
check whether an amendment edge source -> target exists. Pairs that have the statement but no
amendment edge are the GAP. Reports the gap by layer, whether the citation edge exists, and examples.

Run from repo root:  python src/body_amendment_gap_audit.py [--layers SG0,...,SG5]
Outputs: outputs/body_amendment_gap/{gap_pairs.json, summary.md}
"""
import argparse, importlib.util, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, "src")
spec = importlib.util.spec_from_file_location("ba", "src/boilerplate_citation_audit.py")
ba = importlib.util.module_from_spec(spec); spec.loader.exec_module(ba)   # reuse extraction + reconcile helpers
normalize, local_name, element_text, raw_path, resolve = ba.normalize, ba.local_name, ba.element_text, ba.raw_path, ba.resolve_citation_m

OUT = Path("outputs/body_amendment_gap"); OUT.mkdir(parents=True, exist_ok=True)
SELF_AMENDS = re.compile(
    r"^\W*(?:This\s+(?:Act|Part|section|subpart|Schedule|clause|order|notice)|These\s+regulations|"
    r"(?:Section|Sections|Part|Subpart|Schedule|Regulation|Regulations)\s+[\dA-Za-z]+(?:\s*(?:to|and|,)\s*[\dA-Za-z]+)*)"
    r"[^.;:]{0,60}?\b(?:amends?|repeals?|revokes?)\b", re.I)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--layers", default="SG0,SG1,SG2,SG3,SG4,SG5")
    layers = set(ap.parse_args().layers.split(","))
    nodes = {normalize(n["id"]): n for n in json.loads(Path("outputs/graph_typed/nodes.json").read_text(encoding="utf-8"))}
    edges = json.loads(Path("outputs/graph_typed/edges.json").read_text(encoding="utf-8"))
    have = defaultdict(set)
    for e in edges: have[(normalize(e["source"]), normalize(e["target"]))].add(e["edge_type"])

    # audit_fix_12: documents merged into one node are still read, and attributed to the merged (canonical) node.
    amap, src_nodes = {}, dict(nodes)
    fx = Path("data/processed/audit_fix_12_node_merges.json")
    if fx.exists():
        for m in json.loads(fx.read_text(encoding="utf-8"))["merges"]:
            ak = normalize(m["alias"]); amap[ak] = normalize(m["canonical"])
            if m["kind"] == "rename": continue
            a = {**m["alias_node"], "id": m["alias"]}
            for f in ("year", "number"):
                a[f] = int(a[f]) if str(a[f]).isdigit() and f == "year" else a[f]
            src_nodes[ak] = a
    docs_read = 0

    stmt = defaultdict(list)       # (source,target) -> example sentences
    for sk0, n in src_nodes.items():
        if n["layer"] not in layers: continue
        p = raw_path(n)
        if p is None or not p.exists(): continue
        try: root = ET.parse(p).getroot()
        except Exception: continue
        docs_read += 1; sk = amap.get(sk0, sk0)
        parent = {c: pp for pp in root.iter() for c in pp}
        last = None
        for el in root.iter():
            ln = local_name(el.tag)
            if ln == "prov": last = None
            if ln != "citation" or el.get("jurisdiction") != "nz": continue
            name, method = resolve(el)
            if name: last = name; tk = normalize(name)
            elif method == "anaphoric" and last: tk = normalize(last)
            else: continue
            tk = amap.get(tk, tk)
            if tk not in nodes or tk == sk: continue
            node, ctx = el, ""
            while node in parent:
                node = parent[node]
                if local_name(node.tag) in ("para", "text", "subprov", "def-para", "label-para"):
                    ctx = element_text(node); break
            if SELF_AMENDS.search(ctx):
                if len(stmt[(sk, tk)]) < 2: stmt[(sk, tk)].append(ctx[:200])

    tot = len(stmt)
    covered = [k for k in stmt if "amendment" in have.get(k, ())]
    gap = [k for k in stmt if "amendment" not in have.get(k, ())]
    rev = [k for k in gap if "amendment" in have.get((k[1], k[0]), ())]
    by_layer = Counter(nodes[k[0]]["layer"] for k in gap); tot_layer = Counter(nodes[k[0]]["layer"] for k in stmt)
    L = []
    def line(s=""): L.append(s); print(s)
    line(f"\n## Body-text amendment statements vs amendment edges (sources in {sorted(layers)})\n")
    line(f"Documents read: **{docs_read}** (raw XML found for the layers requested)\n")
    line(f"Pairs where the source's own text says it amends/repeals/revokes the target: **{tot}**\n")
    line("| Outcome | Pairs | Share |"); line("|---|---|---|")
    line(f"| Amendment edge present | {len(covered)} | {100*len(covered)/max(tot,1):.1f}% |")
    line(f"| **Gap: no amendment edge** | {len(gap)} | {100*len(gap)/max(tot,1):.1f}% |")
    line(f"|   of which only the reverse-direction amendment exists | {len(rev)} | |\n")
    line("| Source layer | Statement pairs | Gap pairs |"); line("|---|---|---|")
    for l in ("SG0", "SG1", "SG2", "SG3", "SG4", "SG5"):
        if tot_layer[l]: line(f"| {l} | {tot_layer[l]} | {by_layer[l]} |")
    line("\n## Examples of gap pairs\n"); line("| Source | Target | Text |"); line("|---|---|---|")
    for k in gap[:15]: line(f"| {nodes[k[0]]['id'][:40]} | {nodes[k[1]]['id'][:40]} | {stmt[k][0][:110]} |")
    (OUT / "gap_pairs.json").write_text(json.dumps(
        [{"source": nodes[k[0]]["id"], "target": nodes[k[1]]["id"], "examples": stmt[k], "edge_types_present": sorted(have.get(k, ()))} for k in gap],
        indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "summary.md").write_text("\n".join(L), encoding="utf-8")

if __name__ == "__main__":
    main()
