"""
check_sg4_sg5_cleaned_count.py

Second step of the SG4/SG5 citation check. Takes the raw 'extra instruments'
(those that would have reached the cutoff of 6 if citations were counted) and
applies the project's own cleaning ideas to remove names that are not new
instruments. Diagnostic only; changes no existing file.

Each extra is placed in exactly one group, in this order:
  already_in_graph      name matches a node in the frozen graph (any layer)
  not_an_instrument     no 4-digit year in the name (e.g. "Act", "Treaty of Waitangi")
  part_of_existing      "Schedule 7 of the X Act 2002" etc. where X is in the graph
  part_of_other         a part/schedule of an Act not in the graph (kept, flagged)
  fragment_of_existing  name is the tail of a longer node name
                        (e.g. "Drugs Act 1975" in "Misuse of Drugs Act 1975")
  clean                 none of the above: treated as a plausible new instrument

Run from the project root (after check_sg4_sg5_citation_effect.py is in src/):
    python src/check_sg4_sg5_cleaned_count.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_sg4_sg5_citation_effect as base

YEAR = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
PART = re.compile(r"^(?:Schedules?|Parts?|Sections?|Clauses?|Regulations?|Rules?)\b.*?\bof (?:the )?(.+)$",
                  re.IGNORECASE)

nodes = json.load(open("outputs/graph_typed/nodes.json", encoding="utf-8"))
graph_names = {}
for n in nodes:
    graph_names[base.normalize(n["id"])] = n["layer"]
lower_names = {k.lower(): k for k in graph_names}


def classify(c):
    if c in graph_names:
        return "already_in_graph", graph_names[c]
    if not YEAR.search(c):
        return "not_an_instrument", ""
    m = PART.match(c)
    if m:
        parent = base.resolve_canonical(m.group(1).strip())
        if parent in graph_names:
            return "part_of_existing", graph_names[parent]
        return "part_of_other", parent
    cl = c.lower()
    for k_low, k in lower_names.items():
        if len(k_low) > len(cl) and k_low.endswith(" " + cl):
            return "fragment_of_existing", k
    return "clean", ""


results = {}
for layer in ("sg4", "sg5"):
    r = base.run(layer)
    groups = Counter()
    rows = []
    for x in r["all"]:
        g, note = classify(x["act"])
        groups[g] += 1
        rows.append(dict(x, group=g, note=note))
    clean = [x for x in rows if x["group"] == "clean"]
    flagged = [x for x in rows if x["group"] == "part_of_other"]
    print("\n" + "-" * 70)
    print(f"{layer.upper()} CLEANED COUNT")
    print(f"  amendment-only layer: {r['amendment_only']}")
    print(f"  raw extras:           {r['extra']}")
    for g in ("already_in_graph", "not_an_instrument", "part_of_existing",
              "part_of_other", "fragment_of_existing", "clean"):
        print(f"    {g:22s} {groups[g]}")
    print(f"  CLEAN extras: {len(clean)}  "
          f"({100*len(clean)/max(1,r['amendment_only']):.1f}% of the amendment-only layer); "
          f"of these, citation-only (no amendment link): {sum(1 for x in clean if x['amendment']==0)}")
    print(f"  CLEAN + part_of_other (upper end): {len(clean)+len(flagged)}")
    print("  --- every group except 'clean' (check the grouping is right) ---")
    for x in rows:
        if x["group"] != "clean":
            print(f"    [{x['group']}] {x['act'][:62]:62s} A={x['amendment']:>3} C={x['citation']:>3} -> {x['note']}")
    print("  --- all CLEAN extras ---")
    for x in clean:
        print(f"    {x['act'][:70]:70s} A={x['amendment']:>3} C={x['citation']:>3} src={x['citing_sources']}")
    results[layer] = dict(summary=dict(groups), clean=clean, flagged=flagged, rows=rows)

with open("outputs/sg4_sg5_cleaned_count.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\nSaved -> outputs/sg4_sg5_cleaned_count.json")
