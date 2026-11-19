"""
sg3_filenames.py

Shared filename-derivation helper for SG3 (and future SG4/SG5) XML files.

Plain `{year}_{number}.xml` (the scheme SG1/SG2 used) breaks for SG3
because public Acts, local Acts, and secondary-legislation subtypes each
have their OWN independent numbering sequence, so two unrelated real
documents can share a (year, number) pair. Confirmed 6 live collisions in
the 872-document SG3 pool (see sg3_filename_collision_findings.md) -- in
each case exactly one side's real content was on disk and the other's was
silently missing.

Fix: keep the plain `{year}_{number}.xml` name for the side that's
already correctly saved under it (no need to touch ~860 files that were
never ambiguous), and give ONLY the other, previously-overwritten side of
each collision a disambiguated name. SG3_FILENAME_OVERRIDES is therefore
a short, explicit, hand-verified list, not a blanket renaming rule --
simplest fix that actually matches what's really on disk today.

For SG4/SG5: re-run find_collisions() below against the FULL combined
identifier set before trusting plain `{year}_{number}.xml` again -- it is
not a guarantee, just something that happened to hold for SG1 and SG2.
"""
import json
from pathlib import Path

# act name (exact string in *_act_identifiers.json) -> override filename.
# Only the previously-overwritten side of each of the 6 known collisions
# needs an entry; the surviving side keeps its existing plain filename.
SG3_FILENAME_OVERRIDES = {
    "Waitakere Ranges Heritage Area Act 2008 (2008 No 1 (L))": "2008_1_local.xml",
    "Public Trust Act Commencement Order 2002": "2002_11_sl.xml",
    "Tauranga District Council (Route K Toll) Empowering Act 2000": "2000_1_local.xml",
    "Health and Safety at Work (Mining Operations and Quarrying Operations) Regulations 2016": "2016_17_sl.xml",
    "Children, Young Persons, and Their Families Amendment Act 2001": "2001_3_public.xml",
    "United Nations (Iran—Joint Comprehensive Plan of Action) Regulations 2016": "2016_9_sl.xml",
}


def filename_for_sg3(entry):
    """entry is one row from sg3_act_identifiers.json."""
    name = entry["act"]
    if name in SG3_FILENAME_OVERRIDES:
        return SG3_FILENAME_OVERRIDES[name]
    return f"{entry['year']}_{entry['number']}.xml"


def find_collisions(identifier_entries):
    """Returns {filename: [entries]} for any filename claimed by >1 entry,
    after applying filename_for_sg3(). Empty dict == no collisions."""
    from collections import defaultdict
    by_fname = defaultdict(list)
    for a in identifier_entries:
        by_fname[filename_for_sg3(a)].append(a)
    return {k: v for k, v in by_fname.items() if len(v) > 1}


if __name__ == "__main__":
    path = Path("data/processed/sg3_act_identifiers.json")
    ids = json.loads(path.read_text(encoding="utf-8"))
    collisions = find_collisions(ids)
    print(f"Checked {len(ids)} SG3 identifier entries with filename_for_sg3()")
    if collisions:
        print(f"REMAINING COLLISIONS: {len(collisions)}")
        for fname, group in collisions.items():
            print(f"  {fname}: {[a['act'] for a in group]}")
    else:
        print("No collisions -- every entry maps to its own distinct filename.")
