"""
Confirm the 13 target Acts share the same XML schema as the seed Act,
before reusing Stage 2's parsing logic on them. Starts with the
smallest file (a university Act) for a quick, safe check.
"""

from lxml import etree
from pathlib import Path
from collections import Counter

xml_path = Path("data/raw/stage6_targets/1961_49.xml")  # University of Canterbury Act, smallest file
tree = etree.parse(str(xml_path))
root = tree.getroot()

print("Root tag:", root.tag)
print("Root attributes:", dict(root.attrib))

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

tag_counts = Counter(local_name(el.tag) for el in root.iter())
print(f"\nFound {len(tag_counts)} distinct tag types. Top 15:")
for tag, count in tag_counts.most_common(15):
    print(f"  {tag}: {count}")