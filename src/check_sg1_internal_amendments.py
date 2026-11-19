"""
Check whether the 37 SG1 Acts amend/are amended by each other directly --
the amendment-side counterpart to check_sg1_internal_citations.py.

sg2_step2_amendment_relationships.py already proved this gap exists: its
own pool-construction step explicitly excludes any candidate whose
normalized name is `in sg1_names_norm` (line 122) -- meaning every
amendment relationship between two SG1 Acts was silently discarded right
at the point of extraction and never written to any file. This reuses
the exact same extraction logic (extract_outgoing_amendments /
extract_amendment_records, reading <schedule.amendments.group2> and
<history-note> elements) against the same 37 XML files in
data/raw/sg2_targets/, but keeps SG1-internal matches instead of
excluding them, and preserves edge direction.
"""
import json
import re
from collections import defaultdict
from pathlib import Path
from lxml import etree

SG1_PATH = Path("data/processed/sg1_final_list.json")
TARGETS_DIR = Path("data/raw/sg2_targets")

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
def normalize(name):
    if not name:
        return name
    name = name.replace("\u2019", "'").replace("\u2018", "'")
    m = CITE_PATTERN.match(name.strip())
    base = m.group(1).strip() if m else name.strip()
    return base.lower()

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

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def element_text(el):
    if el is None:
        return ""
    raw = " ".join(el.itertext())
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"\s+([,.:;)])", r"\1", cleaned)
    return cleaned

def extract_amendment_records(root):
    """Other Acts that amend THIS document -- amending_act -> this Act."""
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
    """Acts THIS document amends -- this Act -> target_act."""
    records = []
    for group2 in root.iter():
        if local_name(group2.tag) != "schedule.amendments.group2":
            continue
        heading_el = group2.find("heading")
        target_act = element_text(heading_el) if heading_el is not None else None
        for para in group2.findall("para"):
            records.append({"target_act": target_act, "text": element_text(para)})
    return records


def main():
    sg1 = json.loads(SG1_PATH.read_text(encoding="utf-8"))
    sg1_norm_to_display = {normalize(a["act"]): a["act"] for a in sg1}
    sg1_norms = set(sg1_norm_to_display)

    edges = []  # (source_display, target_display, count, signal)
    missing_files = []

    for a in sg1:
        fname = filename_for(a["act"])
        path = TARGETS_DIR / fname if fname else None
        if not path or not path.exists():
            missing_files.append((a["act"], fname))
            continue

        source_display = a["act"]
        source_norm = normalize(source_display)

        try:
            tree = etree.parse(str(path))
            root = tree.getroot()
        except Exception as e:
            print(f"  PARSE FAILED: {path.name} ({type(e).__name__}: {e})")
            continue

        outgoing = extract_outgoing_amendments(root)
        incoming = extract_amendment_records(root)

        out_counts = defaultdict(int)
        for r in outgoing:
            if r["target_act"]:
                out_counts[r["target_act"]] += 1
        for target_raw, count in out_counts.items():
            t_norm = normalize(target_raw)
            if t_norm in sg1_norms and t_norm != source_norm:
                edges.append((source_display, sg1_norm_to_display[t_norm], count, "outgoing"))

        in_counts = defaultdict(int)
        for r in incoming:
            if r["amending_act"]:
                in_counts[r["amending_act"]] += 1
        for amending_raw, count in in_counts.items():
            a_norm = normalize(amending_raw)
            if a_norm in sg1_norms and a_norm != source_norm:
                edges.append((sg1_norm_to_display[a_norm], source_display, count, "incoming"))

    print(f"SG1 Acts processed: {len(sg1) - len(missing_files)} / {len(sg1)}")
    if missing_files:
        print(f"Missing XML files: {missing_files}")

    print(f"\nRaw SG1-internal amendment signals found: {len(edges)} "
          f"({sum(1 for e in edges if e[3]=='outgoing')} via outgoing schedules, "
          f"{sum(1 for e in edges if e[3]=='incoming')} via history-notes)")

    # merge outgoing+incoming detections of the same (source,target) pair
    merged = defaultdict(int)
    for source, target, count, _ in edges:
        merged[(source, target)] += count

    print(f"\nDistinct SG1-internal amendment edges (deduplicated, directed): {len(merged)}")
    acts_involved = {n for pair in merged for n in pair}
    print(f"SG1 Acts with at least one internal amendment edge: {len(acts_involved)} / {len(sg1)}")

    print("\nAll SG1-internal amendment edges (source -> target, count):")
    for (source, target), count in sorted(merged.items(), key=lambda kv: -kv[1]):
        print(f"  {source}  ->  {target}   ({count}x)")

    out_path = Path("data/processed/sg1_internal_amendment_edges.json")
    out_path.write_text(json.dumps(
        [{"source": s, "target": t, "count": c} for (s, t), c in merged.items()],
        indent=2, ensure_ascii=False
    ), encoding="utf-8")
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()