"""
Shows a few complete <citation jurisdiction="nz">...</citation> blocks in
full (not truncated), including ones that contain a <leg-title> tag, to
see the exact schema before writing the citation-extraction parser.
"""
import re

XML_PATH = "data/raw/sg2_targets/act_1975_114.xml"

with open(XML_PATH, encoding="utf-8") as f:
    xml = f.read()

blocks = re.findall(r'<citation jurisdiction="nz">.*?</citation>', xml)
print(f"Found {len(blocks)} <citation jurisdiction=\"nz\"> blocks total")
print()

# show a few plain ones (no leg-title)
plain = [b for b in blocks if "<leg-title>" not in b][:4]
print("--- Without leg-title ---")
for b in plain:
    print(b)
    print()

# show a few with leg-title, if any
with_title = [b for b in blocks if "<leg-title>" in b][:4]
print(f"--- With leg-title ({len(with_title)} found in first pass) ---")
for b in with_title:
    print(b)
    print()