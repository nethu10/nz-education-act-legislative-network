"""
slm_spotcheck_04_build_sample_typed.py

Option-2 SLM spot-check, built on the FINAL typed graph (outputs/graph_typed/edges.json).

Differences from slm_spotcheck_01 (which sampled the old coarse graph):
  * samples BOTH edge types: amendment AND citation (citation edges were never checked before)
  * stratified: SAMPLE_PER_CELL edges per (layer SG1..SG5) x (edge_type) = 150 edges
  * reads the local raw XML (data/raw/*_targets) -- no network, no fetching
  * amendment evidence: the source's <schedule.amendments.group2> prose (preferred), else the
    target's <history-note> naming the source
  * citation evidence: the text of the provision containing the <citation> tag that resolves to the target
  * samples only edges whose evidence text can actually be found; the number skipped is reported

Typed amendment edges run amending Act (source) -> amended Act (target).
Typed citation edges run citing Act (source) -> cited Act (target).

Run from repo root (needs all raw XML, i.e. on the Mac):
    python src/slm_spotcheck_04_build_sample_typed.py [--layers SG1,SG2,...] [--per-cell 15]
Output: outputs/spotcheck/sample_typed.json   (then run slm_spotcheck_05_classify_typed.py)
"""
import argparse, json, random, re, sys
from collections import defaultdict, Counter
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, "src")
from sg3_filenames import filename_for_sg3
from sg4_filenames import filename_for_sg4

DATA, RAW = Path("data/processed"), Path("data/raw")
OUT = Path("outputs/spotcheck"); OUT.mkdir(parents=True, exist_ok=True)
SEED = "Education and Training Act 2020"
RANDOM_SEED = 42
MAX_SNIPPET = 2000

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")
NAME_VARIANT_ALIASES = {"land transport rule: frontal impact 2001 (32006/1)": "land transport rule 32006/1: frontal impact 2001"}
ACT_NAME_PATTERN = re.compile(
    r"of\s+(?:Part\s+\S+\s+of\s+)?(?:the\s+)?"
    r"([A-Z][A-Za-z0-9,’'\-\(\) ]*?\b(?:Act|Rules?|Regulations?|Order|Notice|Bylaw)\s+\d{4})\b")


def normalize(name):  # identical to assemble_typed_multiedge_graph.normalize
    name = name.replace("’", "'").replace("‘", "'").replace("\xa0", " ")
    name = re.sub(r"\s+", " ", name).strip().rstrip(".").strip()
    m = CITE_PATTERN.match(name)
    base = (m.group(1).strip() if m else name).lower()
    return NAME_VARIANT_ALIASES.get(base, base)


def local_name(tag): return tag.split("}")[-1] if "}" in tag else tag

def element_text(el):
    if el is None: return ""
    cleaned = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
    return re.sub(r"\s+([,.:;)])", r"\1", cleaned)


# ---------- node -> raw XML path ----------
def load(name): return json.loads((DATA / name).read_text(encoding="utf-8"))
sg3_ids = {a["act"]: a for a in load("sg3_act_identifiers.json")}
sg4_ids = {a["act"]: a for a in load("sg4_act_identifiers.json")}

def raw_path(node):
    layer, name = node["layer"], node["id"]
    if not node.get("has_xml"): return None
    if layer == "SG0": return RAW / "education_and_training_act_2020.xml"
    if layer == "SG1":
        m = CITE_PATTERN.match(name.strip())
        if not m: return None
        c = m.group(2)
        mm = re.match(r"(?:SR|LI)\s+(\d{4})/(\d+)", c) or re.match(r"(\d{4})\s+No\s+(\d+)", c)
        return RAW / "sg1_targets" / f"{mm.group(1)}_{mm.group(2)}.xml" if mm else None
    if layer == "SG2": return RAW / "sg2_targets" / f"{node['year']}_{node['number']}.xml"
    if layer == "SG3": return RAW / "sg3_targets" / filename_for_sg3(sg3_ids[name])
    if layer == "SG4": return RAW / "sg4_targets" / filename_for_sg4(sg4_ids[name])
    if layer == "SG5": return RAW / "sg5_targets" / f"{node['year']}_{node['number']}.xml"

_cache = {}
def parse(path):
    if path is None or not path.exists(): return None
    if path not in _cache:
        if len(_cache) > 40: _cache.clear()
        try: _cache[path] = ET.parse(path).getroot()
        except Exception: _cache[path] = None
    return _cache[path]


# ---------- evidence finders ----------
def amendment_evidence(src, tgt, nodes_by_key):
    """schedule prose in src's XML about tgt, else tgt's history-note naming src."""
    tk, sk = normalize(tgt["id"]), normalize(src["id"])
    root = parse(raw_path(src))
    if root is not None:
        texts = []
        for g2 in root.iter():
            if local_name(g2.tag) != "schedule.amendments.group2": continue
            h = g2.find("heading")
            if h is not None and normalize(element_text(h)) == tk:
                texts += [element_text(p) for p in g2.findall("para")]
        texts = [t for t in texts if t]
        if texts and not all(t.lower().startswith("amendment(s) incorporated") for t in texts):
            return "schedule_amendment", " ".join(texts)[:MAX_SNIPPET]
    root = parse(raw_path(tgt))
    if root is not None:
        ops = []
        for note in root.iter():
            if local_name(note.tag) != "history-note": continue
            a, o = note.find("amending-leg"), note.find("amending-operation")
            if a is not None and normalize(element_text(a)) == sk:
                ops.append((o.text if o is not None and o.text else "amended"))
        if ops:
            return "history_note", (f"[history-note] The history notes of \"{tgt['id']}\" record that it was "
                                    f"amended by \"{src['id']}\" ({len(ops)} time(s)); recorded operations: "
                                    + ", ".join(sorted(set(ops))[:6]) + ".")
    return None


def resolve_citation(cit_el):
    lt, has_ext = None, False
    for ch in cit_el.iter():
        ln = local_name(ch.tag)
        if ln == "leg-title" and lt is None: lt = ch
        elif ln == "extref": has_ext = True
    if lt is not None: return element_text(lt)
    if not has_ext: return None
    full = element_text(cit_el)
    if re.search(r"\bthis Act\b", full): return None
    m = ACT_NAME_PATTERN.search(full)
    return m.group(1).strip() if m else None

CONTEXT_TAGS = ("def-para", "subprov", "label-para", "para", "prov", "schedule.provision", "text")

def citation_evidence(src, tgt, rng):
    root = parse(raw_path(src))
    if root is None: return None
    tk = normalize(tgt["id"])
    parent = {c: p for p in root.iter() for c in p}
    hits = []
    for el in root.iter():
        if local_name(el.tag) == "citation" and el.get("jurisdiction") == "nz":
            nm = resolve_citation(el)
            if nm and normalize(nm) == tk: hits.append(el)
    if not hits: return None
    el = rng.choice(hits)
    node, best = el, None
    while node in parent:
        node = parent[node]
        if local_name(node.tag) in CONTEXT_TAGS:
            t = element_text(node)
            if len(t) >= 40: best = t; break
    best = best or element_text(parent.get(el, el))
    if len(best) > 700:  # very large container (e.g. a whole schedule): keep a window around the citation
        needle = element_text(el)[:60]
        i = best.find(needle) if needle else -1
        i = max(i, 0)
        best = best[max(0, i - 350): i + 350]
    return "citation_context", best[:MAX_SNIPPET]


# ---------- prompts (same five-type taxonomy as Stage 3/4 and the original spot-check) ----------
TAXONOMY = """- "definition_reference": use ONLY when this text itself states what a term means, using patterns like "X means...", "X has the meaning given in...", or "X includes..."
- "citation": this text refers to another Act, regulation, or provision to establish context, a condition, or an exemption -- without defining a term and without changing that other Act's wording
- "amendment": this text formally changes the wording of another Act or Schedule, or records that another Act changed this one
- "cross_reference": an internal, procedural pointer within this Act that is not a definition, citation, or amendment (e.g. commencement dates, references between sections of this same Act)
- "power_or_duty": this text grants, describes, or constrains a power, function, duty, or discretion held by a person or body under this Act"""

TIE_BREAK = """Tie-break rule (apply BEFORE picking a type, consistently regardless of how long or complex the wording is): if this text performs a formal repeal, replacement, insertion, or revocation of wording in another Act, Schedule, or regulation, classify it as "amendment" -- the OPERATION being performed (repeal/replace/insert/revoke another document's wording) determines "amendment", not the content of what is inserted. Use "definition_reference" only when the text states what a term means WITHOUT performing such an amending operation on another document. Use "cross_reference" only for an internal pointer within THIS Act that is not itself an amending operation on another document."""

PROMPT = """You are validating a legal-relationship extraction for a New Zealand legislative citation network.

Below is the RELEVANT TEXT {where} (this is the text that a rule-based, tag-only extraction method used to conclude that "{source}" has {a_an} "{rb}" relationship with "{target}").

Your task: read the text and independently classify the relationship between "{source}" and "{target}" as exactly ONE of the following five types. Use the text alone -- do not assume the rule-based label is correct.

Relation type definitions -- use exactly one of these five, and nothing else:
{taxonomy}

{tie}

Text:
\"\"\"
{snippet}
\"\"\"

Return ONLY a JSON object with this exact structure, nothing else:
{{"type": "one of the five types above", "confidence": "high|medium|low", "justification": "one sentence, quoting or paraphrasing the specific part of the text that supports your answer"}}
"""

def make_prompt(edge_type, snip_src, source, target, snippet):
    if edge_type == "amendment":
        where = (f"taken from \"{source}\"" if snip_src == "schedule_amendment"
                 else f"taken from the history notes of \"{target}\"")
        rb = "amendment"
    else:
        where = f"taken from \"{source}\" (the provision containing a legislative citation that points to \"{target}\")"
        rb = "citation"
    return PROMPT.format(where=where, source=source, target=target, rb=rb, a_an="an" if rb == "amendment" else "a",
                         taxonomy=TAXONOMY, tie=TIE_BREAK, snippet=snippet)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", default="SG1,SG2,SG3,SG4,SG5")
    ap.add_argument("--per-cell", type=int, default=15)
    args = ap.parse_args()
    layers = args.layers.split(",")

    nodes = {normalize(n["id"]): n for n in json.loads(Path("outputs/graph_typed/nodes.json").read_text(encoding="utf-8"))}
    edges = json.loads(Path("outputs/graph_typed/edges.json").read_text(encoding="utf-8"))
    pools = defaultdict(list)
    for e in edges: pools[(e["layer"], e["edge_type"])].append(e)

    rng = random.Random(RANDOM_SEED)
    sample, skipped = [], Counter()
    for layer in layers:
        for etype in ("amendment", "citation"):
            pool = pools.get((layer, etype), [])
            rng.shuffle(pool)
            taken = 0
            print(f"\n=== {layer} / {etype}: target {args.per_cell} of {len(pool)} edges ===")
            for e in pool:
                if taken >= args.per_cell: break
                src, tgt = nodes[normalize(e["source"])], nodes[normalize(e["target"])]
                ev = amendment_evidence(src, tgt, nodes) if etype == "amendment" else citation_evidence(src, tgt, rng)
                if ev is None:
                    skipped[(layer, etype)] += 1; continue
                snip_src, text = ev
                sample.append({"layer": layer, "source": e["source"], "target": e["target"],
                               "rule_based_edge_type": etype, "rule_based_weight": e["weight"],
                               "scope": e.get("scope"), "snippet_source": snip_src, "snippet_text": text,
                               "prompt": make_prompt(etype, snip_src, e["source"], e["target"], text)})
                taken += 1
            print(f"  sampled {taken}/{args.per_cell}; skipped (no evidence text found locally): {skipped[(layer, etype)]}")

    (OUT / "sample_typed.json").write_text(json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSample built: {len(sample)} edges")
    cnt = Counter((s["layer"], s["rule_based_edge_type"], s["snippet_source"]) for s in sample)
    for k, v in sorted(cnt.items()): print(f"  {k}: {v}")
    print(f"Skipped for missing evidence: {sum(skipped.values())}  {dict(skipped)}")
    print("Saved -> outputs/spotcheck/sample_typed.json\nNext: python src/slm_spotcheck_05_classify_typed.py")

if __name__ == "__main__":
    main()
