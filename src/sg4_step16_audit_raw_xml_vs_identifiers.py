"""
sg4_step16_audit_raw_xml_vs_identifiers.py  (run on the Mac, project root)

Checks data/raw/sg4_targets against sg4_act_identifiers.json:
  - every resolved entry with a URL has a file with matching year/number
  - no orphan files (files no identifier points to)
  - counts leaf nodes (resolved but no XML) = SG4 "no XML" figure for the thesis
Writes data/processed/sg4_raw_xml_audit.md and prints the summary.
"""
import json, sys, re
from pathlib import Path
sys.path.insert(0, "src")
from sg4_filenames import filename_for_sg4, find_collisions
RAW = Path("data/raw/sg4_targets")
ids = json.load(open("data/processed/sg4_act_identifiers.json", encoding="utf-8"))
res = [d for d in ids if d.get("resolved")]
unres = [d for d in ids if not d.get("resolved")]
leaf = [d for d in res if not d.get("url")]
have = [d for d in res if d.get("url")]
expected = {filename_for_sg4(d): d for d in have}
disk = {p.name for p in RAW.glob("*.xml")}
missing = sorted(set(expected) - disk)
orphans = sorted(disk - set(expected))
bad = []
for fn, d in expected.items():
    p = RAW / fn
    if not p.exists(): continue
    head = p.read_text(encoding="utf-8", errors="replace")[:4000]
    t = re.search(r"<(?![?!])[\w.-]+\b[^>]*>", head)
    yr = re.search(r'\byear="(\d+)"', t.group(0)) if t else None
    no = re.search(r'(?:act|sr)\.no="([^"]+)"', t.group(0)) if t else None
    if not (yr and no and int(yr.group(1)) == int(d["year"]) and no.group(1) == str(d["number"])):
        bad.append((fn, yr and yr.group(1), no and no.group(1)))
lines = [f"# SG4 raw XML audit", "",
 f"- identifier entries: {len(ids)} (resolved {len(res)}, unresolved {len(unres)})",
 f"- resolved with XML expected: {len(have)}; leaf nodes without XML: {len(leaf)}",
 f"- files on disk: {len(disk)}",
 f"- expected but missing: {len(missing)} {missing}",
 f"- orphan files: {len(orphans)} {orphans}",
 f"- year/number mismatches: {len(bad)} {bad}",
 f"- filename collisions: {find_collisions(res)}"]
Path("data/processed/sg4_raw_xml_audit.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
