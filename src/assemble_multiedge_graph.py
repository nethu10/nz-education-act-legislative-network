"""
assemble_multiedge_graph.py

Combines SG1-SG5 into one multi-edge, directed citation/amendment graph for
Stage 7 (Katz centrality) and Stage 8 (Leiden communities).

Sources (all in data/processed/):
  sg1_final_list.json                  - 37 Acts directly adjacent to the seed
  sg1_internal_amendment_edges.json + sg1_internal_citation_edges.json
                                        - SG1-internal edges (added -- see note below)
  sg2_final_list.json + sg2_internal_links.json
  sg3_final_list.json + sg3_internal_links.json
  sg4_final_list.json + sg4_internal_links.json
  sg5_final_list.json + sg5_internal_links.json (zero internal edges)

FIX (2026-09-30): SG1-internal edges were computed by check_sg1_internal_
amendments.py / check_sg1_internal_citations.py and drawn in
sg1_full_network_diagram.png, but this script's `internal_files` map never
included SG1 -- it only covered SG2-SG5 -- so the assembled graph silently
modeled SG1 as a pure star around the seed even though 119 real SG1-internal
Act pairs were already known. The two SG1 files use a different schema
(direct source/target/count rows) than SG2-SG5's internal_links.json
(act/linked_from rows), so they're folded in as their own block below
rather than added to `internal_files`.

Node identity: raw Act-name strings differ across layers for the same real
Act (trailing "(2011 No 13)", "(SR 2003/153)" style citations, curly vs
straight apostrophes -- the exact variance the pipeline's own audit trail
already documents). Rather than treat every string as a distinct node, this
script folds name variants that differ only in a trailing parenthetical
citation or apostrophe style into one canonical node, reusing the same
TRAILING_PAREN_RE pattern already validated in sg4_step03_resolve_identifiers.py.
Macron folding is NOT applied to node identity (too high a risk of merging
two distinct Acts that happen to share a macron-stripped spelling) -- it's
only used for the identifier-resolution cascade elsewhere, not here.

Edge model (directed): edge(source, target) means "source cites/amends/
contains target" -- i.e. target's "linked_from" list, or SG1's amendment
counts relative to the seed. Every edge keeps its originating layer and
type so later stages can choose how to weight amendment vs citation vs
internal-link edges rather than that choice being made silently here.

Known open question (documented, not resolved here): SG1's "citations"
field direction is assumed seed -> act (an outgoing reference from the
seed's own text), consistent with every other layer's "earlier layer cites
into later layer" convention. This differs from amendments, where the tag
that produced the count (<history-note> vs <schedule.amendments.group2>)
fixes the direction unambiguously. Flagged in the output as
direction_assumed=True on those specific edges so it's easy to find and
confirm/override later.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

DATA = Path("data/processed")
OUT = Path("outputs/graph")
OUT.mkdir(parents=True, exist_ok=True)

SEED = "Education and Training Act 2020"

TRAILING_PAREN_RE = re.compile(r"\s*\((?:[^()]|\([^()]*\))*\)\s*$")
# Same pattern used in sg4_step03_resolve_identifiers.py's FRAGMENT_CITATION_RE,
# reused here so "Schedule 1 of the Resource Management Act 1991" and
# "Part 3 and section 114 of the Legislation Act 2019" fold into their
# parent Act instead of becoming spurious one-off nodes.
FRAGMENT_OF_RE = re.compile(r"^(?:Parts?|Sections?|Schedules?)\b.*?\bof (?:the\s+)?(.+)$", re.IGNORECASE)
CURLY_APOS = "’"
STRAIGHT_APOS = "'"


def normalize_key(name: str) -> str:
    """Folding key used only to GROUP node variants -- not the display name."""
    n = name.strip()
    m = FRAGMENT_OF_RE.match(n)
    if m:
        n = m.group(1).strip()
    # Strip one or more trailing parenthetical citations, and a trailing
    # period left behind (e.g. "... Act 2011 (2011 No 13).").
    prev = None
    while prev != n:
        prev = n
        n = TRAILING_PAREN_RE.sub("", n).strip()
    n = n.rstrip(".").strip()
    n = n.replace(CURLY_APOS, STRAIGHT_APOS)
    n = re.sub(r"\s+", " ", n)
    return n.lower()


def load(name):
    p = DATA / name
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------
# Pass 1: collect every raw name and which layer's final_list it belongs
# to (the layer an Act was DISCOVERED in -- its "act" field in that
# layer's own final_list, not just a mention inside someone else's
# linked_from).
# ---------------------------------------------------------------------
layer_files = {
    "SG1": "sg1_final_list.json",
    "SG2": "sg2_final_list.json",
    "SG3": "sg3_final_list.json",
    "SG4": "sg4_final_list.json",
    "SG5": "sg5_final_list.json",
}
internal_files = {
    "SG2": "sg2_internal_links.json",
    "SG3": "sg3_internal_links.json",
    "SG4": "sg4_internal_links.json",
    "SG5": "sg5_internal_links.json",
}
# SG1-internal edges use a different schema (direct source/target/count
# rows, from two separate files split by relationship type) than
# internal_files' act/linked_from schema, so handled as their own list
# rather than added to internal_files -- see the FIX note above.
SG1_INTERNAL_FILES = [
    "sg1_internal_amendment_edges.json",
    "sg1_internal_citation_edges.json",
]

raw_name_variants = defaultdict(set)   # norm_key -> {raw strings seen}
raw_name_count = defaultdict(lambda: defaultdict(int))  # norm_key -> raw -> count
node_layer = {}  # norm_key -> earliest layer string ("SG0".."SG5")

def register(raw, layer):
    key = normalize_key(raw)
    raw_name_variants[key].add(raw)
    raw_name_count[key][raw] += 1
    if key not in node_layer or layer < node_layer[key]:
        # simple lexical compare works because "SG1" < "SG2" < ... < "SG5"
        node_layer[key] = layer
    return key

seed_key = register(SEED, "SG0")

for layer, fname in layer_files.items():
    for entry in load(fname):
        register(entry["act"], layer)

# also register every linked_from name (some may be earlier-layer names
# already covered, some may be same-layer sideways references -- either
# way they need a canonical key to be usable as an edge endpoint)
for layer, fname in layer_files.items():
    for entry in load(fname):
        for src in entry.get("linked_from", []):
            if normalize_key(src) not in node_layer:
                # a linked_from name that never appears as its own "act"
                # entry anywhere -- register it at the citing layer as a
                # fallback so the edge isn't silently dropped.
                register(src, layer)

for layer, fname in internal_files.items():
    for entry in load(fname):
        register(entry["act"], layer)
        for src in entry.get("linked_from", []):
            if normalize_key(src) not in node_layer:
                register(src, layer)

# SG1-internal source/target names should already be registered (every one
# of the 37 SG1 Acts is registered above via sg1_final_list.json), but
# register defensively in case a name variant slipped through, matching
# the fallback pattern used for internal_files just above.
for fname in SG1_INTERNAL_FILES:
    for entry in load(fname):
        if normalize_key(entry["source"]) not in node_layer:
            register(entry["source"], "SG1")
        if normalize_key(entry["target"]) not in node_layer:
            register(entry["target"], "SG1")


def canonical_name(key):
    """Pick the display name for a node.

    Bug fixed 2026-09-30: this used to be pure frequency + length ("most
    frequently-seen raw form; tie-break on length"), with no bias against
    picking a "Part/Section/Schedule ... of ... " FRAGMENT_OF_RE match as
    the canonical name. That let a schedule/part/section reference
    outvote an Act's own clean name whenever enough OTHER Acts happened to
    cite that specific schedule/part/section -- confirmed against the
    live data to have mislabelled 6 of 2519 nodes, including the SEED
    node itself as "Schedule 9 of the Education and Training Act 2020"
    (should be "Education and Training Act 2020"), plus Crown Entities
    Act 2004, Social Security Act 2018, Legislation Act 2019, and
    Financial Markets Conduct Act 2013 -- all high-combined_score hub
    Acts likely to matter for Katz centrality.

    Fix has two parts:
      1. If ANY non-fragment raw variant was ever registered for this
         key, prefer it outright (by frequency then length among ONLY
         the non-fragment variants), regardless of how often a fragment
         form was seen.
      2. If NO non-fragment variant was ever registered at all (confirmed
         for exactly one node: "Immigration Regulations 1999", which
         only ever appears via "Schedule 1 of the Immigration Regulations
         1999" across sg2_final_list.json / sg2_internal_links.json /
         sg3_final_list.json -- never under its own name) -- fall back to
         algorithmically extracting the Act name from the best fragment
         string, via the same FRAGMENT_OF_RE pattern normalize_key()
         already uses to compute the grouping key. This won't recover a
         citation suffix that was never in any raw string to begin with
         (e.g. the real citation is "Immigration Regulations 1999 (SR
         1999/284)", confirmed against legislation.govt.nz, but "SR
         1999/284" appears nowhere in the source data) -- that's a known,
         accepted residual limit for this one node, not something this
         function can recover on its own.
    """
    counts = raw_name_count[key]
    non_fragment = {r: c for r, c in counts.items() if not FRAGMENT_OF_RE.match(r)}
    if non_fragment:
        return sorted(non_fragment.items(), key=lambda kv: (-kv[1], -len(kv[0])))[0][0]
    best_fragment = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))[0][0]
    m = FRAGMENT_OF_RE.match(best_fragment)
    return m.group(1).strip() if m else best_fragment


# ---------------------------------------------------------------------
# Pass 2: build edges
# ---------------------------------------------------------------------
# edge key: (source_key, target_key, edge_type, layer) -> weight accumulator
edges = defaultdict(lambda: {"weight": 0, "confirmed_internal": False, "direction_assumed": False})

def add_edge(src_raw, tgt_raw, edge_type, layer, weight=1, direction_assumed=False):
    sk = normalize_key(src_raw)
    tk = normalize_key(tgt_raw)
    if sk == tk:
        return  # drop self-loops from name-variant noise
    e = edges[(sk, tk, edge_type, layer)]
    e["weight"] += weight
    e["direction_assumed"] = e["direction_assumed"] or direction_assumed

# SG1: seed <-> each SG1 Act
for entry in load("sg1_final_list.json"):
    act = entry["act"]
    if entry.get("outgoing_amendments"):
        add_edge(SEED, act, "amendment_outgoing", "SG1", entry["outgoing_amendments"])
    if entry.get("incoming_amendments"):
        add_edge(act, SEED, "amendment_incoming", "SG1", entry["incoming_amendments"])
    if entry.get("citations"):
        add_edge(SEED, act, "citation", "SG1", entry["citations"], direction_assumed=True)

# SG1-internal edges (citation + amendment, from check_sg1_internal_*.py).
# Both files give real, tag-derived direction (not assumed) -- amendment
# direction comes straight from <history-note> vs <schedule.amendments.
# group2>, same as every other layer's amendment edges; citation direction
# comes from which Act's XML the <citation> element was found in, same
# convention as every other layer's citation-derived internal_link edges.
# No "confirmed_internal" merge check against final_list_link edges here,
# unlike SG2-SG5: SG1 doesn't have final_list_link edges (its seed-facing
# edges are amendment_outgoing/amendment_incoming/citation instead), so
# there's no risk of double-counting the same pair under two edge types.
for fname in SG1_INTERNAL_FILES:
    for entry in load(fname):
        add_edge(entry["source"], entry["target"], "internal_link", "SG1", entry["count"])

# SG2-SG5 final_list linked_from edges
for layer, fname in layer_files.items():
    if layer == "SG1":
        continue
    for entry in load(fname):
        act = entry["act"]
        for src in entry.get("linked_from", []):
            add_edge(src, act, "final_list_link", layer)

# SG2-SG5 internal_links edges (mark as confirmed_internal; merge into
# existing edge if the (source,target) pair is already present)
for layer, fname in internal_files.items():
    for entry in load(fname):
        act = entry["act"]
        for src in entry.get("linked_from", []):
            sk, tk = normalize_key(src), normalize_key(act)
            if sk == tk:
                continue
            # look for an existing final_list_link edge for this pair in
            # any layer to flag rather than duplicate
            merged = False
            for (esk, etk, etype, elayer), e in edges.items():
                if esk == sk and etk == tk and etype == "final_list_link":
                    e["confirmed_internal"] = True
                    merged = True
                    break
            if not merged:
                add_edge(src, act, "internal_link", layer)

# ---------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------
nodes_out = []
for key, layer in node_layer.items():
    nodes_out.append({
        "id": canonical_name(key),
        "layer": layer,
        "name_variants": sorted(raw_name_variants[key]),
    })
nodes_out.sort(key=lambda n: (n["layer"], n["id"]))

edges_out = []
for (sk, tk, etype, layer), e in edges.items():
    edges_out.append({
        "source": canonical_name(sk),
        "target": canonical_name(tk),
        "edge_type": etype,
        "layer": layer,
        "weight": e["weight"],
        "confirmed_internal": e["confirmed_internal"],
        "direction_assumed": e["direction_assumed"],
    })
edges_out.sort(key=lambda e: (e["layer"], e["source"], e["target"]))

(OUT / "nodes.json").write_text(json.dumps(nodes_out, indent=2, ensure_ascii=False), encoding="utf-8")
(OUT / "edges.json").write_text(json.dumps(edges_out, indent=2, ensure_ascii=False), encoding="utf-8")

with open(OUT / "nodes.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "layer", "n_name_variants"])
    for n in nodes_out:
        w.writerow([n["id"], n["layer"], len(n["name_variants"])])

with open(OUT / "edges.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["source", "target", "edge_type", "layer", "weight", "confirmed_internal", "direction_assumed"])
    for e in edges_out:
        w.writerow([e["source"], e["target"], e["edge_type"], e["layer"], e["weight"], e["confirmed_internal"], e["direction_assumed"]])

# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------
print(f"Nodes: {len(nodes_out)}")
by_layer = defaultdict(int)
for n in nodes_out:
    by_layer[n["layer"]] += 1
for layer in ["SG0", "SG1", "SG2", "SG3", "SG4", "SG5"]:
    print(f"  {layer}: {by_layer.get(layer, 0)}")

collapsed = sum(1 for k, v in raw_name_variants.items() if len(v) > 1)
print(f"\nName-variant groups collapsed into one node: {collapsed}")

print(f"\nEdges: {len(edges_out)}")
by_type = defaultdict(int)
for e in edges_out:
    by_type[e["edge_type"]] += 1
for t, c in sorted(by_type.items(), key=lambda kv: -kv[1]):
    print(f"  {t}: {c}")

confirmed = sum(1 for e in edges_out if e["confirmed_internal"])
assumed = sum(1 for e in edges_out if e["direction_assumed"])
print(f"\nEdges also confirmed by an internal-link scan: {confirmed}")
print(f"Edges with an assumed (not tag-derived) direction: {assumed}")

print(f"\nSaved -> {OUT}/nodes.json, {OUT}/edges.json, {OUT}/nodes.csv, {OUT}/edges.csv")