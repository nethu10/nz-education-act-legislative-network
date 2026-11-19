"""
audit_fix_02_lookup_cross_layer_names.py

audit_fix_01's CROSS_LAYER_REMOVE_FROM_SG3 list used names guessed from
the audit's NORMALIZED (lowercased, macron-stripped) output, which
didn't match the actual stored text -- both removals came back "NOT
FOUND". This finds the real raw strings (in both SG2 and SG3) by
re-running the same normalization match, so we know the exact text to
target next.

Writes nothing -- just prints the real entries for both known
cross-layer duplicates so the removal can be re-run with exact names.
"""
import json
import re
import unicodedata
from pathlib import Path

SG2_FINAL = Path("data/processed/sg2_final_list.json")
SG3_FINAL = Path("data/processed/sg3_final_list.json")

MACRON_MAP = str.maketrans("\u0101\u0113\u012b\u014d\u016b\u0100\u0112\u012a\u014c\u016a", "aeiouAEIOU")
CURLY_APOS = "\u2019"

TARGETS_NORMALIZED = [
    "pae ora (disestablishment of maori health authority) amendment act 2024",
    "employment services and income support (integrated administration) act 1998",
]


def normalize(name):
    n = name.translate(MACRON_MAP)
    n = n.replace(CURLY_APOS, "'").replace("'", "")
    n = unicodedata.normalize("NFKD", n)
    n = re.sub(r"\s+", " ", n).strip().lower()
    return n


with open(SG2_FINAL, encoding="utf-8") as f:
    sg2 = json.load(f)
with open(SG3_FINAL, encoding="utf-8") as f:
    sg3 = json.load(f)

for target in TARGETS_NORMALIZED:
    print("=" * 70)
    print(f"Target (normalized): {target!r}")
    print("=" * 70)
    for layer_name, entries in [("SG2", sg2), ("SG3", sg3)]:
        for e in entries:
            act = e.get("act", "")
            if normalize(act) == target:
                print(f"  [{layer_name}] raw act = {act!r}")
                print(f"          full entry = {json.dumps(e, ensure_ascii=False)}")
    print()