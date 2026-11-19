"""
sg2_step25_reconcile_sg3_identifiers.py

Housekeeping pass, run once identifier resolution has stabilised.
sg2_step20_deduplicate_sg3_court_variants.py merged 3 Court/Courts naming
variants in sg3_final_list.json and sg3_combined_final_list.json
(904 -> 901 Acts), but deliberately left sg3_act_identifiers.json alone --
its docstring flagged this explicitly, pending exactly this check. As a
result sg3_act_identifiers.json still has 904 rows: the 3 canonical Acts
plus their now-merged-away variant names, each with its own independent
resolution attempt across every pass so far. Every "X/901 resolved"
summary printed by steps 21-24 was actually computed against this stale
904-row file (using 901 only as the denominator label, taken from
sg3_final_list.json's length) -- so the true resolved count needs
recomputing here too.

  Family Court Act 1980     <- Family Courts Act 1980
  District Court Rules 2014 <- District Courts Rules 2014
  Family Court Rules 2002   <- Family Courts Rules 2002

For each pair: if both sides resolved, confirms (and prints) whether they
landed on the same (type, year, number) -- the original open question from
step20. Keeps the canonical entry's identifier if it's resolved; otherwise
promotes the variant's identifier onto the canonical name if THAT resolved
instead; drops the variant row either way. Finally drops any other
orphaned entries (names no longer present in sg3_final_list.json) as a
safety net, and recomputes resolved/total against the real 901.
"""
import json
from pathlib import Path

SG3_PATH = Path("data/processed/sg3_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")

MERGE_PAIRS = [
    ("Family Court Act 1980", "Family Courts Act 1980"),
    ("District Court Rules 2014", "District Courts Rules 2014"),
    ("Family Court Rules 2002", "Family Courts Rules 2002"),
]

with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

canonical_names = {c["act"] for c in sg3}
by_act = {d["act"]: d for d in identifiers}

print(f"{IDENTIFIERS_PATH}: {len(identifiers)} entries before "
      f"({len(canonical_names)} canonical SG3 Acts)\n")

dropped = []

for canonical, variant in MERGE_PAIRS:
    c_entry = by_act.get(canonical)
    v_entry = by_act.get(variant)

    if c_entry is None or v_entry is None:
        print(f"  {canonical!r} / {variant!r}: one or both entries missing, skipping")
        continue

    c_resolved = c_entry.get("resolved")
    v_resolved = v_entry.get("resolved")

    if c_resolved and v_resolved:
        same = (
            c_entry.get("type") == v_entry.get("type")
            and c_entry.get("year") == v_entry.get("year")
            and c_entry.get("number") == v_entry.get("number")
        )
        status = "SAME identifier (confirmed)" if same else "DIFFERENT identifiers (!) -- check by hand"
        print(f"  {canonical!r}: {c_entry.get('type')}/{c_entry.get('year')}/{c_entry.get('number')}")
        print(f"  {variant!r}: {v_entry.get('type')}/{v_entry.get('year')}/{v_entry.get('number')}")
        print(f"    -> {status}")
    elif c_resolved and not v_resolved:
        print(f"  {canonical!r}: resolved ({c_entry.get('type')}/{c_entry.get('year')}/{c_entry.get('number')}); "
              f"{variant!r} was never resolved -- keeping canonical's identifier")
    elif v_resolved and not c_resolved:
        print(f"  {canonical!r}: was unresolved; promoting {variant!r}'s identifier "
              f"({v_entry.get('type')}/{v_entry.get('year')}/{v_entry.get('number')}) onto it")
        promoted = {k: v for k, v in v_entry.items() if k != "act"}
        c_entry.update(promoted)
        c_entry["resolved_via"] = (c_entry.get("resolved_via") or "")
        c_entry["note"] = (c_entry.get("note", "") + " " if c_entry.get("note") else "") + \
            f"Identifier promoted from merged-away variant name {variant!r} (sg2_step25)."
    else:
        print(f"  {canonical!r} / {variant!r}: neither resolved -- nothing to promote")

    del by_act[variant]
    dropped.append(variant)
    print()

# Safety net: drop any other orphaned names not present in the 901-Act
# final list (shouldn't be any beyond the 3 above, but don't silently
# carry stale rows forward if there are).
extra_orphans = [name for name in by_act if name not in canonical_names]
for name in extra_orphans:
    print(f"  Also dropping orphaned entry not in sg3_final_list.json: {name!r}")
    del by_act[name]
dropped.extend(extra_orphans)

new_identifiers = [by_act[c["act"]] for c in sg3 if c["act"] in by_act]
missing = [c["act"] for c in sg3 if c["act"] not in by_act]

with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(new_identifiers, f, indent=2, ensure_ascii=False)

n_resolved = sum(1 for d in new_identifiers if d.get("resolved"))
print(f"{IDENTIFIERS_PATH}: {len(new_identifiers)} entries after "
      f"(dropped {len(dropped)}: {dropped})")
if missing:
    print(f"  WARNING: {len(missing)} canonical Acts have no identifiers entry at all: {missing}")
print(f"\nTrue overall: {n_resolved}/{len(sg3)} resolved ({n_resolved/len(sg3):.1%})")
print(f"Saved -> {IDENTIFIERS_PATH}")