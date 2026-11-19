"""
Quick diagnostic: shows the raw <extref> tags (including their inner
text, not just the href) from one target Act's XML, to check whether the
readable Act name/citation is already sitting inside the tag rather than
needing to be resolved from the href id over the network.
"""
import re

XML_PATH = "data/raw/sg2_targets/act_1975_114.xml"

with open(XML_PATH, encoding="utf-8") as f:
    xml = f.read()

matches = re.findall(r"<extref[^>]*>.*?</extref>", xml)

print(f"Found {len(matches)} <extref> tags in {XML_PATH}")
print()
for m in matches[:10]:
    print(m)
    print()