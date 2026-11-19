"""
SG2, step 2: run Stage 2 segmentation + amendment classification across
all 37 SG2 target XML files (not the seed), aggregate into one candidate
pool, and exclude the seed Act / existing SG1 members / self-references.

Pure XML parsing -- no SLM, no Ollama needed for this step.
"""
import json
import re
from pathlib import Path
from collections import defaultdict
from lxml import etree

RAW_DIR = Path("data/raw/sg2_targets")
OUT_DIR = Path("data/processed")
SEED_ACT_NAME = "Education and Training Act 2020"

sg1_acts = json.loads((OUT_DIR / "sg1_final_list.json").read_text())

def normalize(name):
    """Strip citation suffixes like '(2004 No 115)' and normalise
    whitespace/case for matching against SG1/seed."""
    base = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    return base.lower()

sg1_names_norm = {normalize(a["act"]) for a in sg1_acts}
seed_norm = normalize(SEED_ACT_NAME)

# ---- reused verbatim from your Stage 2 script ----
def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def element_text(el):
    if el is None:
        return ""
    raw = " ".join(el.itertext())
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"\s+([,.:;)])", r"\1", cleaned)
    return cleaned

def find_ancestor(el, tag_name):
    parent = el.getparent()
    while parent is not None and local_name(parent.tag) != tag_name:
        parent = parent.getparent()
    return parent

def extract_refs(el, tag_name):
    return [c.get("href") for c in el.iter()
            if local_name(c.tag) == tag_name and c.get("href")]

def extract_amendment_records(root):
    records = []
    for note in root.iter():
        if local_name(note.tag) != "history-note":
            continue
        def first_text(tag_name):
            el = note.find(tag_name)
            return el.text if el is not None else None
        records.append({
            "operation": first_text("amending-operation"),
            "amending_act": first_text("amending-leg"),
        })
    return records

def extract_outgoing_amendments(root):
    records = []
    for group2 in root.iter():
        if local_name(group2.tag) != "schedule.amendments.group2":
            continue
        heading_el = group2.find("heading")
        target_act = element_text(heading_el) if heading_el is not None else None
        for i, para in enumerate(group2.findall("para")):
            records.append({"target_act": target_act, "text": element_text(para)})
    return records

def classify_operation(text):
    t = text.lower()
    if re.search(r"\brepeal(s|ed|ing)?\b", t): return "repeal"
    if re.search(r"\binsert(s|ed|ing)?\b", t): return "insert"
    if re.search(r"\breplace(s|d|ing)?\b", t): return "replace"
    if re.search(r"\bomit(s|ted|ting)?\b", t): return "omit"
    return "amend (other)"
# ---- end reused block ----

pool = defaultdict(lambda: {"combined_score": 0, "linked_from": [], "display_name": None})
excluded_self_or_seed = []

xml_files = sorted(RAW_DIR.glob("*.xml"))
print(f"Processing {len(xml_files)} SG2 source Acts...\n")

for xml_path in xml_files:
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
    except Exception as e:
        print(f"  PARSE FAILED: {xml_path.name} ({type(e).__name__}: {e})")
        continue

    incoming = extract_amendment_records(root)
    outgoing = extract_outgoing_amendments(root)

    # source Act's own name -- best guess from the filename's SG1 entry
    stem = xml_path.stem  # e.g. "act_2004_115" or "secondary-legislation_2016_122"
    parts = stem.rsplit("_", 2)
    year, number = parts[-2], parts[-1]
    source_match = next((a["act"] for a in sg1_acts
                          if f"{year}" in a["act"] and f"/{number})" in a["act"].replace(" No ", "/").replace("(", "(")), None)
    source_name = source_match or stem
    source_norm = normalize(source_name)

    per_source_counts = defaultdict(int)
    for r in incoming:
        if r["amending_act"]:
            per_source_counts[r["amending_act"]] += 1
    for r in outgoing:
        if r["target_act"]:
            per_source_counts[r["target_act"]] += 1  # counted regardless of operation type; breakdown by op comes later if needed

    kept = 0
    for candidate, count in per_source_counts.items():
        cand_norm = normalize(candidate)
        if cand_norm == source_norm or cand_norm == seed_norm or cand_norm in sg1_names_norm:
            excluded_self_or_seed.append((source_name, candidate))
            continue
        pool[cand_norm]["combined_score"] += count
        pool[cand_norm]["linked_from"].append(source_name)
        pool[cand_norm]["display_name"] = candidate
        kept += 1

    print(f"  {source_name}: {len(incoming)} incoming, {len(outgoing)} outgoing "
          f"-> {kept} new candidates (excluded {len(per_source_counts) - kept} self/seed/SG1)")

print(f"\nRaw SG2 amendment-based candidate pool: {len(pool)} distinct Acts")
print(f"Total exclusions (self-reference / seed / already in SG1): {len(excluded_self_or_seed)}")

ranked = sorted(pool.items(), key=lambda kv: -kv[1]["combined_score"])
print(f"\n{'Rank':<5}{'Act':<55}{'Score':<8}{'# SG1 Acts linking to it'}")
for i, (norm_name, info) in enumerate(ranked[:40], 1):
    print(f"{i:<5}{info['display_name'][:53]:<55}{info['combined_score']:<8}{len(info['linked_from'])}")

Path(OUT_DIR / "sg2_amendment_candidates.json").write_text(
    json.dumps([{"act": info["display_name"], **{k: v for k, v in info.items() if k != "display_name"}}
                for _, info in ranked], indent=2, ensure_ascii=False),
    encoding="utf-8"
)
print(f"\nSaved: {OUT_DIR / 'sg2_amendment_candidates.json'}")