"""
sg1_step03_build_typed_edges.py

Builds fully typed SG1 edges -- both the seed<->SG1 boundary and the
SG1-internal edges -- replacing the untyped sg1_final_list.json counts and
the operation-less sg1_internal_amendment_edges.json / sg1_internal_citation_
edges.json.

Every amendment edge now carries WHICH operation it is (insert / amend /
repeal / replace / substitute / add / revoke / renumber / editorial /
commencement / other), not just a bare count. Every edge also carries
edge_type ("amendment" or "citation") explicitly.

KEY DESIGN DECISION (verified against real XML before writing this):
For an amendment edge (A -> B, meaning A amends B), the operation detail is
read from B's OWN XML <history-note> (the "incoming" side), never from A's
own "schedule.amendments.group2" ("outgoing" side). Verified directly:
Crown Entities Act 2004 -> Education Act 1989 shows only 1 paragraph on the
outgoing side (generic boilerplate "Amendment(s) incorporated in the
Act(s)." -- the "latest" XML consolidation collapses the real wording once
it's folded into the target's text) vs 69 separately-tagged, real-operation
history-note entries on the incoming side. The outgoing side is kept only
as a secondary existence cross-check (did we also see this pair from the
other direction?), never for counting or operation typing. This is a
one-sided reliability issue specific to this "schedule.amendments.group2"
element, not a reason to distrust <history-note> -- that tag's own
"amending-operation" text is PCO's own, directly-stated classification
(confirmed vocabulary: inserted, amended, repealed, replaced, substituted,
added, revoked, renumbered, editorial change, brought into force, plus a
long tail of one-off narrative notes bucketed as "other").

This means the previous sg1_internal_amendment_edges.json counts (e.g. the
"70x" for this exact pair) were 1 boilerplate paragraph + 69 real operations
added together, not a true double-count of the same fact, but not a clean
number either -- the new output reports the 69 operation-tagged facts as
the authoritative count, with the single outgoing-side boilerplate note
dropped as uninformative.

Scope: the seed Act (Education and Training Act 2020) + all 37 SG1 Acts.
Boundary and internal edges are built with the exact same logic -- the only
difference is whether the pair happens to include the seed.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

DATA = Path("data/processed")
RAW = Path("data/raw")
TARGETS_DIR = RAW / "sg1_targets"
SEED_XML = RAW / "education_and_training_act_2020.xml"
SEED_NAME = "Education and Training Act 2020"

SG1_PATH = DATA / "sg1_final_list.json"

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")


def normalize(name):
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'").replace("\xa0", " ")
    # 2026-10-07 NBSP fix: fold non-breaking spaces / whitespace runs / trailing period
    # (names like "Finance Act (No\xa02) 1988" previously never matched XML text).
    name = re.sub(r"\s+", " ", name).strip().rstrip(".").strip()
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


def filename_for(act_field):
    """Real sg1_targets/ files are named '{year}_{number}.xml', no prefix --
    confirmed against the actual directory listing (differs from the
    'act_'/'secondary-legislation_' prefix the SG2+ scripts use)."""
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
# Operation vocabulary -- confirmed by scanning amending-operation text
# across all 37 SG1 Acts' real XML before writing this bucketing.
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
    # strip a trailing "(with effect on ...)" / similar qualifier before matching
    text = re.sub(r"\s*\(with effect on[^)]*\)\s*$", "", text, flags=re.I).strip()
    for pattern, bucket in OPERATION_BUCKETS:
        if pattern.match(text):
            return bucket
    return "other"


def classify_outgoing_text(text):
    """Crude fallback classification for outgoing-schedule paragraph text,
    used ONLY for the existence cross-check, never for the real operation
    label (see module docstring)."""
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
# Load SG1 membership and build the name <-> file index
# ---------------------------------------------------------------------
sg1 = json.loads(SG1_PATH.read_text(encoding="utf-8"))
members = [{"name": SEED_NAME, "path": SEED_XML, "is_seed": True}]
missing_files = []
for a in sg1:
    fname = filename_for(a["act"])
    path = TARGETS_DIR / fname if fname else None
    if not path or not path.exists():
        missing_files.append((a["act"], fname))
        continue
    members.append({"name": a["act"], "path": path, "is_seed": False})

name_norm_to_display = {normalize(m["name"]): m["name"] for m in members}
all_norms = set(name_norm_to_display)

print(f"SG1 membership: seed + {len(sg1)} Acts; XML found for {len(members)-1}/{len(sg1)} Acts")
if missing_files:
    print("Missing XML files:")
    for name, fname in missing_files:
        print(f"  {name}  (expected: {fname})")

# ---------------------------------------------------------------------
# Pass 1: for every member's own XML, extract:
#   - incoming amendment facts (this act was amended by X, operation Y)
#   - outgoing amendment EXISTENCE signals (this act's schedule lists
#     target Y) -- cross-check only
#   - citations this act's own text makes to other members
# ---------------------------------------------------------------------
incoming_amend_edges = defaultdict(Counter)   # (source, target) -> Counter(operation -> count)
outgoing_signal_pairs = set()                  # (source, target) seen via schedule, for cross-check
outgoing_fallback_text = defaultdict(list)     # (source, target) -> [para texts], for the outgoing-only fallback
citation_edges = defaultdict(int)              # (source, target) -> count

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

    # --- incoming amendments: <history-note> entries in THIS act's XML ---
    last_named_act = None  # for anaphoric citation resolution, reused below
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

    # --- outgoing amendment existence signal: schedule.amendments.group2 ---
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

    # --- citations: <citation jurisdiction="nz"> in THIS act's own text ---
    last_named_act = None
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

# ---------------------------------------------------------------------
# Cross-check: does every incoming-detected pair also show up as an
# outgoing signal from the source's own schedule, and vice versa?
# Logged, not auto-resolved -- a mismatch is a data point, not an error.
# ---------------------------------------------------------------------
incoming_pairs = set(incoming_amend_edges.keys())
only_incoming = incoming_pairs - outgoing_signal_pairs
only_outgoing = outgoing_signal_pairs - incoming_pairs
both_sides = incoming_pairs & outgoing_signal_pairs

print(f"\nAmendment pairs seen on BOTH sides (incoming history-note + outgoing schedule): {len(both_sides)}")
print(f"Amendment pairs seen ONLY on the incoming side (no schedule entry found in source's own XML -- "
      f"expected whenever the source's schedule uses boilerplate without a matching heading, or lists it "
      f"under a slightly different name variant): {len(only_incoming)}")
print(f"Amendment pairs seen ONLY on the outgoing side (schedule lists a target with NO matching "
      f"history-note entry in the target's own XML -- worth a manual look): {len(only_outgoing)}")
if only_outgoing:
    for s, t in sorted(only_outgoing):
        print(f"  ONLY OUTGOING: {s}  ->  {t}")
    print("  (kept in the output below via the outgoing-text fallback classifier, flagged "
          "operation_source='outgoing_fallback' -- not dropped, but less reliable than a "
          "tagged history-note, since it's inferred from prose rather than PCO's own label)")

# ---------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------
amendment_edges_out = []
for (source, target), ops in sorted(incoming_amend_edges.items(), key=lambda kv: -sum(kv[1].values())):
    amendment_edges_out.append({
        "source": source,
        "target": target,
        "edge_type": "amendment",
        "operations": dict(ops),
        "count": sum(ops.values()),
        "operation_source": "history_note",
        "confirmed_by_outgoing_schedule": (source, target) in outgoing_signal_pairs,
    })

# outgoing-only pairs: no tagged history-note was found at all, so include
# them via the cruder text classifier rather than silently dropping a real
# relationship -- flagged so it's never confused with the tagged kind above.
for (source, target) in sorted(only_outgoing):
    ops = Counter(classify_outgoing_text(t) for t in outgoing_fallback_text[(source, target)])
    amendment_edges_out.append({
        "source": source,
        "target": target,
        "edge_type": "amendment",
        "operations": dict(ops),
        "count": sum(ops.values()),
        "operation_source": "outgoing_fallback",
        "confirmed_by_outgoing_schedule": True,
    })

citation_edges_out = []
for (source, target), count in sorted(citation_edges.items(), key=lambda kv: -kv[1]):
    citation_edges_out.append({
        "source": source,
        "target": target,
        "edge_type": "citation",
        "count": count,
    })

DATA.mkdir(parents=True, exist_ok=True)
(DATA / "sg1_typed_amendment_edges.json").write_text(
    json.dumps(amendment_edges_out, indent=2, ensure_ascii=False), encoding="utf-8")
(DATA / "sg1_typed_citation_edges.json").write_text(
    json.dumps(citation_edges_out, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"\nAmendment edges written: {len(amendment_edges_out)}  "
      f"(seed-boundary: {sum(1 for e in amendment_edges_out if SEED_NAME in (e['source'], e['target']))}, "
      f"internal: {sum(1 for e in amendment_edges_out if SEED_NAME not in (e['source'], e['target']))})")
op_totals = Counter()
for e in amendment_edges_out:
    for op, n in e["operations"].items():
        op_totals[op] += n
print("Operation sub-type totals across all amendment edges:")
for op, n in op_totals.most_common():
    print(f"  {op}: {n}")

print(f"\nCitation edges written: {len(citation_edges_out)}  "
      f"(seed-boundary: {sum(1 for e in citation_edges_out if SEED_NAME in (e['source'], e['target']))}, "
      f"internal: {sum(1 for e in citation_edges_out if SEED_NAME not in (e['source'], e['target']))})")

print(f"\nSaved -> {DATA}/sg1_typed_amendment_edges.json, {DATA}/sg1_typed_citation_edges.json")
