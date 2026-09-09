"""
Check whether any headings are silently truncated by <insertwords>
appearing mid-heading (not just at the very start, which produces the
6 fully-missing cases already found) -- comparing the naive .text
extraction against a full itertext() extraction for every heading in
the source XML.
"""

from lxml import etree
from pathlib import Path

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def full_text(el):
    import re
    raw = " ".join(el.itertext())
    return re.sub(r"\s+", " ", raw).strip()

mismatches = []
for el in root.iter():
    if local_name(el.tag) != "heading":
        continue
    naive = (el.text or "").strip()
    full = full_text(el)
    if naive != full:
        mismatches.append((el.getparent().get("id"), naive, full))

print(f"Total headings checked with a mismatch between naive and full extraction: {len(mismatches)}")
for parent_id, naive, full in mismatches[:20]:
    print(f"\n  id={parent_id}")
    print(f"    naive (.text): {naive!r}")
    print(f"    full (correct): {full!r}")