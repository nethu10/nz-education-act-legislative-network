"""
Look at the raw XML structure for a provision that Stage 2 parsed as
having empty text, to find the actual structural reason — before
guessing at a fix.
"""

from lxml import etree
from pathlib import Path

xml_path = Path("data/raw/education_and_training_act_2020.xml")
tree = etree.parse(str(xml_path))
root = tree.getroot()

target_id = "LMS274559"  # "Ministerial approval required to apply for licence"

for el in root.iter():
    if el.get("id") == target_id:
        xml_str = etree.tostring(el, pretty_print=True, encoding="unicode")
        print(xml_str[:3000])
        break
else:
    print(f"{target_id} not found by direct id search.")