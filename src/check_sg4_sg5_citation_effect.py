"""
check_sg4_sg5_citation_effect.py

Diagnostic only (writes one JSON, changes no existing file).

QUESTION: SG4 and SG5 were admitted on amendment operations only
(sg2_step26 / sg4_step06 count history-note and schedule.amendments.group2
hits; they never count <citation> mentions). SG1-SG3 used amendment +
citation. How many instruments would have been admitted to SG4 / SG5 if
citations had been counted too (same cutoff, same cleaning rules)?

METHOD (reuses the project's own logic, unchanged):
  - normalize() / RENAME_MAP / resolve_canonical(): from sg4_step06
  - citation resolution (leg-title / extref text match / anaphoric):
    from sg2_step12_extract_sg3_citations.py
  - amendment score: read from the existing pool file
        SG4: data/processed/sg3_new_candidates_seen.json (sources = SG3 Acts)
        SG5: data/processed/sg4_new_candidates_seen.json (sources = SG4 Acts)
  - citation score: count of <citation> mentions of the candidate in the
    raw XML of the SOURCE layer (SG3 for SG4, SG4 for SG5)
  - candidates already in an earlier layer, the source itself, and
    "Section N" / "Clause N" pseudo-candidates are excluded, as in sg4_step06

Run from the project root:
    python src/check_sg4_sg5_citation_effect.py            # both layers
    python src/check_sg4_sg5_citation_effect.py sg4        # one layer
"""
import json
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path
from lxml import etree

CUTOFF = 6
SEED = "Education and Training Act 2020"

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
GENERIC_TRAILING_PAREN = re.compile(r"^(.+?)\s*\([^()]*\)\s*$")
MACRON_MAP = str.maketrans("āēīōūĀĒĪŌŪ", "aeiouAEIOU")
SECTION_CLAUSE_RE = re.compile(r"^(section|clause)\s+\d+[a-z]*$", re.IGNORECASE)
ACT_NAME_PATTERN = re.compile(
    r"of\s+(?:Part\s+\S+\s+of\s+)?(?:the\s+)?"
    r"([A-Z][A-Za-z0-9,’'\-\(\) ]*?\b(?:Act|Rules?|Regulations?|Order|Notice|Bylaw)\s+\d{4})\b"
)

RENAME_MAP = {
    "Schedule 32 of the Social Security Act 1964": "Social Security Act 1964",
    "Schedule 1 of the New Zealand Superannuation and Retirement Income Act 2001":
        "New Zealand Superannuation and Retirement Income Act 2001",
    "Schedule 1AA of the New Zealand Superannuation and Retirement Income Act 2001":
        "New Zealand Superannuation and Retirement Income Act 2001",
    "Injury Prevention, Rehabilitation, and Compensation Act 2001": "Accident Compensation Act 2001",
    "Healthy Futures (Pae Ora) Act 2022": "Pae Ora (Healthy Futures) Act 2022",
    "Housing Restructuring and Tenancy Matters Act 1992": "Public and Community Housing Management Act 1992",
    "State Sector Act 1988 (RS Vol 33, p 715)": "State Sector Act 1988",
    "New Zealand Act 2021": "Reserve Bank of New Zealand Act 2021",
    "Schedule 1 of the Ombudsmen Act 1975": "Ombudsmen Act 1975",
    "Oranga Tamariki System Legislation Amendment Act 2025":
        "Oversight of Oranga Tamariki System Legislation Amendment Act 2025",
    "Waitangi Day and ANZAC Day) Amendment Act 2013":
        "Holidays (Full Recognition of Waitangi Day and ANZAC Day) Amendment Act 2013",
    "Support Workers (Pay Equity) Settlements Act 2017":
        "Care and Support Workers (Pay Equity) Settlement Act 2017",
    "Schedule 2 of the Public Service Act 2020": None,
    "Schedule 6 of the Public Service Act 2020": None,
    "Schedule 1 of the Privacy Act 2020": None,
    "Family Courts Act 1980": "Family Court Act 1980",
    "District Courts Rules 2014": "District Court Rules 2014",
    "Family Courts Rules 2002": "Family Court Rules 2002",
    "Sexual Violence (Strengthening Legal Protections) Legislation Act 2025":
        "Victims of Sexual Violence (Strengthening Legal Protections) Legislation Act 2025",
    "Family Violence (Strengthening Legal Protections) Legislation Act 2025":
        "Victims of Family Violence (Strengthening Legal Protections) Legislation Act 2025",
}


def normalize(name):
    if not name:
        return name
    name = name.strip()
    if name.endswith("."):
        name = name[:-1].strip()
    name = name.replace("’", "'").replace("‘", "'")
    while True:
        m = CITE_PATTERN.match(name)
        if m:
            name = m.group(1).strip()
            continue
        m2 = GENERIC_TRAILING_PAREN.match(name)
        if m2:
            name = m2.group(1).strip()
            continue
        break
    name = name.translate(MACRON_MAP)
    return re.sub(r"\s+", " ", name).strip()


def resolve_canonical(name):
    n = normalize(name)
    return RENAME_MAP[n] if n in RENAME_MAP else n


def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def element_text(el):
    if el is None:
        return ""
    return re.sub(r"\s+", " ", " ".join(el.itertext())).strip()


def resolve_citation(cit_el):
    leg_title, has_extref = None, False
    for child in cit_el.iter():
        ln = local_name(child.tag)
        if ln == "leg-title" and leg_title is None:
            leg_title = child
        elif ln == "extref":
            has_extref = True
    if leg_title is not None:
        return element_text(leg_title), "leg_title"
    if not has_extref:
        return None, "internal_only"
    full = element_text(cit_el)
    if re.search(r"\bthis Act\b", full):
        return None, "self"
    m = ACT_NAME_PATTERN.search(full)
    if m:
        return m.group(1).strip(), "text_match"
    if re.search(r"\bthat Act\b", full) or re.search(r"\bthe Act\b", full):
        return None, "anaphoric"
    return None, "unresolved"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


P = Path("data/processed")
LAYERS = {
    # layer: (pool file, source raw dir, source identifiers, earlier-layer lists, source-layer list)
    "sg4": dict(pool=P / "sg3_new_candidates_seen.json", raw=Path("data/raw/sg3_targets"),
                ids=P / "sg3_act_identifiers.json",
                earlier=["sg1_final_list", "sg2_final_list", "sg3_final_list"]),
    "sg5": dict(pool=P / "sg4_new_candidates_seen.json", raw=Path("data/raw/sg4_targets"),
                ids=P / "sg4_act_identifiers.json",
                earlier=["sg1_final_list", "sg2_final_list", "sg3_final_list", "sg4_final_list"]),
}


def run(layer):
    cfg = LAYERS[layer]
    print("=" * 70)
    print(f"{layer.upper()}: sources in {cfg['raw']}, amendment pool {cfg['pool'].name}")
    earlier = {normalize(SEED)}
    for name in cfg["earlier"]:
        earlier |= {normalize(a["act"]) for a in load(P / f"{name}.json")}

    # (year, number) -> source name (one filename can be disambiguated, e.g. _public/_sl: map by prefix)
    lookup = defaultdict(list)
    for d in load(cfg["ids"]):
        if d.get("resolved"):
            lookup[(str(d.get("year")), str(d.get("number")))].append(d["act"])

    cit = defaultdict(lambda: {"n": 0, "sources": set()})
    stats, scanned, unmapped = Counter(), 0, 0
    for xp in sorted(cfg["raw"].glob("*.xml")):
        m = re.match(r"_?(~?\d{4})_(~?\d+)", xp.name)
        if not m or (m.group(1), m.group(2)) not in lookup:
            unmapped += 1
            continue
        src_name = lookup[(m.group(1), m.group(2))][0]
        if len(lookup[(m.group(1), m.group(2))]) > 1:
            # shared year/number across series: guess by suffix, else first
            for nm in lookup[(m.group(1), m.group(2))]:
                tag = xp.stem.split("_")[-1]
                if tag in ("public", "local", "sl") and tag[:3] in nm.lower():
                    src_name = nm
        src_norm = normalize(src_name)
        try:
            root = etree.parse(str(xp)).getroot()
        except Exception as e:
            print("  parse failed", xp.name, e)
            continue
        scanned += 1
        last = None
        for el in root.iter():
            ln = local_name(el.tag)
            if ln == "prov":
                last = None
                continue
            if ln != "citation" or el.get("jurisdiction") != "nz":
                continue
            name, kind = resolve_citation(el)
            stats[kind] += 1
            target = None
            if kind in ("leg_title", "text_match"):
                last = name
                target = name
            elif kind == "anaphoric" and last:
                target = last
            if not target:
                continue
            c = resolve_canonical(target)
            if c is None or c == src_norm or c in earlier or SECTION_CLAUSE_RE.match(c):
                continue
            cit[c]["n"] += 1
            cit[c]["sources"].add(src_name)
    print(f"  scanned {scanned} source files; {unmapped} files not mapped; citation kinds: {dict(stats)}")

    # amendment scores from the existing pool, same filters
    amend = {}
    for e in load(cfg["pool"]):
        c = resolve_canonical(e["act"])
        if c is None or c in earlier or SECTION_CLAUSE_RE.match(c):
            continue
        amend[c] = amend.get(c, 0) + e["combined_score"]

    names = set(amend) | set(cit)
    rows = []
    for c in names:
        a, k = amend.get(c, 0), cit.get(c, {"n": 0, "sources": set()})["n"]
        rows.append(dict(act=c, amendment=a, citation=k, combined=a + k,
                         citing_sources=len(cit.get(c, {"sources": set()})["sources"])))
    amend_in = {r["act"] for r in rows if r["amendment"] >= CUTOFF}
    comb_in = {r["act"] for r in rows if r["combined"] >= CUTOFF}
    gained = sorted([r for r in rows if r["act"] in comb_in - amend_in], key=lambda r: -r["combined"])
    cit_only = [r for r in gained if r["amendment"] == 0]

    print(f"  candidates seen (amendment pool + citation scan): {len(rows)}")
    print(f"  admitted at >= {CUTOFF}, amendment only (what was done): {len(amend_in)}")
    print(f"  admitted at >= {CUTOFF}, amendment + citation:           {len(comb_in)}")
    print(f"  extra instruments citations would add:                   {len(gained)}  "
          f"({100*len(gained)/max(1,len(amend_in)):.1f}% of the amendment-only layer)")
    print(f"     of which have NO amendment link at all:               {len(cit_only)}")
    print(f"  dropped by adding citations: 0 (scores can only rise)")
    bands = Counter()
    for r in gained:
        bands["6-9" if r["combined"] < 10 else "10-19" if r["combined"] < 20 else "20+"] += 1
    print(f"  extra, by combined score: {dict(bands)}")
    print("  Top 25 extra instruments (combined = amendment + citation):")
    for r in gained[:25]:
        print(f"    {r['act'][:70]:70s} A={r['amendment']:>3} C={r['citation']:>3} "
              f"(cited by {r['citing_sources']} sources)")
    return dict(layer=layer, amendment_only=len(amend_in), with_citations=len(comb_in),
                extra=len(gained), extra_no_amendment=len(cit_only), top=gained[:100], all=gained)


if __name__ == "__main__":
    which = sys.argv[1:] or ["sg4", "sg5"]
    out = [run(w) for w in which]
    Path("outputs").mkdir(exist_ok=True)
    with open("outputs/sg4_sg5_citation_effect.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("\nSaved -> outputs/sg4_sg5_citation_effect.json")
