"""
sg4_filenames.py

Filename-derivation helper for SG4, same philosophy as sg3_filenames.py.

The SG4 filename-collision audit (data/processed/sg4_collision_full_audit.md)
was originally run against the COMBINED SG2+SG3+SG4 identifier sets, which
conflated three different situations -- see audit_fix_08's docstring for the
full breakdown. After separating them out, exactly 14 pairs are genuine
intra-SG4 collisions: two different real documents, independently present
in SG4's own candidate list, that collide on the same `{year}_{number}.xml`
because SG4 mixes public Acts, local Acts, and several secondary-legislation
subtypes (regulation/rule/order), each with its own independent numbering
series within a year -- the same root cause as SG3's 6 collisions.

Fix: identical approach to SG3_FILENAME_OVERRIDES -- keep the plain
`{year}_{number}.xml` name for whichever side is already correctly saved
under it on disk, and give ONLY the other (previously missing/overwritten)
side a disambiguated name. Suffixes follow SG3's convention: "_public" /
"_local" for Acts, "_sl" (secondary legislation, generic across
regulation/rule/order) for everything else.

All 14 real documents behind these overrides were confirmed live
(canonical page title + act.type/sr.type attribute on the actual XML,
or direct fetch for the still-missing side) -- see
sg4_collision_full_audit.md and audit_fix_08 for the per-pair evidence.
"""
import json
from pathlib import Path

# act name (exact string in sg4_act_identifiers.json) -> override filename.
# Only the previously-missing/overwritten side of each of the 14 known
# collisions needs an entry; the surviving side keeps its plain filename.
SG4_FILENAME_OVERRIDES = {
    "Fisheries (Amateur Fishing) Amendment Regulations 2024": "2024_27_sl.xml",
    "Fair Trading (Gift Card Expiry) Amendment Act 2024": "2024_35_public.xml",
    "Criminal Procedure Amendment Rules 2025": "2025_78_sl.xml",
    "Fisheries (Amateur Fishing) Amendment Regulations 2014": "2014_16_sl.xml",
    "Radio New Zealand Amendment Act 2016": "2016_13_public.xml",
    "Public Service (Ministry for Cities, Environment, Regions, and Transport) Order 2026": "2026_6_sl.xml",
    "Electricity Industry (Enforcement) Amendment Regulations 2012": "2012_73_sl.xml",
    "War Pensions Amendment Regulations (No 2) 2010": "2010_86_sl.xml",
    "Christchurch District Drainage Amendment Act 1979": "1979_3_local.xml",
    "Securities Markets Amendment Act 2002": "2002_44_public.xml",
    "Overseas Investment Amendment Regulations 2016": "2016_101_sl.xml",
    "War Pensions Amendment Regulations 2014": "2014_59_sl.xml",
    "Fire Service Amendment Act 1996": "1996_122_public.xml",
    "Misuse of Drugs (Classification and Presumption of Supply—25B-NBOMe, 25C-NBOMe, and 25I-NBOMe) Order 2016": "2016_89_sl.xml"
}


def filename_for_sg4(entry):
    """entry is one row from sg4_act_identifiers.json."""
    name = entry["act"]
    if name in SG4_FILENAME_OVERRIDES:
        return SG4_FILENAME_OVERRIDES[name]
    return f"{entry['year']}_{entry['number']}.xml"


def find_collisions(identifier_entries):
    """Returns {filename: [entries]} for any filename claimed by >1 entry,
    after applying filename_for_sg4(). Empty dict == no collisions."""
    from collections import defaultdict
    by_fname = defaultdict(list)
    for a in identifier_entries:
        if not a.get("resolved") or "year" not in a:
            continue  # unresolved entries have no year/number to derive a filename from
        by_fname[filename_for_sg4(a)].append(a)
    return {k: v for k, v in by_fname.items() if len(v) > 1}


if __name__ == "__main__":
    path = Path("data/processed/sg4_act_identifiers.json")
    ids = json.loads(path.read_text(encoding="utf-8"))
    collisions = find_collisions(ids)
    print(f"Checked {len(ids)} SG4 identifier entries with filename_for_sg4()")
    if collisions:
        print(f"REMAINING COLLISIONS: {len(collisions)}")
        for fname, group in collisions.items():
            print(f"  {fname}: {[a['act'] for a in group]}")
    else:
        print("No collisions -- every entry maps to its own distinct filename.")
