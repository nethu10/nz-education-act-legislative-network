"""
Shows the text surrounding a few <extref> tags (not just the tag itself),
to see whether the target Act's name appears as plain text right next to
the tag -- the usual legal-drafting pattern is "section 27B of the
Companies Act 1993", where only "section 27B" is wrapped in the tag and
the Act name sits in plain text beside it.
"""
import re

XML_PATH = "data/raw/sg2_targets/act_1975_114.xml"

with open(XML_PATH, encoding="utf-8") as f:
    xml = f.read()

CONTEXT = 150  # characters before/after each match

for m in re.finditer(r"<extref[^>]*>.*?</extref>", xml):
    start = max(0, m.start() - CONTEXT)
    end = min(len(xml), m.end() + CONTEXT)
    snippet = xml[start:end]
    print("..." + snippet + "...")
    print("=" * 80)