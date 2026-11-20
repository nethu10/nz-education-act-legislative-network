"""
make_sg4_internal_diagram.py

SG4-internal hub/density diagram -- the same style of view
make_sg3_internal_diagram.py gave you for SG3, now for SG4: which SG4
Acts get cited/amended by other SG4 Acts most, drawn as a network.

Source data: data/processed/sg4_internal_links.json, written by
sg4_step06_find_sg4_internal_links.py (134 distinct SG4-internal
targets on the confirmed run). Expected shape: a list of dicts with
"act"/"combined_score"/"linked_from" fields (or an equivalent dict-of-
dicts keyed by Act name) -- this script auto-detects the field names
the same way make_sg3_internal_diagram.py does, and prints the real
structure of the first entry if none of the likely key names match.

With 1,135 SG4 Acts but only 134 of them a target of an internal
reference, drawing every node/edge label would still be unreadable, so
the same approach as SG3's diagram applies:
  - every node/edge is still drawn (full structure preserved)
  - only the top N hub Acts (by score) get a text label
  - node size + color scale with score (SG4-internal references received)
  - edges are thin and low-alpha so the hub/periphery pattern reads
    clearly instead of producing visual noise
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

try:
    from adjustText import adjust_text
    HAVE_ADJUST_TEXT = True
except ImportError:
    HAVE_ADJUST_TEXT = False

LINKS_PATH = Path("data/processed/sg4_internal_links.json")
OUTPUT_PATH = Path("outputs/figures/sg4_internal_diagram.png")
TOP_N_LABELS = 25

with open(LINKS_PATH, encoding="utf-8") as f:
    links = json.load(f)

# Normalize into a list of dicts regardless of whether the file is a
# dict-of-dicts (keyed by Act name) or already a list of dicts.
if isinstance(links, dict):
    raw_entries = [{"act": k, **v} for k, v in links.items()]
else:
    raw_entries = links

if not raw_entries:
    raise SystemExit(f"{LINKS_PATH} is empty -- nothing to draw.")

sample = raw_entries[0]
name_key = next((k for k in ("act", "name", "target", "title") if k in sample), None)
score_key = next((k for k in ("combined_score", "score", "total_score", "weight") if k in sample), None)
from_key = next((k for k in ("linked_from", "from_acts", "sources", "citing_acts", "from") if k in sample), None)

if not (name_key and score_key and from_key):
    raise SystemExit(
        "Couldn't recognize the field names in sg4_internal_links.json.\n"
        f"First entry looks like:\n{json.dumps(sample, indent=2, ensure_ascii=False)[:800]}\n\n"
        "Paste this back and I'll fix the NAME_KEY/SCORE_KEY/FROM_KEY names above."
    )

print(f"Using fields: name={name_key!r}, score={score_key!r}, from={from_key!r}")

G = nx.DiGraph()
for entry in raw_entries:
    target = entry[name_key]
    score = entry.get(score_key, 0)
    sources = entry.get(from_key) or []
    if target not in G:
        G.add_node(target, score=score)
    else:
        G.nodes[target]["score"] = score
    for src in sources:
        if src not in G:
            G.add_node(src, score=0)
        G.add_edge(src, target)

print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# Score = SG4-internal references received. Fall back to in-degree if a
# node's own "score" field is missing/zero (e.g. source-only nodes).
in_strength = dict(G.in_degree())
node_score = {n: (G.nodes[n].get("score") or 0) or in_strength.get(n, 0) for n in G.nodes}

top_hubs = sorted(node_score, key=node_score.get, reverse=True)[:TOP_N_LABELS]

# Spring layout pulls hubs toward the centre and periphery nodes
# outward -- exactly the pattern worth seeing here. A bigger k gives
# nodes more repulsion so the dense hub cluster spreads out instead of
# collapsing into an unreadable knot (same tuning as the SG3 diagram).
pos = nx.spring_layout(G, k=0.6, iterations=100, seed=42)

max_score = max(node_score.values()) or 1
node_sizes = [40 + 900 * (node_score[n] / max_score) ** 0.5 for n in G.nodes]
node_colors = [node_score[n] for n in G.nodes]

fig, ax = plt.subplots(figsize=(11, 11))

nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#999999", alpha=0.12, arrows=False, width=0.6)

nodes = nx.draw_networkx_nodes(
    G, pos, ax=ax,
    node_size=node_sizes,
    node_color=node_colors,
    cmap=plt.cm.viridis,
    linewidths=0,
)

# Labels as separate text objects (not nx.draw_networkx_labels) so
# adjustText can nudge overlapping ones apart and draw a thin leader
# line back to the actual node position.
texts = []
for n in top_hubs:
    x, y = pos[n]
    label = n if len(n) <= 50 else n[:47] + "..."
    texts.append(ax.text(x, y, label, fontsize=9, fontweight="bold", zorder=5))

if HAVE_ADJUST_TEXT:
    adjust_text(
        texts,
        ax=ax,
        expand_points=(1.6, 1.8),
        force_text=(0.4, 0.6),
        arrowprops=dict(arrowstyle="-", color="#555555", lw=0.6, alpha=0.8),
    )
else:
    print(
        "\nNOTE: adjustText isn't installed, so hub labels may still overlap "
        "in the dense cluster. Run: pip install adjustText, then re-run this "
        "script for clean, non-overlapping labels."
    )

ax.set_title(
    f"SG4-internal citation/amendment network\n"
    f"{G.number_of_nodes()} SG4 Acts, {G.number_of_edges()} internal edges "
    f"(top {TOP_N_LABELS} hubs labelled)",
    fontsize=13,
)
ax.axis("off")
plt.colorbar(nodes, ax=ax, shrink=0.6, label="Hub score (SG4-internal references received)")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
plt.tight_layout()
plt.savefig(OUTPUT_PATH, dpi=300, bbox_inches="tight", pad_inches=0.05)
plt.savefig(str(OUTPUT_PATH).replace(".png", ".pdf"), bbox_inches="tight", pad_inches=0.05)
print(f"\nSaved -> {OUTPUT_PATH}")

print(f"\nTop {TOP_N_LABELS} hubs (for reference):")
for n in top_hubs:
    print(f"  {n}  (score {node_score[n]})")