"""
audit_sg1_sg2_sg3_completeness.py

A direct completeness/integrity check across SG1, SG2, and SG3 before
building further on top of them -- prompted by realizing the
"Maori Trustee Act 1953" / macron-duplicate issue spotted while
building the SG3 diagram was never actually fixed, just noted.

For each layer, tries several likely file paths (I don't have SG1's
file names confirmed in this sandbox -- no sg1_step*.py exists here,
so this is written defensively and will report exactly what it can
and can't find rather than assuming).

Checks, per layer:
  1. Final list count.
  2. Identifier resolution rate, if an identifiers file exists.
  3. XML availability rate, if that field exists (only SG3 has had
     this documented so far -- SG1/SG2 may have the same agency-drafted
     gap, just never checked).
  4. NEAR-DUPLICATE Act names within the layer, using normalization
     (macron-stripped, apostrophe-normalized, case/whitespace-folded)
     -- this is the check that would have caught the Maori Trustee Act
     1953 duplicate before it slipped through.

Across all layers found:
  5. CROSS-LAYER duplicates -- any Act name (normalized) appearing in
     more than one layer, which shouldn't happen by construction
     (each layer's candidates are supposed to be new/outside the
     previous layers) but is worth confirming rather than assuming.

Writes nothing -- diagnostic only, so we know exactly what (if
anything) needs fixing before SG4 identifier resolution continues.
"""
import json
import re
import unicodedata
from pathlib import Path

LAYER_CANDIDATES = {
    "SG1": [
        "data/processed/sg1_final_list.json",
        "data/processed/sg1_candidates.json",
        "data/processed/seed_sg1_final_list.json",
    ],
    "SG2": [
        "data/processed/sg2_final_list.json",
    ],
    "SG3": [
        "data/processed/sg3_final_list.json",
    ],
}

IDENTIFIER_CANDIDATES = {
    "SG1": ["data/processed/sg1_act_identifiers.json"],
    "SG2": ["data/processed/sg2_act_identifiers.json"],
    "SG3": ["data/processed/sg3_act_identifiers.json"],
}

MACRON_MAP = str.maketrans("\u0101\u0113\u012b\u014d\u016b\u0100\u0112\u012a\u014c\u016a", "aeiouAEIOU")
CURLY_APOS = "\u2019"


def normalize(name):
    """Fold a name down to a comparison key: macrons stripped, curly/
    straight apostrophes unified and removed, whitespace collapsed,
    lowercased. Two names that normalize the same are very likely the
    same real-world Act."""
    n = name.translate(MACRON_MAP)
    n = n.replace(CURLY_APOS, "'").replace("'", "")
    n = unicodedata.normalize("NFKD", n)
    n = re.sub(r"\s+", " ", n).strip().lower()
    return n


def find_first_existing(paths):
    for p in paths:
        pp = Path(p)
        if pp.exists():
            return pp
    return None


def load_names(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return list(data.keys())
    names = []
    for entry in data:
        if isinstance(entry, str):
            names.append(entry)
        elif isinstance(entry, dict):
            for key in ("act", "name", "title"):
                if key in entry:
                    names.append(entry[key])
                    break
    return names


print("=" * 70)
print("PER-LAYER STATUS")
print("=" * 70)

layer_names = {}

for layer, candidates in LAYER_CANDIDATES.items():
    path = find_first_existing(candidates)
    print(f"\n{layer}:")
    if not path:
        print(f"  !! No final-list file found among: {candidates}")
        print(f"     (tell me the real path and I'll re-run against it)")
        continue

    names = load_names(path)
    layer_names[layer] = names
    print(f"  Final list: {path} -- {len(names)} Acts")

    id_path = find_first_existing(IDENTIFIER_CANDIDATES.get(layer, []))
    if id_path:
        with open(id_path, encoding="utf-8") as f:
            identifiers = json.load(f)
        n_resolved = sum(1 for d in identifiers if d.get("resolved"))
        print(f"  Identifiers: {id_path} -- {n_resolved}/{len(identifiers)} resolved "
              f"({100 * n_resolved / len(identifiers):.1f}%)" if identifiers else "  Identifiers file is empty")

        has_xml_field = any("xml_available" in d for d in identifiers)
        if has_xml_field:
            n_xml = sum(1 for d in identifiers if d.get("resolved") and d.get("xml_available", True))
            print(f"  XML available: {n_xml}/{n_resolved} of resolved Acts")
        else:
            n_agency = sum(1 for d in identifiers if d.get("subtype") == "agency-drafted")
            if n_agency:
                print(f"  !! {n_agency} agency-drafted entries found but xml_available was never "
                      f"checked for this layer -- same gap SG3 had before step33/34.")
            else:
                print(f"  (no agency-drafted entries found in {layer} -- xml_available check not needed)")

        n_unresolved = len(identifiers) - n_resolved
        if n_unresolved:
            print(f"  Still unresolved ({n_unresolved}):")
            for d in identifiers:
                if not d.get("resolved"):
                    print(f"    {d['act']!r}")
    else:
        print(f"  No identifiers file found among: {IDENTIFIER_CANDIDATES.get(layer, [])}")

print("\n" + "=" * 70)
print("WITHIN-LAYER NEAR-DUPLICATE CHECK (macron/apostrophe/whitespace-normalized)")
print("=" * 70)

any_dupes = False
for layer, names in layer_names.items():
    by_norm = {}
    for n in names:
        by_norm.setdefault(normalize(n), []).append(n)
    dupes = {k: v for k, v in by_norm.items() if len(v) > 1}
    print(f"\n{layer}: {len(dupes)} near-duplicate group(s) found" + (" -- NONE, clean" if not dupes else ""))
    for norm_key, variants in dupes.items():
        any_dupes = True
        print(f"  {variants}")

print("\n" + "=" * 70)
print("CROSS-LAYER DUPLICATE CHECK (same Act appearing in more than one layer)")
print("=" * 70)

norm_to_layers = {}
for layer, names in layer_names.items():
    for n in names:
        norm_to_layers.setdefault(normalize(n), set()).add(layer)

cross_dupes = {k: v for k, v in norm_to_layers.items() if len(v) > 1}
if cross_dupes:
    any_dupes = True
    print(f"\n{len(cross_dupes)} Act(s) appear in more than one layer:")
    for norm_key, layers in cross_dupes.items():
        print(f"  {norm_key!r} -- in {sorted(layers)}")
else:
    print("\nNone found -- layers are cleanly disjoint.")

print("\n" + "=" * 70)
if any_dupes:
    print("ACTION NEEDED: duplicate(s) found above. Paste this output back and I'll build")
    print("a targeted merge/cleanup script, the same way the Court/Courts and 2025")
    print("companion-Act duplicates were fixed for SG3 (steps 20/28).")
else:
    print("No duplicates found in what this script could check.")
print("=" * 70)