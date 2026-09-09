"""
Check the raw XML directly for one missing-heading provision, to see
whether the <heading> tag is genuinely absent from the source, or
whether Stage 2's parser is missing it despite it being present.
"""

from lxml import etree
from pathlib import Path

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

target_id = "LMS172214"

for el in root.iter():
    if el.get("id") == target_id:
        xml_str = etree.tostring(el, pretty_print=True, encoding="unicode")
        print(xml_str[:800])
        break
else:
    print(f"{target_id} not found in the XML.")