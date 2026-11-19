"""
sg2_step36_build_typed_edges_v2.py

Supersedes sg2_step35_build_typed_edges.py. Fixes one registration bug that
silently dropped real edges; everything else is identical to step35.

BUG FOUND (2026-10-04, while re-investigating the "420/421" SG2 XML gap at
the user's request): step35's member-building loop only added an entry to
`members` (and therefore to `all_norms` / `name_norm_to_display`) when its
local XML file actually existed on disk. The one SG2 entry with no XML --
"Land Transport Rule 32006/1: Frontal Impact 2001" (agency-drafted, tilde-ID,
confirmed HTTP 500 on its XML endpoint, re-verified live just now) -- was
therefore excluded from `all_norms` ENTIRELY, not just skipped as a parse
source. That meant any OTHER member's own XML that named this Rule as an
amendment target (a real, present, taggable <schedule.amendments.group2>
heading) could never resolve to a display name and was silently discarded,
even though the extraction logic to catch it already existed (the
outgoing-only fallback path).

Direct confirmation this actually happened: grepping the raw XML turned up
TWO real, previously-unextracted outgoing amendment signals naming this
Rule, neither captured in step35's output:
  - Immigration Act 2009 (SG1)              -> schedule.amendments.group2
  - Land Transport Management Amendment Act 2008 (SG2, 2008 No 47)
                                             -> schedule.amendments.group2
(A further two mentions, in sg3_targets/1999_27.xml and 2014_291.xml, are
plain prose naming the Rule inside a fees provision -- no <citation> tag,
no schedule heading -- so they stay untagged, consistent with how every
other untagged prose mention in this pipeline is treated.)

FIX: build the member list from the full final-list + identifiers union
regardless of whether local XML exists. Each member carries `has_xml`;
parsing (Pass 1) is skipped for `has_xml=False` members -- they can never
be a SOURCE, since there is no file to read -- but their name is still in
`all_norms`, so they resolve correctly as a TARGET when found in some other
member's own XML (outgoing schedule heading or <citation>). This is exactly
the architecture the outgoing-only fallback path was already built for; it
just never got the chance to run for a target with no file of its own.

Nothing about the extraction logic, operation vocabulary, or scope/
boundary classification changes from step35 -- only which names are
eligible to be resolved as an edge target.
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

# Narrow, hand-verified name-variant aliases -- NOT a general fuzzy-match
# rule, same philosophy as SG3_FILENAME_OVERRIDES in sg3_filenames.py.
# Found 2026-10-04: Land Transport Management Amendment Act 2008's own
# schedule.amendments.group2 heading names this Rule in a different word
# order ("Land Transport Rule: Frontal Impact 2001 (32006/1)") than its
# registered act-identifier name ("Land Transport Rule 32006/1: Frontal
# Impact 2001"), so plain normalize() alone does not resolve them to the
# same entity. Mapped at the normalized-string level so every extraction
# path (incoming/outgoing/citation) benefits uniformly.
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
# Build the full member universe: seed + SG1 (37) + SG2 (421) -- EVERY
# final-list entry is registered regardless of has_xml, unlike step35.
# ---------------------------------------------------------------------
sg1 = json.loads(SG1_PATH.read_text(encoding="utf-8"))
sg2 = json.loads(SG2_PATH.read_text(encoding="utf-8"))
sg2_ids = json.loads(SG2_IDS_PATH.read_text(encoding="utf-8"))
sg2_id_by_name = {a["act"]: a for a in sg2_ids}

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

name_norm_to_display = {normalize(m["name"]): m["name"] for m in members}
name_norm_to_group = {normalize(m["name"]): m["group"] for m in members}
all_norms = set(name_norm_to_display)

n_sg1_ok = sum(1 for m in members if m["group"] == "sg1" and m["has_xml"])
n_sg2_ok = sum(1 for m in members if m["group"] == "sg2" and m["has_xml"])
print(f"Member universe: seed (1) + SG1 ({n_sg1_ok}/{len(sg1)} with XML) + SG2 ({n_sg2_ok}/{len(sg2)} with XML) "
      f"= {len(members)} total registered names ({len(members) - len(no_xml_members)} parseable)")
if no_xml_members:
    print(f"Registered as valid edge TARGETS despite no local XML ({len(no_xml_members)}) -- "
          f"this is the fix over step35, which excluded these from all_norms entirely:")
    for group, name, fname in no_xml_members:
        print(f"  [{group}] {name}  (would-be filename: {fname})")

# ---------------------------------------------------------------------
# Pass 1: identical extraction to step35, but only over has_xml members.
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
        continue  # no file to read; still a valid target via all_norms above
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
if only_outgoing:
    for s, t in sorted(only_outgoing):
        flag = " <-- target has no XML of its own (recovered by this fix)" if normalize(t) in {normalize(n) for _, n, _ in no_xml_members} else ""
        print(f"  ONLY OUTGOING: {s}  ->  {t}{flag}")


def pair_scope(source, target):
    gs = name_norm_to_group[normalize(source)]
    gt = name_norm_to_group[normalize(target)]
    sides = {gs, gt}
    if sides <= {"seed", "sg1"}:
        return "seed_sg1_only"
    if "sg2" in sides and len(sides) == 1:
        return "sg2_internal"
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
# Correctness check against published sg1_typed_*.json (unchanged scope --
# SG1 has no no-XML members, so this should match exactly, same as step35).
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
    print("MATCH: fix does not disturb the seed/SG1-only subset -- safe to apply.")

# ---------------------------------------------------------------------
# Diff against the OLD step35 output, so the exact recovered edges are
# visible and citable (methodology-chapter-worthy: what changed and why).
# ---------------------------------------------------------------------
OLD_AMEND_PATH = DATA / "sg2_typed_amendment_edges.json"
OLD_CITE_PATH = DATA / "sg2_typed_citation_edges.json"
old_amend = json.loads(OLD_AMEND_PATH.read_text(encoding="utf-8")) if OLD_AMEND_PATH.exists() else []
old_cite = json.loads(OLD_CITE_PATH.read_text(encoding="utf-8")) if OLD_CITE_PATH.exists() else []
old_amend_keys = {(e["source"], e["target"]) for e in old_amend}
old_cite_keys = {(e["source"], e["target"]) for e in old_cite}

amendment_edges_out = [e for e in all_amendment_edges if e["scope"] != "seed_sg1_only"]
amendment_edges_out.sort(key=lambda e: -e["count"])
citation_edges_out = [e for e in all_citation_edges if e["scope"] != "seed_sg1_only"]
citation_edges_out.sort(key=lambda e: -e["count"])

new_amend_keys = {(e["source"], e["target"]) for e in amendment_edges_out}
new_cite_keys = {(e["source"], e["target"]) for e in citation_edges_out}

print(f"\n--- Diff against previous (step35) sg2_typed_*.json ---")
print(f"Amendment edges added: {sorted(new_amend_keys - old_amend_keys)}")
print(f"Amendment edges removed: {sorted(old_amend_keys - new_amend_keys)}")
print(f"Citation edges added: {sorted(new_cite_keys - old_cite_keys)}")
print(f"Citation edges removed: {sorted(old_cite_keys - new_cite_keys)}")

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
