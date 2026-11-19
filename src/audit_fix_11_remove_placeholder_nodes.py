"""
audit_fix_11_remove_placeholder_nodes.py

Removes three NODES that are not legislation at all: placeholder phrases that
the citation/amendment extraction mistook for Act names and that the identifier
resolver then matched to unrelated real documents.

  layer  name           wrongly resolved to                     evidence
  SG2    "Act(s)"       Shipping and Seamen's Acts Amendment    text "Amendment(s) incorporated in the
                        Act 1890 (1890 No 15)                   Act(s)" in Government Superannuation Fund
                                                                 Act 1956; 83 citation edges, weight 591
  SG4    "Regulation 14" SR 2022/326                             in-text structural reference, not a title
  SG4    "Schedule 4"    LI 2026/279                             in-text structural reference, not a title

Found by the SLM spot-check integrity step (2026-10-07). Nothing is deleted
outright: every file touched is first copied to data/processed/_pre_fix11/,
removed raw XML is MOVED into the layer folder's _to_delete/, and a justification log is written to
data/processed/audit_fix_11_removed_placeholder_nodes.json.

Run from repo root. After it runs, regenerate the edges in layer order:
  sg2_step36_build_typed_edges_v2.py -> sg3_step02_build_typed_edges.py ->
  sg4_step18_build_typed_edges.py -> sg5_step01_build_typed_edges.py ->
  assemble_typed_multiedge_graph.py
"""
import json, shutil
from pathlib import Path
from sg4_filenames import filename_for_sg4

D = Path("data/processed")
BACKUP = D / "_pre_fix11"; BACKUP.mkdir(exist_ok=True)

REMOVALS = {
    "sg2": {"Act(s)": "Placeholder text 'Amendment(s) incorporated in the Act(s)' mis-read as an Act title; "
                      "resolver matched it to Shipping and Seamen's Acts Amendment Act 1890 (1890 No 15)."},
    "sg4": {"Regulation 14": "In-text structural reference ('regulation 14') mis-read as an instrument title; "
                             "resolver matched it to SR 2022/326.",
            "Schedule 4": "In-text structural reference ('Schedule 4') mis-read as an instrument title; "
                          "resolver matched it to LI 2026/279."},
}
FILES = {  # layer -> list files that carry {'act': name} rows
    "sg2": ["sg2_final_list.json", "sg2_combined_final_list.json", "sg2_act_identifiers.json"],
    "sg4": ["sg4_final_list.json", "sg4_combined_final_list.json", "sg4_act_identifiers.json", "sg4_internal_links.json"],
}

log = {"fix": "audit_fix_11", "removed": [], "raw_xml_moved": []}
removed_ids = {}
for layer, names in REMOVALS.items():
    for fn in FILES[layer]:
        p = D / fn
        rows = json.loads(p.read_text(encoding="utf-8"))
        shutil.copy2(p, BACKUP / fn) if not (BACKUP / fn).exists() else None
        keep, drop = [], []
        for r in rows:
            (drop if r.get("act") in names else keep).append(r)
        if fn.endswith("act_identifiers.json"):
            for r in drop: removed_ids[(layer, r["act"])] = r
        p.write_text(json.dumps(keep, indent=2, ensure_ascii=False), encoding="utf-8")
        log["removed"].append({"file": fn, "rows_removed": [r["act"] for r in drop], "rows_before": len(rows), "rows_after": len(keep)})
        print(f"{fn}: {len(rows)} -> {len(keep)}  (removed {[r['act'] for r in drop]})")

# expected counts: SG2 421->420, SG4 1130->1128
assert len(json.loads((D / "sg2_final_list.json").read_text())) == 420
assert len(json.loads((D / "sg4_final_list.json").read_text())) == 1128

# Move now-orphaned raw XML aside (never delete), only if no remaining identifier claims the file.
sg2_ids = json.loads((D / "sg2_act_identifiers.json").read_text())
sg4_ids = json.loads((D / "sg4_act_identifiers.json").read_text())
claimed = {("sg2_targets", f"{a['year']}_{a['number']}.xml") for a in sg2_ids if a.get("resolved")} | \
          {("sg4_targets", filename_for_sg4(a)) for a in sg4_ids if a.get("resolved") and "year" in a}
for (layer, name), r in removed_ids.items():
    folder = "sg2_targets" if layer == "sg2" else "sg4_targets"
    fname = f"{r['year']}_{r['number']}.xml" if layer == "sg2" else filename_for_sg4(r)
    src = Path("data/raw") / folder / fname
    if (folder, fname) in claimed:
        print(f"  keep {src}: still claimed by another identifier"); continue
    if src.exists():
        dst_dir = src.parent / "_to_delete"; dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst_dir / fname))
        log["raw_xml_moved"].append(str(src)); print(f"  moved {src} -> _to_delete/")
    else:
        print(f"  (no raw file at {src} in this checkout)")

(D / "audit_fix_11_removed_placeholder_nodes.json").write_text(
    json.dumps({**log, "justifications": {k: v for l in REMOVALS.values() for k, v in l.items()}}, indent=2, ensure_ascii=False), encoding="utf-8")
print("log -> data/processed/audit_fix_11_removed_placeholder_nodes.json")
