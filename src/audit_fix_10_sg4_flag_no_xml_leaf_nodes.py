"""
audit_fix_10_sg4_flag_no_xml_leaf_nodes.py

22 of the 39 entries resolved by audit_fix_09 have no standalone page or XML
on legislation.govt.nz (both /en/latest/ and /en/latest.xml return 404): old
amendment regulations / local amending Acts that exist only as entries in the
parent instrument's version history. Identifiers are verified (parent history),
so the nodes are KEPT as leaf nodes (incoming edges only). Flags them
xml_available=false and clears url/xml_url so nothing fetches a 404.
The 17 that downloaded successfully are marked xml_available=true.
"""
import json
from pathlib import Path
P = Path("data/processed/sg4_act_identifiers.json")
OK = {(2014,339),(1959,85),(1931,31),(2002,385),(2011,10),(1993,23),(1960,90),(2000,210),
      (2006,60),(1990,120),(1967,141),(1988,208),(1963,53),(1952,53),(2008,389),(1963,126),(1964,125)}
data = json.load(open(P, encoding="utf-8"))
n_no = n_ok = 0
for d in data:
    if d.get("resolved_via") != "audit_fix_09_manual_verified":
        continue
    if (d["year"], int(d["number"])) in OK:
        d["xml_available"] = True; n_ok += 1
    else:
        d["url_attempted"], d["xml_url_attempted"] = d["url"], d["xml_url"]
        d["url"] = d["xml_url"] = None
        d["xml_available"] = False
        d["xml_note"] = "No standalone page/XML on legislation.govt.nz (404); identifier verified via parent version history. Kept as leaf node."
        n_no += 1
assert (n_ok, n_no) == (17, 22), (n_ok, n_no)
json.dump(data, open(P, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("xml_available=true:", n_ok, " false (leaf):", n_no)
for d in data:
    if d.get("xml_available") is False:
        print(" ", d["type"], d.get("status") or d.get("subtype"), d["year"], d["number"], "|", d["act"].replace("\xa0"," "))
