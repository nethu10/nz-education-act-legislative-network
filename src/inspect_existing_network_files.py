"""
Structural inspection of pre-existing network/relationship files in
data/processed, to check whether SG1-internal (Act-to-Act, not just
Act-to-seed) amendment connectivity has already been computed somewhere
in an earlier pipeline stage, before building anything new from
scratch.

Prints type/shape/sample info only -- not full dumps -- since several
of these files are large.
"""
import json
import pickle
from pathlib import Path

PROCESSED = Path("data/processed")

FILES_TO_CHECK = [
    "stage5_graph.json",
    "stage6_target_acts.json",
    "stage6_target_acts_summary.json",
    "stage6_expansion_summary.json",
    "stage7_katz_amendment_network.json",
    "stage7_katz_internal_network.json",
    "external_acts_relationship_master.json",
    "amendment_relationships_typed.json",
    "amendment_records.json",
    "outgoing_amendments.json",
    "citation_relationships_final.json",
]

def summarize(obj, depth=0, max_items=5):
    indent = "  " * depth
    if isinstance(obj, dict):
        print(f"{indent}dict with {len(obj)} keys: {list(obj.keys())[:15]}")
        for k in list(obj.keys())[:max_items]:
            print(f"{indent}  key '{k}' ->")
            summarize(obj[k], depth + 2, max_items=2)
    elif isinstance(obj, list):
        print(f"{indent}list with {len(obj)} items")
        for item in obj[:max_items]:
            summarize(item, depth + 1, max_items=2)
    else:
        s = repr(obj)
        print(f"{indent}{type(obj).__name__}: {s[:200]}")

for fname in FILES_TO_CHECK:
    path = PROCESSED / fname
    print("=" * 100)
    print(fname)
    print("=" * 100)
    if not path.exists():
        print("  (not found)")
        continue
    try:
        with open(path) as f:
            data = json.load(f)
        summarize(data)
    except Exception as e:
        print(f"  Failed to load as JSON: {e}")
    print()

# Also peek at the pickle (may contain a networkx graph object directly)
pkl_path = PROCESSED / "stage5_graph.pickle"
print("=" * 100)
print("stage5_graph.pickle")
print("=" * 100)
if pkl_path.exists():
    try:
        with open(pkl_path, "rb") as f:
            obj = pickle.load(f)
        print(f"Type: {type(obj)}")
        try:
            import networkx as nx
            if isinstance(obj, (nx.Graph, nx.DiGraph)):
                print(f"Nodes: {obj.number_of_nodes()}  Edges: {obj.number_of_edges()}")
                print("Sample nodes:", list(obj.nodes())[:5])
                print("Sample edges:", list(obj.edges())[:5])
        except ImportError:
            pass
    except Exception as e:
        print(f"  Failed to load pickle: {e}")
else:
    print("  (not found)")