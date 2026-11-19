"""
sg2_step32_remove_transport_notice.py

Fixes a name mismatch in step31: the Transport Notice's SG3 candidate
name was never renamed by step22/step23 (those scripts only transformed
the SEARCH QUERY, not the stored name), so it's still carrying its full
original trailing citation suffix:

  'Transport (Driving Hours Logbook Exemption) Notice 2003 ( Gazette 2003 p 2689)'

step31 targeted the bare title without that suffix, so it matched and
removed "Health Reforms (Transitional Provisions) Act 1993" (901 -> 900)
but silently missed this one -- it's the single remaining unresolved
entry in sg3_act_identifiers.json (899/900). This removes it with the
exact stored name, same justification as recorded in step31/
sg3_manual_exclusions.json (confirmed real document, out of pipeline
scope -- NZ Gazette, no PCO XML available).
"""
import json
from pathlib import Path

SG3_PATH = Path("data/processed/sg3_final_list.json")
SG3_COMBINED_PATH = Path("data/processed/sg3_combined_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")

TARGET = "Transport (Driving Hours Logbook Exemption) Notice 2003 ( Gazette 2003 p 2689)"


def remove_from(path, key="act"):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    before = len(data)
    matches = [c.get(key) for c in data if c.get(key) == TARGET]
    new_data = [c for c in data if c.get(key) != TARGET]
    removed = before - len(new_data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print(f"{path}: {before} -> {len(new_data)} ({removed} removed)" +
          (f"  [matched: {matches[0]!r}]" if matches else "  [NO MATCH FOUND]"))
    return new_data


sg3_after = remove_from(SG3_PATH)
remove_from(SG3_COMBINED_PATH)
identifiers_after = remove_from(IDENTIFIERS_PATH)

n_resolved = sum(1 for d in identifiers_after if d.get("resolved"))
print(f"\nSG3 now {len(sg3_after)} Acts.")
print(f"Identifiers: {n_resolved}/{len(identifiers_after)} resolved ({n_resolved/len(identifiers_after):.1%})")

if len(identifiers_after) == n_resolved:
    print("\nAll remaining SG3 Acts are resolved. Ready for sg2_step26.")