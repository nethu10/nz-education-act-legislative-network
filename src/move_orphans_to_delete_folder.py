"""
move_orphans_to_delete_folder.py  (run from the project root on the Mac)

Moves 24 byte-identical duplicate raw XML files into _to_delete/ (nothing is
permanently deleted). Before moving each file it checks that an identical copy
exists in the layer folder that keeps it; otherwise it skips the file.
"""
import filecmp, shutil
from pathlib import Path
RAW = Path("data/raw"); OUT = Path("_to_delete")
# (folder, file) -> folder holding the identical copy that is kept
SG3 = "1957_87 1974_66 1975_9 1978_103 1988_4 1989_157 1989_75 1991_69 1995_16 1995_39 1999_82 2002_38 2002_54 2002_84 2004_90 2008_64 2011_5 2017_24".split()
JOBS = [("sg3_targets", n, "sg2_targets") for n in SG3]
JOBS += [("sg3_targets", "1995_31", "sg4_targets"), ("sg3_targets", "2020_40", "sg4_targets")]
JOBS += [("sg4_targets", n, "sg3_targets") for n in ("1992_55", "1996_39", "2016_17")]
JOBS += [("sg4_targets", "1994_3", "sg2_targets")]
moved = 0
for folder, n, keep in JOBS:
    src, kept = RAW / folder / f"{n}.xml", RAW / keep / f"{n}.xml"
    if not src.exists():
        print("missing (already moved?)", src); continue
    if not kept.exists() or not filecmp.cmp(src, kept, shallow=False):
        print("SKIP - no identical kept copy:", src); continue
    dest = OUT / folder; dest.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest / src.name)); moved += 1
print(f"moved {moved} of {len(JOBS)} files into {OUT}/")
