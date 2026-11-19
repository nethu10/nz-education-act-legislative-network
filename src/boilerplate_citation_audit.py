"""
boilerplate_citation_audit.py

Splits every citation-edge weight in the typed graph into three kinds, by re-running the same
citation extraction as the typed edge builders (leg-title / text-match / anaphoric) and tagging each
counted <citation> occurrence by WHERE it sits and WHAT it says:

  publication_artefact : inside <reprint-note> (cover or end) or <promulgation>/<issue-authority>.
                         Added by the Parliamentary Counsel Office when it publishes a version
                         ("PCO has made editorial and format changes ... under the Legislation Act 2019",
                         "Issued under the authority of the Legislation Act 2019"). Not part of the
                         enacted text; present in every consolidated version.
  drafting_template    : enacted text, but fixed template wording -- "X under this section is
                         secondary legislation (see Part 3 of the Legislation Act 2019 for publication
                         requirements)", the per-section secondary-legislation tables headed
                         "Legislation Act 2019 requirements", "(see subpart 3 of Part 3 of the Legislation Act)".
  substantive          : everything else.

Reconciles against outputs/graph_typed/edges.json (citation weight per pair) for every source it
processed, and reports the decomposition for the most-cited nodes plus how a simple weighted
in-citation ranking changes if the artefact (and artefact+template) weight is removed.

Run from repo root (needs raw XML for the layers you ask for; default all = run on the Mac):
    python src/boilerplate_citation_audit.py [--layers SG0,SG1,SG2,SG3,SG4,SG5]
Outputs: outputs/boilerplate_audit/{pair_counts.json, target_summary.json, summary.md}
"""
import argparse, importlib.util, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, "src")
spec = importlib.util.spec_from_file_location("sb", "src/slm_spotcheck_04_build_sample_typed.py")
sb = importlib.util.module_from_spec(spec); spec.loader.exec_module(sb)   # reuse normalize/raw_path/resolve_citation
normalize, local_name, element_text, raw_path, resolve_citation = (
    sb.normalize, sb.local_name, sb.element_text, sb.raw_path, sb.resolve_citation)

OUT = Path("outputs/boilerplate_audit"); OUT.mkdir(parents=True, exist_ok=True)
ARTEFACT_TAGS = {"reprint-note", "reprint.notes", "cover.reprint-note", "end.reprint-note", "promulgation", "issue-authority"}
TEMPLATE_RE = re.compile(
    r"secondary legislation\s*\(see\b|grouped under the heading|publication requirements|"
    r"\(see (?:Part|subpart|section)[^)]{0,40}(?:Legislation Act|Acts and Regulations Publication Act)", re.I)


ACT_NAME_PATTERN = re.compile(
    r"of\s+(?:Part\s+\S+\s+of\s+)?(?:the\s+)?"
    r"([A-Z][A-Za-z0-9,’'\-\(\) ]*?\b(?:Act|Rules?|Regulations?|Order|Notice|Bylaw)\s+\d{4})\b")


def resolve_citation_m(cit_el):
    """verbatim copy of resolve_citation() in sg5_step01_build_typed_edges.py (returns name, method)."""
    leg_title, has_extref = None, False
    for child in cit_el.iter():
        ln = local_name(child.tag)
        if ln == "leg-title" and leg_title is None: leg_title = child
        elif ln == "extref": has_extref = True
    if leg_title is not None: return element_text(leg_title), "leg_title"
    if not has_extref: return None, "internal_only"
    full_text = element_text(cit_el)
    if re.search(r"\bthis Act\b", full_text): return None, "self"
    m = ACT_NAME_PATTERN.search(full_text)
    if m: return m.group(1).strip(), "text_match"
    if re.search(r"\bthat Act\b", full_text) or re.search(r"\bthe Act\b", full_text): return None, "anaphoric"
    return None, "unresolved"


def kind_of(chain, ctx):
    if any(t in ARTEFACT_TAGS for t in chain): return "publication_artefact"
    if TEMPLATE_RE.search(ctx or ""): return "drafting_template"
    return "substantive"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--layers", default="SG0,SG1,SG2,SG3,SG4,SG5")
    ap.add_argument("--remap-existing", default=None, help="path to a pre-audit_fix_12 pair_counts.json: re-key it through the audit_fix_12 merge map instead of re-reading the XML (use when the raw XML of some layers is not available)")
    _a = ap.parse_args(); layers = set(_a.layers.split(","))
    nodes = {normalize(n["id"]): n for n in json.loads(Path("outputs/graph_typed/nodes.json").read_text(encoding="utf-8"))}
    edges = json.loads(Path("outputs/graph_typed/edges.json").read_text(encoding="utf-8"))
    graph_w = {(normalize(e["source"]), normalize(e["target"])): e["weight"] for e in edges if e["edge_type"] == "citation"}

    # audit_fix_12: documents that were merged into one node are still read, and attributed to the merged node.
    amap, src_nodes = {}, dict(nodes)
    fx = Path("data/processed/audit_fix_12_node_merges.json")
    if fx.exists():
        for m in json.loads(fx.read_text(encoding="utf-8"))["merges"]:
            ak = normalize(m["alias"])
            if m["kind"] == "rename": amap[ak] = normalize(m["canonical"]); continue
            amap[ak] = normalize(m["canonical"])
            a = {**m["alias_node"], "id": m["alias"]}
            for f in ("year", "number"):
                a[f] = int(a[f]) if str(a[f]).isdigit() and f == "year" else a[f]
            src_nodes[ak] = a

    pair0 = defaultdict(Counter); processed = set(); parse_fail = 0
    if _a.remap_existing:
        for r in json.loads(Path(_a.remap_existing).read_text(encoding="utf-8")):
            sk, t = normalize(r["source"]), normalize(r["target"]); t = amap.get(t, t)
            if t == amap.get(sk, sk): continue
            pair0[(sk, t)].update({k: r[k] for k in ("publication_artefact", "drafting_template", "substantive") if k in r})
            processed.add(amap.get(sk, sk))
    for sk, n in ([] if _a.remap_existing else src_nodes.items()):
        if n["layer"] not in layers: continue
        p = raw_path(n)
        if p is None or not p.exists(): continue
        try: root = ET.parse(p).getroot()
        except Exception: parse_fail += 1; continue
        processed.add(amap.get(sk, sk))
        parent = {c: pp for pp in root.iter() for c in pp}
        last_named = None
        for el in root.iter():
            ln = local_name(el.tag)
            if ln == "prov": last_named = None
            if ln != "citation" or el.get("jurisdiction") != "nz": continue
            name, method = resolve_citation_m(el)       # identical logic to the typed edge builders
            target = None
            if name:
                target = normalize(name); last_named = name
            elif method == "anaphoric" and last_named:
                target = normalize(last_named)
            if target is not None: target = amap.get(target, target)
            if target is None or target not in nodes or target == amap.get(sk, sk): continue
            chain, x = [], el
            while x in parent: x = parent[x]; chain.append(local_name(x.tag))
            ctx, node = "", el
            while node in parent:
                node = parent[node]
                if local_name(node.tag) in ("para", "text", "subprov", "def-para", "label-para"):
                    ctx = element_text(node); break
            pair0[(sk, target)][kind_of(chain, ctx)] += 1

    # same merge policy as the graph: several original documents of one merged node -> keep the larger per target
    best = {}
    for (sk, t), c in pair0.items():
        k = (amap.get(sk, sk), t)
        if k not in best or sum(c.values()) > sum(best[k].values()): best[k] = c
    pair = defaultdict(Counter, best)

    # reconcile with the graph for processed sources
    mism = [(k, sum(v.values()), graph_w.get(k)) for k, v in pair.items() if graph_w.get(k) != sum(v.values())]
    missing = [(k, w) for k, w in graph_w.items() if k[0] in processed and k not in pair]
    n_pairs = sum(1 for k in graph_w if k[0] in processed)
    print(f"Processed {len(processed)} source documents (parse failures: {parse_fail}); graph citation pairs from them: {n_pairs}")
    print(f"Reconciliation: pairs with different weight: {len(mism)}; graph pairs not reproduced: {len(missing)}")
    for k, mine, g in mism[:5]: print("   mismatch", k, "mine", mine, "graph", g)

    # per-target decomposition (only fully valid if all layers were processed)
    tgt = defaultdict(Counter)
    for (s, t), c in pair.items(): tgt[t].update(c)
    rows = []
    for t, c in tgt.items():
        tot = sum(c.values())
        rows.append({"target": nodes[t]["id"], "layer": nodes[t]["layer"], "total": tot,
                     "publication_artefact": c["publication_artefact"], "drafting_template": c["drafting_template"],
                     "substantive": c["substantive"],
                     "non_substantive_share": round((c["publication_artefact"] + c["drafting_template"]) / tot, 3)})
    rows.sort(key=lambda r: -r["total"])
    (OUT / "pair_counts.json").write_text(json.dumps(
        [{"source": nodes[s]["id"], "target": nodes[t]["id"], **dict(c), "total": sum(c.values())} for (s, t), c in pair.items()],
        indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "target_summary.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")

    L = []
    def line(s=""): L.append(s); print(s)
    tot = Counter(); [tot.update(c) for c in pair.values()]
    T = sum(tot.values())
    line("\n## Citation weight by kind (all processed sources)\n")
    line("| Kind | Weight | Share |"); line("|---|---|---|")
    for k in ("publication_artefact", "drafting_template", "substantive"):
        line(f"| {k} | {tot[k]:,} | {100*tot[k]/T:.1f}% |")
    line(f"| **total** | {T:,} | |\n")
    line("## Most-cited targets: how much is boilerplate?\n")
    line("| Target | Layer | Total | Artefact | Template | Substantive | Non-substantive |"); line("|---|---|---|---|---|---|---|")
    for r in rows[:15]:
        line(f"| {r['target']} | {r['layer']} | {r['total']:,} | {r['publication_artefact']:,} | {r['drafting_template']:,} | {r['substantive']:,} | {100*r['non_substantive_share']:.0f}% |")
    def rank(key):
        w = Counter()
        for t, c in tgt.items(): w[t] = key(c)
        return [t for t, _ in w.most_common(15)]
    base, no_art, subst = rank(lambda c: sum(c.values())), rank(lambda c: c["drafting_template"] + c["substantive"]), rank(lambda c: c["substantive"])
    line("\n## Top-15 targets by incoming citation weight, under three treatments\n")
    line("| Rank | All citations | Without publication artefacts | Substantive only |"); line("|---|---|---|---|")
    for i in range(15): line(f"| {i+1} | {nodes[base[i]]['id']} | {nodes[no_art[i]]['id']} | {nodes[subst[i]]['id']} |")
    (OUT / "summary.md").write_text("\n".join(L), encoding="utf-8")
    print("\nSaved -> outputs/boilerplate_audit/")

if __name__ == "__main__":
    main()
