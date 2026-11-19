"""
Check whether the 37 SG1 Acts cite/are cited by each other directly --
i.e. whether SG1 has any internal (SG1 x SG1) edges beyond each
member's individual connection to the seed. This has never been
checked before now: SG1 was discovered purely via "is this Act
connected to the seed", and SG2 purely via "is this Act connected to
some SG1 member" -- neither step ever checked connections WITHIN a
layer, and the diagram currently only draws seed->SG1 and
SG1->best-SG2-source edges (a discovery tree, not the true induced
subgraph).

Reuses the same validated rule-based citation extractor from
sg2_step6_extract_citations.py, now applied to each SG1 Act's own XML
file in data/raw/sg2_targets/ (confirmed to hold exactly the 37 SG1
Acts' source files) instead of to SG2 candidate names.
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SG1_PATH = Path("data/processed/sg1_final_list.json")
TARGETS_DIR = Path("data/raw/sg2_targets")

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
def normalize(name):
    if not name:
        return name
    name = name.replace("\u2019", "'").replace("\u2018", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def element_text(el):
    return "".join(el.itertext())

ACT_NAME_PATTERN = re.compile(
    r"of\s+(?:Part\s+\S+\s+of\s+)?(?:the\s+)?"
    r"([A-Z][A-Za-z0-9,\u2019'\-\(\) ]*?\b(?:Act|Rules?|Regulations?|Order|Notice|Bylaw)\s+\d{4})\b"
)

def resolve_citation(cit_el):
    leg_title = None
    has_extref = False
    for child in cit_el.iter():
        ln = local_name(child.tag)
        if ln == "leg-title" and leg_title is None:
            leg_title = child
        elif ln == "extref":
            has_extref = True
    if leg_title is not None:
        return element_text(leg_title), "leg_title"
    if not has_extref:
        return None, "internal_only"
    full_text = element_text(cit_el)
    if re.search(r"\bthis Act\b", full_text):
        return None, "self"
    m = ACT_NAME_PATTERN.search(full_text)
    if m:
        return m.group(1).strip(), "text_match"
    if re.search(r"\bthat Act\b", full_text) or re.search(r"\bthe Act\b", full_text):
        return None, "anaphoric"
    return None, "unresolved"


def filename_for(act_field):
    m = CITE_PATTERN.match(act_field.strip())
    if not m:
        return None
    cite = m.group(2)
    if cite.startswith(("SR", "LI")):
        ym = re.match(r"(?:SR|LI)\s+(\d{4})/(\d+)", cite)
        prefix = "secondary-legislation"
    else:
        ym = re.match(r"(\d{4})\s+No\s+(\d+)", cite)
        prefix = "act"
    if not ym:
        return None
    year, number = ym.groups()
    return f"{prefix}_{year}_{number}.xml"


def extract_citations_from_file(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    cited = {}
    last_named_act = None
    for el in root.iter():
        ln = local_name(el.tag)
        if ln == "prov":
            last_named_act = None
        if ln == "citation" and el.get("jurisdiction") == "nz":
            name, method = resolve_citation(el)
            if name:
                key = normalize(name)
                cited[key] = cited.get(key, 0) + 1
                last_named_act = name
            elif method == "anaphoric" and last_named_act:
                key = normalize(last_named_act)
                cited[key] = cited.get(key, 0) + 1
    return cited


def main():
    sg1 = json.loads(SG1_PATH.read_text(encoding="utf-8"))
    sg1_names = {normalize(a["act"]) for a in sg1}

    missing_files = []
    edges = []  # (source_act, target_act, count)
    per_source_summary = []

    for a in sg1:
        fname = filename_for(a["act"])
        path = TARGETS_DIR / fname if fname else None
        if not path or not path.exists():
            missing_files.append((a["act"], fname))
            continue

        source_name = normalize(a["act"])
        cited = extract_citations_from_file(path)

        internal_hits = {name: n for name, n in cited.items()
                          if name in sg1_names and name != source_name}
        for target_name, count in internal_hits.items():
            edges.append((source_name, target_name, count))

        per_source_summary.append((source_name, len(internal_hits)))

    print(f"SG1 Acts processed: {len(per_source_summary)} / {len(sg1)}")
    if missing_files:
        print(f"\nSG1 Acts with no matching XML file in {TARGETS_DIR}: {len(missing_files)}")
        for name, fname in missing_files:
            print(f"  {name}  (expected: {fname})")

    print(f"\nTotal SG1-internal citation edges found: {len(edges)}")
    print(f"SG1 Acts with at least one internal citation edge: "
          f"{sum(1 for _, n in per_source_summary if n > 0)} / {len(per_source_summary)}")

    print("\nAll SG1-internal citation edges (source -> target, count):")
    for source, target, count in sorted(edges, key=lambda e: -e[2]):
        print(f"  {source}  ->  {target}   ({count}x)")

    out_path = Path("data/processed/sg1_internal_citation_edges.json")
    out_path.write_text(json.dumps(
        [{"source": s, "target": t, "count": c} for s, t, c in edges],
        indent=2, ensure_ascii=False
    ), encoding="utf-8")
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()