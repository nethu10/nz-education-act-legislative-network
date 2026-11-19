"""
sg3_step02_build_typed_edges.py

Generalizes sg2_step36_build_typed_edges_v2.py to SG3 -- one layer further
out, same architecture. Produces sg3_typed_amendment_edges.json and
sg3_typed_citation_edges.json, covering:
  - SG3-internal edges (both ends are SG3 Acts), and
  - (seed/SG1/SG2) <-> SG3 boundary edges.

Pairs where both ends are within seed/SG1/SG2 are deliberately EXCLUDED --
those are already captured, verified, and published in sg1_typed_*.json
(seed/SG1-only) and sg2_typed_*.json (everything else up to SG2, via the
step36 fix). Re-deriving them here would duplicate that work, so this
script instead uses them as a correctness check: the pairs it (re-)finds
within that smaller universe are compared against the union of both
published files and must match before the SG3-only results are trusted.

NO-XML MEMBER REGISTRATION (carried forward from sg2_step36, same bug class
avoided from the start this time): every final-list member's name is
registered in `all_norms` regardless of whether local XML exists --
`has_xml=False` members (SG3's 21 agency-drafted Land Transport Rules, plus
SG2's 1) can never be a parse SOURCE, but correctly resolve as an edge
TARGET when some other member's own XML names them (schedule heading or
citation). Confirmed this matters in practice: fixing it for SG2's 1
no-XML entry recovered 2 real edges that step35 had silently dropped (see
sg2_no_xml_gap_investigation_findings.md). The NAME_VARIANT_ALIASES map is
carried forward unchanged for the same reason -- it resolves a real
heading-text variant found inside 2008_47.xml's own XML, which this
script's extraction pass also parses.

A genuine cross-layer duplicate was also found and removed during that
investigation: SG3's own list had independently (re-)discovered the exact
same no-XML SG2 entry under a different name string
("Land Transport Rule: Frontal Impact 2001 (32006/1)", same URL/year/number
as the SG2 entry) -- see audit_fix_04_remove_frontal_impact_cross_layer_
duplicate.py. SG3's final list is therefore 871, not 872, by the time this
script runs.

Filename resolution for SG3 uses the shared filename_for_sg3() helper
(handles the 6 known collision overrides; see sg3_filenames.py) --
verified exact 850/850 match against the real sg3_targets/ directory
listing before writing this script.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, "src")
from sg3_filenames import filename_for_sg3

DATA = Path("data/processed")
RAW = Path("data/raw")
SG1_TARGETS_DIR = RAW / "sg1_targets"
SG2_TARGETS_DIR = RAW / "sg2_targets"
SG3_TARGETS_DIR = RAW / "sg3_targets"
SEED_XML = RAW / "education_and_training_act_2020.xml"
SEED_NAME = "Education and Training Act 2020"

SG1_PATH = DATA / "sg1_final_list.json"
SG2_PATH = DATA / "sg2_final_list.json"
SG2_IDS_PATH = DATA / "sg2_act_identifiers.json"
SG3_PATH = DATA / "sg3_final_list.json"
SG3_IDS_PATH = DATA / "sg3_act_identifiers.json"
SG1_TYPED_AMEND_PATH = DATA / "sg1_typed_amendment_edges.json"
SG1_TYPED_CITE_PATH = DATA / "sg1_typed_citation_edges.json"
SG2_TYPED_AMEND_PATH = DATA / "sg2_typed_amendment_edges.json"
SG2_TYPED_CITE_PATH = DATA / "sg2_typed_citation_edges.json"

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")

# Narrow, hand-verified name-variant alias -- carried forward from
# sg2_step36 (same real heading-text variant, same reason it's needed).
NAME_VARIANT_ALIASES = {
    "land transport rule: frontal impact 2001 (32006/1)": "land transport rule 32006/1: frontal impact 2001",
}


def normalize(name):
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'").replace("\xa0", " ")
    # 2026-10-07 NBSP fix: fold non-breaking spaces / whitespace runs / trailing period
    # (names like "Finance Act (No\xa02) 1988" previously never matched XML text).
    name = re.sub(r"\s+", " ", name).strip().rstrip(".").strip()
    m = CITE_PATTERN.match(name.strip())
    base = m.group(1).strip() if m else name.strip()
    norm = base.lower()
    return NAME_VARIANT_ALIASES.get(norm, norm)


def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def element_text(el):
    if el is None:
        return ""
    raw = "".join(el.itertext())
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"\s+([,.:;)])", r"\1", cleaned)
    return cleaned


def filename_for_sg1(act_field):
    m = CITE_PATTERN.match(act_field.strip())
    if not m:
        return None
    cite = m.group(2)
    if cite.startswith(("SR", "LI")):
        ym = re.match(r"(?:SR|LI)\s+(\d{4})/(\d+)", cite)
    else:
        ym = re.match(r"(\d{4})\s+No\s+(\d+)", cite)
    if not ym:
        return None
    year, number = ym.groups()
    return f"{year}_{number}.xml"


OPERATION_BUCKETS = [
    (re.compile(r"^insert", re.I), "insert"),
    (re.compile(r"^repeal", re.I), "repeal"),
    (re.compile(r"^replace", re.I), "replace"),
    (re.compile(r"^substitut", re.I), "substitute"),
    (re.compile(r"^add", re.I), "add"),
    (re.compile(r"^revok", re.I), "revoke"),
    (re.compile(r"^renumber", re.I), "renumber"),
    (re.compile(r"^editorial", re.I), "editorial"),
    (re.compile(r"^brought into force", re.I), "commencement"),
    (re.compile(r"^(further )?amend", re.I), "amend"),
]


def normalize_operation(raw):
    if not raw:
        return "other"
    text = raw.strip()
    text = re.sub(r"\s*\(with effect on[^)]*\)\s*$", "", text, flags=re.I).strip()
    for pattern, bucket in OPERATION_BUCKETS:
        if pattern.match(text):
            return bucket
    return "other"


def classify_outgoing_text(text):
    t = text.lower()
    if re.search(r"\brepeal(s|ed|ing)?\b", t):
        return "repeal"
    if re.search(r"\binsert(s|ed|ing)?\b", t):
        return "insert"
    if re.search(r"\breplace(s|d|ing)?\b", t):
        return "replace"
    if re.search(r"\bomit(s|ted|ting)?\b", t):
        return "omit"
    return "amend (other)"


# ---------------------------------------------------------------------
# Build the full member universe: seed + SG1 (37) + SG2 (421) + SG3 (871).
# Every final-list entry is registered regardless of has_xml.
# ---------------------------------------------------------------------
sg1 = json.loads(SG1_PATH.read_text(encoding="utf-8"))
sg2 = json.loads(SG2_PATH.read_text(encoding="utf-8"))
sg2_ids = json.loads(SG2_IDS_PATH.read_text(encoding="utf-8"))
sg3 = json.loads(SG3_PATH.read_text(encoding="utf-8"))
sg3_ids = json.loads(SG3_IDS_PATH.read_text(encoding="utf-8"))
sg2_id_by_name = {a["act"]: a for a in sg2_ids}
sg3_id_by_name = {a["act"]: a for a in sg3_ids}

members = [{"name": SEED_NAME, "path": SEED_XML, "group": "seed", "has_xml": True}]

no_xml_members = []
for a in sg1:
    fname = filename_for_sg1(a["act"])
    path = SG1_TARGETS_DIR / fname if fname else None
    has_xml = bool(path and path.exists())
    if not has_xml:
        no_xml_members.append(("sg1", a["act"], fname))
    members.append({"name": a["act"], "path": path, "group": "sg1", "has_xml": has_xml})

for a in sg2:
    ident = sg2_id_by_name.get(a["act"])
    fname = f"{ident['year']}_{ident['number']}.xml" if ident else None
    path = SG2_TARGETS_DIR / fname if fname else None
    has_xml = bool(path and path.exists())
    if not has_xml:
        no_xml_members.append(("sg2", a["act"], fname))
    members.append({"name": a["act"], "path": path, "group": "sg2", "has_xml": has_xml})

for a in sg3:
    ident = sg3_id_by_name.get(a["act"])
    fname = filename_for_sg3(ident) if ident else None
    path = SG3_TARGETS_DIR / fname if fname else None
    has_xml = bool(path and path.exists())
    if not has_xml:
        no_xml_members.append(("sg3", a["act"], fname))
    members.append({"name": a["act"], "path": path, "group": "sg3", "has_xml": has_xml})

name_norm_to_display = {normalize(m["name"]): m["name"] for m in members}
name_norm_to_group = {normalize(m["name"]): m["group"] for m in members}
all_norms = set(name_norm_to_display)

n_sg1_ok = sum(1 for m in members if m["group"] == "sg1" and m["has_xml"])
n_sg2_ok = sum(1 for m in members if m["group"] == "sg2" and m["has_xml"])
n_sg3_ok = sum(1 for m in members if m["group"] == "sg3" and m["has_xml"])
print(f"Member universe: seed (1) + SG1 ({n_sg1_ok}/{len(sg1)}) + SG2 ({n_sg2_ok}/{len(sg2)}) + "
      f"SG3 ({n_sg3_ok}/{len(sg3)}) = {len(members)} total registered names "
      f"({len(members) - len(no_xml_members)} parseable)")
if no_xml_members:
    print(f"Registered as valid edge TARGETS despite no local XML ({len(no_xml_members)}):")
    for group, name, fname in no_xml_members:
        print(f"  [{group}] {name}  (would-be filename: {fname})")

# ---------------------------------------------------------------------
# Pass 1: identical extraction to sg2_step36, over the wider union,
# skipping parsing (not registration) for has_xml=False members.
# ---------------------------------------------------------------------
incoming_amend_edges = defaultdict(Counter)
outgoing_signal_pairs = set()
outgoing_fallback_text = defaultdict(list)
citation_edges = defaultdict(int)

ACT_NAME_PATTERN = re.compile(
    r"of\s+(?:Part\s+\S+\s+of\s+)?(?:the\s+)?"
    r"([A-Z][A-Za-z0-9,’'\-\(\) ]*?\b(?:Act|Rules?|Regulations?|Order|Notice|Bylaw)\s+\d{4})\b"
)


def resolve_citation(cit_el):
    leg_title = None
    has_extref = False
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
    full_text = element_text(cit_el)
    if re.search(r"\bthis Act\b", full_text):
        return None, "self"
    m = ACT_NAME_PATTERN.search(full_text)
    if m:
        return m.group(1).strip(), "text_match"
    if re.search(r"\bthat Act\b", full_text) or re.search(r"\bthe Act\b", full_text):
        return None, "anaphoric"
    return None, "unresolved"


parse_failures = []
for member in members:
    if not member["has_xml"]:
        continue
    this_name = member["name"]
    this_norm = normalize(this_name)
    try:
        root = ET.parse(member["path"]).getroot()
    except Exception as e:
        parse_failures.append((this_name, str(e)))
        continue

    for el in root.iter():
        ln = local_name(el.tag)
        if ln == "history-note":
            op_el = el.find("amending-operation")
            aleg_el = el.find("amending-leg")
            operation_raw = op_el.text if op_el is not None else None
            amending_raw = element_text(aleg_el) if aleg_el is not None else None
            if not amending_raw:
                continue
            a_norm = normalize(amending_raw)
            if a_norm not in all_norms or a_norm == this_norm:
                continue
            source = name_norm_to_display[a_norm]
            bucket = normalize_operation(operation_raw)
            incoming_amend_edges[(source, this_name)][bucket] += 1

    for g2 in root.iter():
        if local_name(g2.tag) != "schedule.amendments.group2":
            continue
        heading_el = g2.find("heading")
        target_raw = element_text(heading_el) if heading_el is not None else None
        if not target_raw:
            continue
        t_norm = normalize(target_raw)
        if t_norm not in all_norms or t_norm == this_norm:
            continue
        target = name_norm_to_display[t_norm]
        paras = g2.findall("para")
        if paras:
            outgoing_signal_pairs.add((this_name, target))
            for p in paras:
                outgoing_fallback_text[(this_name, target)].append(element_text(p))

    for el in root.iter():
        ln = local_name(el.tag)
        if ln == "prov":
            last_named_act = None
        if ln == "citation" and el.get("jurisdiction") == "nz":
            cited_name, method = resolve_citation(el)
            if cited_name:
                c_norm = normalize(cited_name)
                if c_norm in all_norms and c_norm != this_norm:
                    target = name_norm_to_display[c_norm]
                    citation_edges[(this_name, target)] += 1
                last_named_act = cited_name
            elif method == "anaphoric" and last_named_act:
                c_norm = normalize(last_named_act)
                if c_norm in all_norms and c_norm != this_norm:
                    target = name_norm_to_display[c_norm]
                    citation_edges[(this_name, target)] += 1

if parse_failures:
    print(f"\nXML parse failures: {len(parse_failures)}")
    for name, err in parse_failures:
        print(f"  {name}: {err}")

incoming_pairs = set(incoming_amend_edges.keys())
only_incoming = incoming_pairs - outgoing_signal_pairs
only_outgoing = outgoing_signal_pairs - incoming_pairs
both_sides = incoming_pairs & outgoing_signal_pairs

print(f"\n[Full union] Amendment pairs on BOTH sides: {len(both_sides)}")
print(f"[Full union] ONLY incoming: {len(only_incoming)}")
print(f"[Full union] ONLY outgoing: {len(only_outgoing)}")

no_xml_norms = {normalize(name) for _, name, _ in no_xml_members}
flagged_only_outgoing = [(s, t) for s, t in only_outgoing if normalize(t) in no_xml_norms]
if flagged_only_outgoing:
    print(f"  Of which, targets a no-XML member (recovered by the has_xml-registration fix): {len(flagged_only_outgoing)}")
    for s, t in sorted(flagged_only_outgoing):
        print(f"    {s}  ->  {t}")


def pair_scope(source, target):
    gs = name_norm_to_group[normalize(source)]
    gt = name_norm_to_group[normalize(target)]
    sides = {gs, gt}
    if sides <= {"seed", "sg1"}:
        return "seed_sg1_only"
    if sides <= {"seed", "sg1", "sg2"}:
        return "upto_sg2_only"
    if "sg3" in sides and len(sides) == 1:
        return "sg3_internal"
    return "boundary"


all_amendment_edges = []
for (source, target), ops in incoming_amend_edges.items():
    all_amendment_edges.append({
        "source": source,
        "target": target,
        "edge_type": "amendment",
        "operations": dict(ops),
        "count": sum(ops.values()),
        "operation_source": "history_note",
        "confirmed_by_outgoing_schedule": (source, target) in outgoing_signal_pairs,
        "scope": pair_scope(source, target),
    })

for (source, target) in sorted(only_outgoing):
    ops = Counter(classify_outgoing_text(t) for t in outgoing_fallback_text[(source, target)])
    all_amendment_edges.append({
        "source": source,
        "target": target,
        "edge_type": "amendment",
        "operations": dict(ops),
        "count": sum(ops.values()),
        "operation_source": "outgoing_fallback",
        "confirmed_by_outgoing_schedule": True,
        "scope": pair_scope(source, target),
    })

all_citation_edges = []
for (source, target), count in citation_edges.items():
    all_citation_edges.append({
        "source": source,
        "target": target,
        "edge_type": "citation",
        "count": count,
        "scope": pair_scope(source, target),
    })

# ---------------------------------------------------------------------
# Correctness check: re-derived "upto_sg2_only" pairs must match the
# UNION of the already-published sg1_typed_*.json + sg2_typed_*.json
# (the corrected step36 version) exactly.
# ---------------------------------------------------------------------
sg1_amend = json.loads(SG1_TYPED_AMEND_PATH.read_text(encoding="utf-8"))
sg1_cite = json.loads(SG1_TYPED_CITE_PATH.read_text(encoding="utf-8"))
sg2_amend = json.loads(SG2_TYPED_AMEND_PATH.read_text(encoding="utf-8"))
sg2_cite = json.loads(SG2_TYPED_CITE_PATH.read_text(encoding="utf-8"))

published_amend_keys = {(e["source"], e["target"]): e["count"] for e in sg1_amend}
published_amend_keys.update({(e["source"], e["target"]): e["count"] for e in sg2_amend})
published_cite_keys = {(e["source"], e["target"]): e["count"] for e in sg1_cite}
published_cite_keys.update({(e["source"], e["target"]): e["count"] for e in sg2_cite})

UPTO_SG2_SCOPES = ("seed_sg1_only", "upto_sg2_only")
rederived_amend = {(e["source"], e["target"]): e["count"] for e in all_amendment_edges if e["scope"] in UPTO_SG2_SCOPES}
rederived_cite = {(e["source"], e["target"]): e["count"] for e in all_citation_edges if e["scope"] in UPTO_SG2_SCOPES}

amend_mismatches = []
for k, v in rederived_amend.items():
    if published_amend_keys.get(k) != v:
        amend_mismatches.append((k, v, published_amend_keys.get(k)))
for k, v in published_amend_keys.items():
    if k not in rederived_amend:
        amend_mismatches.append((k, None, v))

cite_mismatches = []
for k, v in rederived_cite.items():
    if published_cite_keys.get(k) != v:
        cite_mismatches.append((k, v, published_cite_keys.get(k)))
for k, v in published_cite_keys.items():
    if k not in rederived_cite:
        cite_mismatches.append((k, None, v))

print(f"\n--- Correctness check against published sg1_typed_*.json + sg2_typed_*.json ---")
print(f"Re-derived seed/sg1/sg2-only amendment pairs: {len(rederived_amend)} "
      f"(published: {len(published_amend_keys)}); mismatches: {len(amend_mismatches)}")
if amend_mismatches:
    for k, got, want in amend_mismatches[:20]:
        print(f"  MISMATCH {k}: re-derived={got} published={want}")
print(f"Re-derived seed/sg1/sg2-only citation pairs: {len(rederived_cite)} "
      f"(published: {len(published_cite_keys)}); mismatches: {len(cite_mismatches)}")
if cite_mismatches:
    for k, got, want in cite_mismatches[:20]:
        print(f"  MISMATCH {k}: re-derived={got} published={want}")
if not amend_mismatches and not cite_mismatches:
    print("MATCH: generalized extraction reproduces sg1_typed_*.json + sg2_typed_*.json exactly "
          "on the upto-SG2 subset -- the method generalizes safely to SG3.")

# ---------------------------------------------------------------------
# Write SG3 outputs: only sg3_internal + boundary pairs.
# ---------------------------------------------------------------------
amendment_edges_out = [e for e in all_amendment_edges if e["scope"] in ("sg3_internal", "boundary")]
amendment_edges_out.sort(key=lambda e: -e["count"])
citation_edges_out = [e for e in all_citation_edges if e["scope"] in ("sg3_internal", "boundary")]
citation_edges_out.sort(key=lambda e: -e["count"])

DATA.mkdir(parents=True, exist_ok=True)
(DATA / "sg3_typed_amendment_edges.json").write_text(
    json.dumps(amendment_edges_out, indent=2, ensure_ascii=False), encoding="utf-8")
(DATA / "sg3_typed_citation_edges.json").write_text(
    json.dumps(citation_edges_out, indent=2, ensure_ascii=False), encoding="utf-8")

n_internal = sum(1 for e in amendment_edges_out if e["scope"] == "sg3_internal")
n_boundary = sum(1 for e in amendment_edges_out if e["scope"] == "boundary")
print(f"\nAmendment edges written: {len(amendment_edges_out)} "
      f"(sg3_internal: {n_internal}, (seed/sg1/sg2)<->sg3 boundary: {n_boundary})")
op_totals = Counter()
for e in amendment_edges_out:
    for op, n in e["operations"].items():
        op_totals[op] += n
print("Operation sub-type totals across SG3 output amendment edges:")
for op, n in op_totals.most_common():
    print(f"  {op}: {n}")

n_internal_c = sum(1 for e in citation_edges_out if e["scope"] == "sg3_internal")
n_boundary_c = sum(1 for e in citation_edges_out if e["scope"] == "boundary")
print(f"\nCitation edges written: {len(citation_edges_out)} "
      f"(sg3_internal: {n_internal_c}, (seed/sg1/sg2)<->sg3 boundary: {n_boundary_c})")

print(f"\nSaved -> {DATA}/sg3_typed_amendment_edges.json, {DATA}/sg3_typed_citation_edges.json")
