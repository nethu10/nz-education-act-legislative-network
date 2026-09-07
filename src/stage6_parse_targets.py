"""
Stage 6: light-touch parsing of the 13 target Acts. Extracts identity,
size, and each Act's own incoming/outgoing amendment connections --
the genuine second ring of the network -- without full provision-by-
provision extraction, which isn't warranted for supporting Acts that
don't undergo the same SLM analysis as the seed Act.
"""

import json
from lxml import etree
from pathlib import Path

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def element_text(el):
    if el is None:
        return ""
    import re
    raw = " ".join(el.itertext())
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"\s+([,.:;)])", r"\1", cleaned)
    return cleaned

def find_ancestor(el, tag_name):
    parent = el.getparent()
    while parent is not None and local_name(parent.tag) != tag_name:
        parent = parent.getparent()
    return parent

def extract_incoming(root):
    records = []
    for note in root.iter():
        if local_name(note.tag) != "history-note":
            continue
        def first_text(tag_name):
            el = note.find(tag_name)
            return el.text if el is not None else None
        records.append({
            "amended_provision": first_text("amended-provision"),
            "operation": first_text("amending-operation"),
            "date": first_text("amendment-date"),
            "amending_act": first_text("amending-leg"),
        })
    return records

def extract_outgoing(root):
    records = []
    for group2 in root.iter():
        if local_name(group2.tag) != "schedule.amendments.group2":
            continue
        heading_el = group2.find("heading")
        target_act = element_text(heading_el) if heading_el is not None else None
        for para in group2.findall("para"):
            records.append({"target_act": target_act, "text": element_text(para)[:200]})
    return records

target_acts = json.loads(Path("data/processed/stage6_target_acts.json").read_text())
results = []

for t in target_acts:
    xml_path = Path(f"data/raw/stage6_targets/{t['year']}_{t['number']}.xml")
    if not xml_path.exists():
        print(f"SKIP (file not found): {t['name']}")
        continue

    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    prov_count = sum(1 for el in root.iter() if local_name(el.tag) == "prov")
    incoming = extract_incoming(root)
    outgoing = extract_outgoing(root)

    incoming_sources = sorted(set(r["amending_act"] for r in incoming if r["amending_act"]))
    outgoing_targets = sorted(set(r["target_act"] for r in outgoing if r["target_act"]))

    result = {
        "name": t["name"],
        "id": root.get("id"),
        "date_as_at": root.get("date.as.at"),
        "provision_count": prov_count,
        "incoming_amendment_count": len(incoming),
        "outgoing_amendment_count": len(outgoing),
        "incoming_sources": incoming_sources,
        "outgoing_targets": outgoing_targets,
    }
    results.append(result)
    print(f"{t['name']}: {prov_count} provisions, {len(incoming)} incoming, {len(outgoing)} outgoing "
          f"({len(outgoing_targets)} distinct second-ring targets)")

Path("data/processed/stage6_target_acts_summary.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved to data/processed/stage6_target_acts_summary.json")

all_second_ring = set()
for r in results:
    all_second_ring.update(r["outgoing_targets"])
print(f"\nTotal distinct second-ring Acts discovered (before dedup against existing 193): {len(all_second_ring)}")