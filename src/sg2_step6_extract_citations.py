"""
sg2_step6_extract_citations.py

Citation-relationship extraction for SG2, built entirely from plain-text
already present in the XML -- no network resolution needed. Handles the
four patterns found in check_citation_full_blocks.py's output:
  1. <leg-title>Act Name</leg-title>            -- name given directly
  2. <extref>section N</extref> of the {Act}    -- name in trailing text
  3. <extref>section N</extref> of that/this Act -- anaphoric / self-ref
  4. <intref> only or bare text                  -- internal, skipped

Excludes the same source Acts already excluded on the amendment side:
the two confirmed hub Acts (Income Tax Act 2007, Tax Administration Act
1994).
"""
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from lxml import etree

TARGETS_DIR = Path("data/raw/sg2_targets")
SG1_PATH = Path("data/processed/sg1_final_list.json")
OUTPUT_PATH = Path("data/processed/sg2_citation_candidates.json")
UNRESOLVED_PATH = Path("data/processed/sg2_citation_unresolved.json")

HUB_ACTS_EXCLUDED = {
    "Income Tax Act 2007",
    "Tax Administration Act 1994",
}

CITE_PATTERN = re.compile(
    r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$"
)

ACT_NAME_PATTERN = re.compile(
    r"of\s+(?:Part\s+\S+\s+of\s+)?(?:the\s+)?"
    r"([A-Z][A-Za-z0-9,\u2019'\-\(\) ]*?\b(?:Act|Rules?|Regulations?|Order|Notice|Bylaw)\s+\d{4})\b"
)

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def element_text(el):
    if el is None:
        return ""
    raw = " ".join(el.itertext())
    return re.sub(r"\s+", " ", raw).strip()

with open(SG1_PATH) as f:
    sg1_acts = json.load(f)

def build_act_lookup():
    lookup = {}
    for a in sg1_acts:
        full = a.get("act", "")
        m = CITE_PATTERN.match(full.strip())
        if not m:
            continue
        name, cite = m.group(1), m.group(2)
        if cite.startswith(("SR", "LI")):
            ym = re.match(r"(?:SR|LI)\s+(\d{4})/(\d+)", cite)
        else:
            ym = re.match(r"(\d{4})\s+No\s+(\d+)", cite)
        if ym:
            year, number = ym.groups()
            lookup[(year, number)] = name
    return lookup

lookup = build_act_lookup()

def resolve_citation(cit_el):
    """Returns (act_name_or_None, kind)."""
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

candidates = defaultdict(lambda: {"combined_score": 0, "linked_from": []})
unresolved_examples = []
stats = Counter()

xml_files = sorted(TARGETS_DIR.glob("*.xml"))

for xml_path in xml_files:
    m = re.search(r"_(\d{4})_(\d+)\.xml$", xml_path.name)
    if not m:
        continue
    year, number = m.groups()
    source_act = lookup.get((year, number), xml_path.stem)

    if source_act in HUB_ACTS_EXCLUDED:
        print(f"skipping hub Act: {source_act}")
        continue

    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    last_named_act = None
    found_this_source = 0

    for el in root.iter():
        ln = local_name(el.tag)
        if ln == "prov":
            last_named_act = None  # reset anaphora context at each provision
            continue
        if ln != "citation" or el.get("jurisdiction") != "nz":
            continue

        name, kind = resolve_citation(el)
        stats[kind] += 1

        if kind in ("leg_title", "text_match"):
            last_named_act = name
            candidates[name]["combined_score"] += 1
            candidates[name]["linked_from"].append(source_act)
            found_this_source += 1
        elif kind == "anaphoric" and last_named_act:
            candidates[last_named_act]["combined_score"] += 1
            candidates[last_named_act]["linked_from"].append(source_act)
            found_this_source += 1
        elif kind == "unresolved":
            unresolved_examples.append({"source": source_act, "text": element_text(el)})

    print(f"  {source_act}: {found_this_source} citation-based candidate hits")

print()
print("Resolution breakdown:", dict(stats))
print(f"Distinct candidate Acts found: {len(candidates)}")

result = [{"act": name, **data} for name, data in candidates.items()]
result.sort(key=lambda c: -c["combined_score"])

with open(OUTPUT_PATH, "w") as f:
    json.dump(result, f, indent=2)
with open(UNRESOLVED_PATH, "w") as f:
    json.dump(unresolved_examples[:200], f, indent=2)

print(f"\nSaved -> {OUTPUT_PATH}")
print(f"Saved sample of unresolved citations -> {UNRESOLVED_PATH}")

print("\nTop 30 citation-based candidates:")
for c in result[:30]:
    print(f"  {c['act']}  (score {c['combined_score']}, {len(c['linked_from'])} links)")