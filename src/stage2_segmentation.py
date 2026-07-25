"""
Stage 2: Parsing and segmentation.

Produces three clean, structured datasets from the raw XML:
  1. provisions.json          — one record per ordinary provision, or per
                                 individual definition for definition-heavy
                                 sections like "Interpretation"
  2. amendment_records.json   — incoming amendments: other Acts amending
                                 this one (from <history-note>)
  3. outgoing_amendments.json — outgoing amendments: this Act amending
                                 other Acts (from the Schedule of
                                 Consequential Amendments)

Internal (intref) and external (extref) reference hrefs are captured on
every record — these are the raw citation edges for Stage 6's network
expansion, extracted here rather than re-parsed later.
"""

import json
import re
from pathlib import Path
from lxml import etree

RAW_PATH = Path("data/raw/education_and_training_act_2020.xml")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def element_text(el) -> str:
    """Flattens all text inside an element into one clean string."""
    if el is None:
        return ""
    raw = " ".join(el.itertext())
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"\s+([,.:;)])", r"\1", cleaned)
    return cleaned


def find_first(el, tag_name):
    for child in el.iter():
        if local_name(child.tag) == tag_name:
            return child
    return None


def find_ancestor(el, tag_name):
    parent = el.getparent()
    while parent is not None and local_name(parent.tag) != tag_name:
        parent = parent.getparent()
    return parent


def extract_refs(el, tag_name) -> list[str]:
    return [
        child.get("href") for child in el.iter()
        if local_name(child.tag) == tag_name and child.get("href")
    ]


def extract_provisions(root) -> list[dict]:
    """Ordinary provisions and, separately, individual definitions."""
    records = []
    for prov in root.iter():
        if local_name(prov.tag) != "prov":
            continue

        label_el = prov.find("label")
        heading_el = prov.find("heading")
        section_number = label_el.text if label_el is not None else None
        heading = heading_el.text if heading_el is not None else None
        body_el = prov.find("prov.body")
        if body_el is None:
            continue

        def_paras = [el for el in body_el.iter() if local_name(el.tag) == "def-para"]

        if def_paras:
            for dp in def_paras:
                term_el = find_first(dp, "def-term")
                records.append({
                    "id": dp.get("id"),
                    "type": "definition",
                    "section_number": section_number,
                    "heading": heading,
                    "term": element_text(term_el) or None,
                    "text": element_text(dp),
                    "internal_refs": extract_refs(dp, "intref"),
                    "external_refs": extract_refs(dp, "extref"),
                })
        else:
            records.append({
                "id": prov.get("id"),
                "type": "provision",
                "section_number": section_number,
                "heading": heading,
                "term": None,
                "text": element_text(body_el),
                "internal_refs": extract_refs(body_el, "intref"),
                "external_refs": extract_refs(body_el, "extref"),
            })
    return records


def extract_amendment_records(root) -> list[dict]:
    """Incoming: other Acts amending this one."""
    records = []
    for note in root.iter():
        if local_name(note.tag) != "history-note":
            continue

        def first_text(tag_name):
            el = note.find(tag_name)
            return el.text if el is not None else None

        amending_provision_el = note.find("amending-provision")

        records.append({
            "id": note.get("id"),
            "amended_provision": first_text("amended-provision"),
            "operation": first_text("amending-operation"),
            "date": first_text("amendment-date"),
            "amending_provision_ref": (
                amending_provision_el.get("href") if amending_provision_el is not None else None
            ),
            "amending_act": first_text("amending-leg"),
            "full_text": element_text(note),
        })
    return records


def extract_outgoing_amendments(root) -> list[dict]:
    """Outgoing: this Act amending other Acts (Schedule of Consequential Amendments)."""
    records = []
    for group2 in root.iter():
        if local_name(group2.tag) != "schedule.amendments.group2":
            continue

        heading_el = group2.find("heading")
        target_act = element_text(heading_el) if heading_el is not None else None

        group1 = find_ancestor(group2, "schedule.amendments.group1")
        part_heading_el = group1.find("heading") if group1 is not None else None
        part_context = element_text(part_heading_el) if part_heading_el is not None else None

        for i, para in enumerate(group2.findall("para")):
            records.append({
                "id": f"{group2.get('id')}_para{i}",
                "target_act": target_act,
                "part_context": part_context,
                "text": element_text(para),
                "target_section_refs": extract_refs(para, "extref"),
            })
    return records


if __name__ == "__main__":
    tree = etree.parse(str(RAW_PATH))
    root = tree.getroot()

    provisions = extract_provisions(root)
    incoming = extract_amendment_records(root)
    outgoing = extract_outgoing_amendments(root)

    (OUT_DIR / "provisions.json").write_text(
        json.dumps(provisions, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT_DIR / "amendment_records.json").write_text(
        json.dumps(incoming, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT_DIR / "outgoing_amendments.json").write_text(
        json.dumps(outgoing, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    n_definitions = sum(1 for p in provisions if p["type"] == "definition")
    n_ordinary = sum(1 for p in provisions if p["type"] == "provision")

    print(f"Provisions: {len(provisions)} total ({n_ordinary} ordinary, {n_definitions} definitions)")
    print(f"Incoming amendments (other Acts -> this Act): {len(incoming)}")
    print(f"Outgoing amendments (this Act -> other Acts): {len(outgoing)}")

    target_acts = sorted(set(r["target_act"] for r in outgoing if r["target_act"]))
    print(f"\nDistinct target Acts amended by this Act: {len(target_acts)}")
    for act in target_acts[:10]:
        print(f"  - {act}")

    print("\nSample outgoing amendment:")
    print(json.dumps(outgoing[0], indent=2, ensure_ascii=False))