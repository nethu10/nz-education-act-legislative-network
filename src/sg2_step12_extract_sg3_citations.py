"""
sg2_step12_extract_sg3_citations.py

Citation-side candidate pool for SG3 -- the direct sequel to
sg2_step6_extract_citations.py, but scanning the 436 SG2 Acts instead of
the 37 SG1 Acts. Same citation-pattern logic (leg-title / extref / bare
sentinel resolution), reused unchanged, since that part of the method has
already proven itself and there's no reason to touch it.

WHY THIS FILE DEFENDS AGAINST FOLDER CONTAMINATION
------------------------------------------------------
sg2_step6 read cached XML from data/raw/sg2_targets/ -- at that point in
the pipeline, that folder meant "the 37 SG1 Acts, i.e. the documents
being scanned to find SG2." sg2_step11_find_internal_links.py (this
session) later wrote the 436 SG2 Acts' XML into a folder with the exact
same name, for the unrelated reason that THEY are now the layer being
scanned. Purely by that naming coincidence, a real working copy of this
project may have both the old 37 SG1 files and the new 436 SG2 files
sitting in the same data/raw/sg2_targets/ directory.

Rather than assume the folder is clean, this script explicitly builds
the set of SG1 (year, number) identifiers and skips any XML file that
matches one, regardless of whether the folder actually turns out to be
mixed. This makes the script correct either way, instead of correct only
if a manual folder-cleanup happened first.

WHY THERE'S NO HUB_ACTS_EXCLUDED HERE
------------------------------------------------------
sg2_step6 skipped scanning citations FROM Income Tax Act 2007 and Tax
Administration Act 1994 -- both confirmed SG1 Acts -- presumably because
their own citation text is unusually generic/heavy and would flood the
SG2 citation pool with noise. There isn't yet evidence for which (if any)
SG2 Acts play that same role for SG3, so this script doesn't guess new
exclusions up front. If the raw output shows an analogous flood from a
specific source, that's a decision to make on evidence (the same way
every other exclusion in this pipeline was made), not in advance.

Inputs:
  data/raw/sg2_targets/*.xml           -- cached XML (436 SG2 + possibly
                                           37 leftover SG1 files; SG1 ones
                                           are skipped, see above)
  data/processed/sg1_final_list.json   -- to build the SG1-skip set
  data/processed/sg2_act_identifiers.json -- to map (year, number) -> the
                                           real SG2 Act name for each file

Outputs:
  data/processed/sg3_citation_candidates.json
  data/processed/sg3_citation_unresolved.json  (sample, for spot-checking)
"""
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from lxml import etree

TARGETS_DIR = Path("data/raw/sg2_targets")
SG1_PATH = Path("data/processed/sg1_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg2_act_identifiers.json")
OUTPUT_PATH = Path("data/processed/sg3_citation_candidates.json")
UNRESOLVED_PATH = Path("data/processed/sg3_citation_unresolved.json")

CITE_PATTERN = re.compile(
    r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$"
)

ACT_NAME_PATTERN = re.compile(
    r"of\s+(?:Part\s+\S+\s+of\s+)?(?:the\s+)?"
    r"([A-Z][A-Za-z0-9,’'\-\(\) ]*?\b(?:Act|Rules?|Regulations?|Order|Notice|Bylaw)\s+\d{4})\b"
)

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def element_text(el):
    if el is None:
        return ""
    raw = " ".join(el.itertext())
    return re.sub(r"\s+", " ", raw).strip()

# ---- build the SG1 skip-set (defends against the shared-folder-name issue) ----
with open(SG1_PATH, encoding="utf-8") as f:
    sg1_acts = json.load(f)

sg1_identifiers = set()
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
        sg1_identifiers.add((year, number))

# ---- build the SG2 (year, number) -> real Act name lookup ----
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

sg2_lookup = {}
for d in identifiers:
    if not d.get("resolved"):
        continue
    year, number = str(d.get("year", "")), str(d.get("number", ""))
    sg2_lookup[(year, number)] = d["act"]

def resolve_citation(cit_el):
    """Returns (act_name_or_None, kind). Unchanged from sg2_step6."""
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
print(f"{len(xml_files)} XML files found in {TARGETS_DIR}")

n_skipped_sg1 = 0
n_skipped_unmapped = 0
n_scanned = 0

for xml_path in xml_files:
    m = re.search(r"_?(~?\d{4})_(~?\d+)\.xml$", xml_path.name)
    if not m:
        print(f"  skipping unrecognised filename: {xml_path.name}")
        continue
    year, number = m.groups()

    if (year, number) in sg1_identifiers:
        n_skipped_sg1 += 1
        continue  # leftover SG1 file from the shared folder name -- not part of this scan

    source_act = sg2_lookup.get((year, number))
    if source_act is None:
        print(f"  WARNING: {xml_path.name} doesn't map to a known SG2 Act -- skipping rather than guessing")
        n_skipped_unmapped += 1
        continue

    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    n_scanned += 1

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

    if n_scanned % 50 == 0:
        print(f"  [{n_scanned}] ...still scanning ({source_act})")

print()
print(f"Scanned as SG2 sources: {n_scanned}")
print(f"Skipped (leftover SG1 file, same folder name): {n_skipped_sg1}")
print(f"Skipped (file didn't map to any known SG2 Act): {n_skipped_unmapped}")
print()
print("Resolution breakdown:", dict(stats))
print(f"Distinct candidate Acts found: {len(candidates)}")

result = [{"act": name, **data} for name, data in candidates.items()]
result.sort(key=lambda c: -c["combined_score"])

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
with open(UNRESOLVED_PATH, "w", encoding="utf-8") as f:
    json.dump(unresolved_examples[:200], f, indent=2, ensure_ascii=False)

print(f"\nSaved -> {OUTPUT_PATH}")
print(f"Saved sample of unresolved citations -> {UNRESOLVED_PATH}")

print("\nTop 30 citation-based SG3 candidates:")
for c in result[:30]:
    print(f"  {c['act']}  (score {c['combined_score']}, {len(c['linked_from'])} links)")
