"""
sg2_step35_build_typed_edges.py

Generalizes sg1_step03_build_typed_edges.py to SG2. Produces
sg2_typed_amendment_edges.json and sg2_typed_citation_edges.json, covering:
  - SG2-internal edges (both ends are SG2 Acts), and
  - SEED/SG1 <-> SG2 boundary edges (one end is the seed Act or an SG1 Act,
    the other is an SG2 Act).

Pure seed<->SG1 and SG1-internal pairs are deliberately EXCLUDED from this
script's output -- those are already captured, verified, and published in
sg1_typed_amendment_edges.json / sg1_typed_citation_edges.json. Re-deriving
them here would duplicate that work, so this script instead uses them as a
correctness check: the pure seed/SG1 pairs it (re-)finds along the way are
compared against the SG1 outputs and must match before the SG2-only results
are trusted.

SAME KEY DESIGN DECISION AS SG1 (re-verified, not assumed, before writing
this): for an amendment edge A -> B (A amends B), the operation detail is
read from B's OWN XML <history-note> entries (the incoming side), never from
A's own "schedule.amendments.group2" (the outgoing side, which collapses to
generic boilerplate once folded into a "latest" consolidation). The outgoing
side is kept only as an existence cross-check, and as a last-resort fallback
classifier for the rare pair with no tagged incoming record at all.

Member universe for this pass = seed (1) + SG1 Acts (37) + SG2 Acts (421, of
which 420 have real XML -- the 421st, the tilde-ID Land Transport Rule
32006/1, has no PCO XML endpoint and is already documented/excluded; see
sg2_step34_document_agency_drafted_xml_gap.py). All three groups' XML is
parsed for incoming history-notes / outgoing schedule signals / citations
against the FULL union of names, because a boundary fact can show up in
either side's own document (an SG2 Act amending an SG1 Act shows up as a
history-note inside the SG1 Act's XML; an SG1 Act amending an SG2 Act shows
up inside the SG2 Act's XML).

Act-name resolution differs from SG1 only in how filenames are derived:
  - seed / SG1: the act string itself carries a "(YYYY No N)" / "(SR/LI
    YYYY/N)" citation suffix, parsed with filename_for() exactly as SG1 did.
  - SG2: sg2_final_list.json's "act" field usually has NO citation suffix,
    so filenames instead come from sg2_act_identifiers.json's own resolved
    year/number fields ("{year}_{number}.xml"), confirmed 420/421 exact
    matches against the real sg2_targets/ directory listing before writing
    this script.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

DATA = Path("data/processed")
RAW = Path("data/raw")
SG1_TARGETS_DIR = RAW / "sg1_targets"
SG2_TARGETS_DIR = RAW / "sg2_targets"
SEED_XML = RAW / "education_and_training_act_2020.xml"
SEED_NAME = "Education and Training Act 2020"

SG1_PATH = DATA / "sg1_final_list.json"
SG2_PATH = DATA / "sg2_final_list.json"
SG2_IDS_PATH = DATA / "sg2_act_identifiers.json"
SG1_TYPED_AMEND_PATH = DATA / "sg1_typed_amendment_edges.json"
SG1_TYPED_CITE_PATH = DATA / "sg1_typed_citation_edges.json"

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")


def normalize(name):
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    base = m.group(1).strip() if m else name.strip()
    return base.lower()


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
    """SG1 / seed-style naming: filename comes from the act string's own
    citation suffix, e.g. 'Crown Entities Act 2004 (2004 No 115)'."""
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


# ---------------------------------------------------------------------
# Operation vocabulary -- identical bucketing to SG1 (same PCO vocabulary
# confirmed again by spot-checking amending-operation text in SG2 XML).
# ---------------------------------------------------------------------
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
# Build the full member universe: seed + SG1 (37) + SG2 (421, 420 w/ XML)
# ---------------------------------------------------------------------
sg1 = json.loads(SG1_PATH.read_text(encoding="utf-8"))
sg2 = json.loads(SG2_PATH.read_text(encoding="utf-8"))
sg2_ids = json.loads(SG2_IDS_PATH.read_text(encoding="utf-8"))
sg2_id_by_name = {a["act"]: a for a in sg2_ids}

members = [{"name": SEED_NAME, "path": SEED_XML, "group": "seed"}]

missing_files = []
for a in sg1:
    fname = filename_for_sg1(a["act"])
    path = SG1_TARGETS_DIR / fname if fname else None
    if not path or not path.exists():
        missing_files.append(("sg1", a["act"], fname))
        continue
    members.append({"name": a["act"], "path": path, "group": "sg1"})

for a in sg2:
    ident = sg2_id_by_name.get(a["act"])
    fname = f"{ident['year']}_{ident['number']}.xml" if ident else None
    path = SG2_TARGETS_DIR / fname if fname else None
    if not path or not path.exists():
        missing_files.append(("sg2", a["act"], fname))
        continue
    members.append({"name": a["act"], "path": path, "group": "sg2"})

name_norm_to_display = {normalize(m["name"]): m["name"] for m in members}
name_norm_to_group = {normalize(m["name"]): m["group"] for m in members}
all_norms = set(name_norm_to_display)

n_sg1_ok = sum(1 for m in members if m["group"] == "sg1")
n_sg2_ok = sum(1 for m in members if m["group"] == "sg2")
print(f"Member universe: seed (1) + SG1 ({n_sg1_ok}/{len(sg1)}) + SG2 ({n_sg2_ok}/{len(sg2)}) "
      f"= {len(members)} XML files to parse")
if missing_files:
    print("Missing XML files (expected -- documents the known agency-drafted gap and any others):")
    for group, name, fname in missing_files:
        print(f"  [{group}] {name}  (expected: {fname})")

# ---------------------------------------------------------------------
# Pass 1: same extraction as SG1, run over the FULL union of members
# ---------------------------------------------------------------------
incoming_amend_edges = defaultdict(Counter)   # (source, target) -> Counter(operation -> count)
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

print(f"\n[Full union, seed+SG1+SG2] Amendment pairs on BOTH sides: {len(both_sides)}")
print(f"[Full union] ONLY incoming (no matching outgoing schedule signal): {len(only_incoming)}")
print(f"[Full union] ONLY outgoing (no tagged history-note; outgoing-fallback classifier used): {len(only_outgoing)}")


def pair_scope(source, target):
    gs = name_norm_to_group[normalize(source)]
    gt = name_norm_to_group[normalize(target)]
    sides = {gs, gt}
    if sides <= {"seed", "sg1"}:
        return "seed_sg1_only"       # excluded from SG2 output; already published
    if "sg2" in sides and len(sides) == 1:
        return "sg2_internal"
    return "boundary"               # sg2 <-> (seed or sg1)


# ---------------------------------------------------------------------
# Build the full (unfiltered) edge records, same shape as SG1 script,
# then split by scope.
# ---------------------------------------------------------------------
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
# Correctness check: re-derived seed/SG1-only pairs must match the
# already-published sg1_typed_*.json exactly (same logic, same inputs
# restricted to the smaller universe -- the SG2-widened all_norms should
# not change anything about pairs where neither side is an SG2 Act).
# ---------------------------------------------------------------------
sg1_published_amend = json.loads(SG1_TYPED_AMEND_PATH.read_text(encoding="utf-8"))
sg1_published_cite = json.loads(SG1_TYPED_CITE_PATH.read_text(encoding="utf-8"))
sg1_published_amend_keys = {(e["source"], e["target"]): e["count"] for e in sg1_published_amend}
sg1_published_cite_keys = {(e["source"], e["target"]): e["count"] for e in sg1_published_cite}

rederived_amend_seed_sg1 = {(e["source"], e["target"]): e["count"] for e in all_amendment_edges if e["scope"] == "seed_sg1_only"}
rederived_cite_seed_sg1 = {(e["source"], e["target"]): e["count"] for e in all_citation_edges if e["scope"] == "seed_sg1_only"}

amend_mismatches = []
for k, v in rederived_amend_seed_sg1.items():
    if sg1_published_amend_keys.get(k) != v:
        amend_mismatches.append((k, v, sg1_published_amend_keys.get(k)))
for k, v in sg1_published_amend_keys.items():
    if k not in rederived_amend_seed_sg1:
        amend_mismatches.append((k, None, v))

cite_mismatches = []
for k, v in rederived_cite_seed_sg1.items():
    if sg1_published_cite_keys.get(k) != v:
        cite_mismatches.append((k, v, sg1_published_cite_keys.get(k)))
for k, v in sg1_published_cite_keys.items():
    if k not in rederived_cite_seed_sg1:
        cite_mismatches.append((k, None, v))

print(f"\n--- Correctness check against published sg1_typed_*.json ---")
print(f"Re-derived seed/SG1-only amendment pairs: {len(rederived_amend_seed_sg1)} "
      f"(published: {len(sg1_published_amend_keys)}); mismatches: {len(amend_mismatches)}")
if amend_mismatches:
    for k, got, want in amend_mismatches[:20]:
        print(f"  MISMATCH {k}: re-derived={got} published={want}")
print(f"Re-derived seed/SG1-only citation pairs: {len(rederived_cite_seed_sg1)} "
      f"(published: {len(sg1_published_cite_keys)}); mismatches: {len(cite_mismatches)}")
if cite_mismatches:
    for k, got, want in cite_mismatches[:20]:
        print(f"  MISMATCH {k}: re-derived={got} published={want}")
if not amend_mismatches and not cite_mismatches:
    print("MATCH: generalized extraction reproduces sg1_typed_*.json exactly on the seed/SG1-only "
          "subset -- the method generalizes safely to SG2.")

# ---------------------------------------------------------------------
# Write SG2 outputs: everything EXCEPT seed/SG1-only pairs (those stay
# published only in sg1_typed_*.json, not duplicated here).
# ---------------------------------------------------------------------
amendment_edges_out = [e for e in all_amendment_edges if e["scope"] != "seed_sg1_only"]
amendment_edges_out.sort(key=lambda e: -e["count"])
citation_edges_out = [e for e in all_citation_edges if e["scope"] != "seed_sg1_only"]
citation_edges_out.sort(key=lambda e: -e["count"])

DATA.mkdir(parents=True, exist_ok=True)
(DATA / "sg2_typed_amendment_edges.json").write_text(
    json.dumps(amendment_edges_out, indent=2, ensure_ascii=False), encoding="utf-8")
(DATA / "sg2_typed_citation_edges.json").write_text(
    json.dumps(citation_edges_out, indent=2, ensure_ascii=False), encoding="utf-8")

n_internal = sum(1 for e in amendment_edges_out if e["scope"] == "sg2_internal")
n_boundary = sum(1 for e in amendment_edges_out if e["scope"] == "boundary")
print(f"\nAmendment edges written: {len(amendment_edges_out)} "
      f"(sg2_internal: {n_internal}, sg1/seed<->sg2 boundary: {n_boundary})")
op_totals = Counter()
for e in amendment_edges_out:
    for op, n in e["operations"].items():
        op_totals[op] += n
print("Operation sub-type totals across SG2 output amendment edges:")
for op, n in op_totals.most_common():
    print(f"  {op}: {n}")

n_internal_c = sum(1 for e in citation_edges_out if e["scope"] == "sg2_internal")
n_boundary_c = sum(1 for e in citation_edges_out if e["scope"] == "boundary")
print(f"\nCitation edges written: {len(citation_edges_out)} "
      f"(sg2_internal: {n_internal_c}, sg1/seed<->sg2 boundary: {n_boundary_c})")

print(f"\nSaved -> {DATA}/sg2_typed_amendment_edges.json, {DATA}/sg2_typed_citation_edges.json")
