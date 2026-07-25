"""
Checks what tags actually exist in the downloaded XML,
so Stage 2's parser is built against reality, not assumptions.
"""

from lxml import etree
from pathlib import Path
from collections import Counter

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

print("Root tag:", root.tag)
print("Root attributes:", dict(root.attrib))
print()


def local_name(tag):
    # Strips the namespace prefix (e.g. "{some-url}section" -> "section")
    return tag.split("}")[-1] if "}" in tag else tag


tag_counts = Counter(local_name(el.tag) for el in root.iter())

print(f"Found {len(tag_counts)} distinct tag types. Top 30 by frequency:")
for tag, count in tag_counts.most_common(30):
    print(f"  {tag}: {count}")