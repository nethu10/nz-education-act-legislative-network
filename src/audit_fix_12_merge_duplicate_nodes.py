"""
audit_fix_12_merge_duplicate_nodes.py

Writes data/processed/audit_fix_12_node_merges.json, the alias map that
assemble_typed_multiedge_graph.py (and boilerplate_citation_audit.py) apply so that one document is one node.

Why: the 2026-10-13 duplicate scan (same year+number, same legislation.govt.nz URL / identical XML text) found
the same document present under two names. Nothing is deleted: the upstream final lists, identifier files and
raw XML are untouched; the merge is applied when the graph is assembled, and the pre-fix outputs are kept in
outputs/_pre_fix12/.

  kind    alias node (layer)                                  -> canonical node (layer)                         evidence
  merge   Schedule 9 of the Education and Training Act 2020 (SG2) -> Education and Training Act 2020 (SG0)       same Act (LMS170674, 2020 No 38); XML = two snapshots
  merge   Schedule 1 of the Social Security Act 2018 (SG3)    -> Social Security Act 2018 (2018 No 32) (SG1)    XML text identical to the SG1 file
  merge   Schedule 5 of the Crown Entities Act 2004 (SG3)     -> Crown Entities Act 2004 (2004 No 115) (SG1)    XML text identical to the SG1 file
  merge   Government Superannuation Fund Act 1956 (1956 No 47) (RS Vol 21, p 209) (SG3) -> same without the reprint note (SG1)   XML text identical
  merge   Health Reforms (Transitional Provisions) Act 1993 (SG4) -> Health Sector (Transfers) Act 1993 (SG2)   same 1993 No 23, same URL; former title
  merge   Securities Trustees and Statutory Supervisors Act 2011 (SG4) -> Financial Markets Supervisors Act 2011 (SG3)  same 2011 No 10, same URL; former title
  rename  Schedule 1 of the Immigration Regulations 1999 (SG2) -> Immigration Regulations 1999 (SR 1999/284)    XML title is "Immigration Regulations 1999"; no parent node exists

Merge policy ("dedupe"):
  * a self-loop created by the merge is dropped;
  * edges out of a merged document come from the same text, so per target the larger count is kept (not summed);
  * amendment edges (counted from the target's history note) take the larger count;
  * citations INTO the merged node from one third-party document are summed (distinct references in its text).
Run from repo root, then: python src/assemble_typed_multiedge_graph.py
"""
import csv, json, shutil
from pathlib import Path

D = Path("data/processed"); OUT = D / "audit_fix_12_node_merges.json"
nodes = {r["id"]: r for r in csv.DictReader(open("outputs/_pre_fix12/graph_typed/nodes.csv", encoding="utf-8"))}

M = [
 ("Schedule 9 of the Education and Training Act 2020", "Education and Training Act 2020", "merge",
  "Structural reference to a schedule of the seed Act, resolved by the identifier step to 2020 No 38 (the seed). Both XML files carry document id LMS170674; they are different snapshots (1.78M vs 1.84M characters of text), so out-edges take the larger count."),
 ("Schedule 1 of the Social Security Act 2018", "Social Security Act 2018 (2018 No 32)", "merge",
  "Resolved to 2018 No 32; the SG3 XML text is identical to the SG1 file (normalised text, 1,137,638 characters)."),
 ("Schedule 5 of the Crown Entities Act 2004", "Crown Entities Act 2004 (2004 No 115)", "merge",
  "Resolved to 2004 No 115; the SG3 XML text is identical to the SG1 file (251,773 characters)."),
 ("Government Superannuation Fund Act 1956 (1956 No 47) (RS Vol 21, p 209)", "Government Superannuation Fund Act 1956 (1956 No 47)", "merge",
  "Same Act cited with a reprint-volume note; the SG3 XML text is identical to the SG1 file (837,635 characters)."),
 ("Health Reforms (Transitional Provisions) Act 1993", "Health Sector (Transfers) Act 1993", "merge",
  "Both resolved to 1993 No 23 at the same legislation.govt.nz URL; the current title (in the SG2 XML) is Health Sector (Transfers) Act 1993, so the SG4 name is a former title."),
 ("Securities Trustees and Statutory Supervisors Act 2011", "Financial Markets Supervisors Act 2011", "merge",
  "Both resolved to 2011 No 10 at the same legislation.govt.nz URL; the current title (in the SG3 XML) is Financial Markets Supervisors Act 2011, so the SG4 name is a former title."),
 ("Schedule 1 of the Immigration Regulations 1999", "Immigration Regulations 1999 (SR 1999/284)", "rename",
  "Resolved to SR 1999/284 (revoked 2010-11-29); the XML title is 'Immigration Regulations 1999'. No parent node exists, so the node is renamed, not merged."),
]
merges = []
for alias, canon, kind, why in M:
    assert alias in nodes, alias
    if kind == "merge": assert canon in nodes, canon
    a = nodes[alias]
    merges.append({"alias": alias, "canonical": canon, "kind": kind, "evidence": why,
                   "alias_node": {k: a[k] for k in ("layer", "has_xml", "resolved", "year", "number", "doc_type")}})
OUT.write_text(json.dumps({"fix": "audit_fix_12", "policy": "dedupe", "merges": merges}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"{len(merges)} entries -> {OUT}")
