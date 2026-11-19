"""
slm_spotcheck_01_build_sample.py

Builds the sample for the SLM validation spot-check: takes a stratified
sample of edges from the assembled SG1-SG5 graph (outputs/graph/edges.json)
and, for each one, re-fetches the SOURCE Act's XML and pulls out the actual
provision text that produced the edge -- not just the two Act names.

Why this is needed: the rule-based SG-layer pipeline only ever reads two
XML tags -- <history-note> (an Act recording it was amended BY another Act)
and <schedule.amendments.group2> (an Act's own schedule amending another
Act). Every edge in the assembled graph is, by construction, labelled
"amendment" by the extraction method -- there's no other tag it knows how
to read. The point of this spot-check is to hand a SAMPLE of the real text
behind those edges to the SLM (independently, with no knowledge of what the
rule-based method assumed) and see how often it agrees the relationship is
really an amendment, versus something else in the taxonomy
(definition_reference / citation / cross_reference / power_or_duty).

Reuses the exact tag-parsing functions from sg2_step11_find_internal_links.py
(extract_amendment_records, extract_outgoing_amendments) so the snippets are
pulled the same way the original edges were found, not through separate
logic that could drift out of sync.

Two snippet qualities, both kept and labelled:
  - "schedule_amendment": from <schedule.amendments.group2>/<para> -- real
    prose describing the specific change. Strong evidence for the SLM.
  - "history_note": from <history-note> -- only an operation code + the
    amending Act's name, no prose. Thinner evidence, kept anyway but
    flagged so results can be read with that caveat in mind.

Run from the repo root (same place you run the other sgN_step*.py scripts):
    python src/slm_spotcheck_01_build_sample.py

Output: outputs/spotcheck/sample.json -- one entry per sampled edge, with
the snippet and a ready-to-send classification prompt. Feed this into
slm_spotcheck_02_classify_with_slm.py next.
"""
import json
import random
import re
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import requests
from lxml import etree

DATA = Path("data/processed")
RAW_ROOT = Path("data/raw")
OUT_DIR = Path("outputs/spotcheck")
OUT_DIR.mkdir(parents=True, exist_ok=True)

EDGES_PATH = Path("outputs/graph/edges.json")
SEED_ACT = "Education and Training Act 2020"

SAMPLE_PER_LAYER = 15     # target sample size per layer, SG1-SG5
RANDOM_SEED = 42
DELAY_SECONDS = 1.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CITE_PATTERN = re.compile(r"^(.+?)\s*\(((?:\d{4}\s+No\s+\d+)|(?:SR|LI)\s+\d{4}/\d+)\)$")


def normalize(name):
    if not name:
        return name
    name = name.replace("’", "'").replace("‘", "'")
    m = CITE_PATTERN.match(name.strip())
    return m.group(1).strip() if m else name.strip()


# ---- reused verbatim from sg2_step11_find_internal_links.py ----
def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def element_text(el):
    if el is None:
        return ""
    raw = " ".join(el.itertext())
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = re.sub(r"\s+([,.:;)])", r"\1", cleaned)
    return cleaned

def extract_amendment_records(root):
    records = []
    for note in root.iter():
        if local_name(note.tag) != "history-note":
            continue
        def first_text(tag_name):
            el = note.find(tag_name)
            return el.text if el is not None else None
        records.append({
            "operation": first_text("amending-operation"),
            "amending_act": first_text("amending-leg"),
        })
    return records

def extract_outgoing_amendments(root):
    records = []
    for group2 in root.iter():
        if local_name(group2.tag) != "schedule.amendments.group2":
            continue
        heading_el = group2.find("heading")
        target_act = element_text(heading_el) if heading_el is not None else None
        for para in group2.findall("para"):
            records.append({"target_act": target_act, "text": element_text(para)})
    return records
# ---- end reused block ----


def find_supporting_text(root, target_name):
    """Search this Act's XML for a record matching target_name. Prefers a
    schedule_amendment paragraph (real prose) over a history_note (bare
    operation code) if both exist."""
    target_norm = normalize(target_name)

    for rec in extract_outgoing_amendments(root):
        if rec["target_act"] and normalize(rec["target_act"]) == target_norm and rec["text"]:
            return {"snippet_source": "schedule_amendment", "text": rec["text"]}

    for rec in extract_amendment_records(root):
        if rec["amending_act"] and normalize(rec["amending_act"]) == target_norm:
            op = rec["operation"] or "amended"
            return {
                "snippet_source": "history_note",
                "text": f"[history-note] This Act's own history note records: "
                        f"'{op}' by {rec['amending_act']}.",
            }
    return None


def search_legislation_nz(name, timeout=25):
    url = f"https://www.legislation.govt.nz/items/?search_term={quote(name)}&per_page=5"
    return requests.get(url, headers=HEADERS, timeout=timeout)


RESULT_LINK_RE = re.compile(
    r'href="(?P<path>'
    r'/(?P<type1>act|regulation|rule|order|notice)/(?P<status1>public|private|local|imperial)/(?P<year1>\d{4})/(?P<number1>\d+)/en/latest/[^"]*'
    r'|/secondary-legislation/(?P<subtype2>pco-drafted)/(?P<year2>\d{4})/(?P<number2>\d+)/en/latest/[^"]*'
    r'|/secondary-legislation/(?P<subtype3>agency-drafted)/~(?P<year3>\d{4})/~(?P<number3>\d+)/en/latest/[^"]*'
    r')"'
)

def resolve_seed_identifier():
    """SG1 has no act_identifiers file (the seed isn't itself a candidate),
    so resolve it the same way the SGn resolvers do: search, take the top
    result, build the xml_url from type/status/year/number."""
    r = search_legislation_nz(SEED_ACT)
    m = RESULT_LINK_RE.search(r.text)
    if not m:
        return None
    gd = m.groupdict()
    if gd["year1"]:
        t, s, y, n = gd["type1"], gd["status1"], gd["year1"], gd["number1"]
        return {"type": t, "status": s, "year": int(y), "number": n,
                "xml_url": f"https://legislation.govt.nz/{t}/{s}/{y}/{n}/en/latest.xml"}
    return None


def load_identifier_maps():
    """act name -> {year, number, xml_url, ...} for every layer that has one."""
    maps = {}
    for layer, fname in [("SG1", "sg1_act_identifiers.json"), ("SG2", "sg2_act_identifiers.json"),
                          ("SG3", "sg3_act_identifiers.json"), ("SG4", "sg4_act_identifiers.json"),
                          ("SG5", "sg5_act_identifiers.json")]:
        p = DATA / fname
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        maps[layer] = {e["act"]: e for e in d if e.get("resolved") and e.get("xml_url")}
    return maps


def resolve_identifier(name, id_maps):
    """Look up an Act's identifier across EVERY layer's map, not just one.

    Bug fixed 2026-09-30: this used to be `id_maps.get(edge["layer"], {}).get(source)`
    -- i.e. it only checked the map for the layer the EDGE was recorded
    under. But an edge's "layer" field is the layer the TARGET was
    discovered in, not necessarily the layer the SOURCE belongs to -- a
    `linked_from` source is very often an EARLIER layer's Act (e.g. an SG3
    Act discovered via a citation from an SG2 Act has layer="SG3" on the
    edge, but the source's identifier lives in sg2_act_identifiers.json).
    Checked against the actual edges.json: the old per-edge-layer lookup
    resolved only 1273/7275 SG3 sources, 217/2681 SG4 sources, and 0/63
    SG5 sources; searching every map resolves 4693, 1688, and 54
    respectively. Without this fix the "random" sample was drawn from a
    heavily biased subset (mostly same-layer edges) rather than a fair
    cross-section of each layer's edges.
    """
    for layer in ("SG1", "SG2", "SG3", "SG4", "SG5"):
        ident = id_maps.get(layer, {}).get(name)
        if ident is not None:
            return ident
    return None


def fetch_xml(xml_url, cache_dir, year, number):
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{year}_{number}.xml"
    if cache_path.exists():
        return cache_path.read_bytes(), True
    r = requests.get(xml_url, headers=HEADERS, timeout=60)
    if r.status_code != 200:
        return None, False
    cache_path.write_bytes(r.content)
    time.sleep(DELAY_SECONDS)
    return r.content, False


CLASSIFY_PROMPT_TEMPLATE = """You are validating a legal-relationship extraction for a New Zealand legislative citation network.

Below is the RELEVANT TEXT taken from "{source_act}" (this is the text that a rule-based, tag-only extraction method used to conclude that "{source_act}" has an "amendment" relationship with "{target_act}").

Your task: read the text and independently classify the relationship between "{source_act}" and "{target_act}" as exactly ONE of the following five types. Use the text alone -- do not assume the rule-based label is correct.

Relation type definitions -- use exactly one of these five, and nothing else:
- "definition_reference": use ONLY when this text itself states what a term means, using patterns like "X means...", "X has the meaning given in...", or "X includes..."
- "citation": this text refers to another Act, regulation, or provision to establish context, a condition, or an exemption -- without defining a term and without changing that other Act's wording
- "amendment": this text formally changes the wording of another Act or Schedule, or records that another Act changed this one
- "cross_reference": an internal, procedural pointer within this Act that is not a definition, citation, or amendment (e.g. commencement dates, references between sections of this same Act)
- "power_or_duty": this text grants, describes, or constrains a power, function, duty, or discretion held by a person or body under this Act

Tie-break rule (apply this BEFORE picking a type, and apply it consistently no matter
how long or complex the inserted/substituted wording is): if this text performs a
formal repeal, replacement, insertion, or revocation of wording in another Act,
Schedule, or regulation, classify it as "amendment" -- regardless of what the
inserted, substituted, or revoked wording itself says or refers to. It does not
matter whether that wording is a definition ("repeal the definition of X and
substitute: X means ..."), a procedural cross-reference to other provisions, or
anything else: the OPERATION being performed (repeal/replace/insert/revoke another
document's wording) is what determines "amendment", not the content of what is being
inserted. Judge this the same way whether the substituted text is one clause or
several. Use "definition_reference" only when the text states what a term means
WITHOUT performing such an amending operation on another document. Use
"cross_reference" only for an internal pointer within THIS Act that is not itself
an amending operation on another document.

Text:
\"\"\"
{snippet}
\"\"\"

Return ONLY a JSON object with this exact structure, nothing else:
{{"type": "one of the five types above", "confidence": "high|medium|low", "justification": "one sentence, quoting or paraphrasing the specific part of the text that supports your answer"}}
"""


def main():
    random.seed(RANDOM_SEED)
    edges = json.loads(EDGES_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(edges)} edges from {EDGES_PATH}")

    by_layer = defaultdict(list)
    for e in edges:
        by_layer[e["layer"]].append(e)

    id_maps = load_identifier_maps()

    print("Resolving seed Act identifier (for SG1 edges)...")
    seed_id = resolve_seed_identifier()
    if seed_id:
        print(f"  seed -> {seed_id['type']}/{seed_id['status']}/{seed_id['year']}/{seed_id['number']}")
    else:
        print("  !! could not resolve seed identifier -- SG1 edges will be skipped")

    sample = []
    for layer in ["SG1", "SG2", "SG3", "SG4", "SG5"]:
        pool = by_layer.get(layer, [])
        if not pool:
            continue
        random.shuffle(pool)
        n_target = min(SAMPLE_PER_LAYER, len(pool))
        print(f"\n=== {layer}: sampling up to {n_target} of {len(pool)} edges ===")

        taken = 0
        for e in pool:
            if taken >= n_target:
                break
            source, target = e["source"], e["target"]

            # figure out which Act's XML to fetch: for SG1 amendment_outgoing
            # the seed is the source; for amendment_incoming the seed is the
            # TARGET and the SG1 Act is the source of the history-note.
            fetch_name = source
            if layer == "SG1":
                if e["edge_type"] == "amendment_outgoing":
                    ident = seed_id
                    fetch_name = SEED_ACT
                    cache_dir = RAW_ROOT / "seed_target"
                elif e["edge_type"] == "internal_link":
                    # Added once sg1_step01/sg1_step02 backfilled SG1's own
                    # identifiers + internal-link scan. Unlike
                    # amendment_outgoing/citation, the SOURCE here is one of
                    # the 37 SG1 Acts itself, not the seed -- but it WAS
                    # produced by the same tag-only method (<history-note>/
                    # <schedule.amendments.group2>) as every other
                    # internal_link edge in the graph, so it belongs in this
                    # spot-check exactly like SG2-SG5's internal_link edges do.
                    ident = resolve_identifier(source, id_maps)
                    cache_dir = RAW_ROOT / "sg1_spotcheck"
                elif e["edge_type"] == "amendment_incoming":
                    # moot in practice: SG1 currently has zero
                    # amendment_incoming edges, per the assembled graph's
                    # own edge-type counts.
                    continue
                else:
                    # "citation" edges: excluded by design, not a gap.
                    # SG1's "citation" field comes from a separate, dedicated
                    # <citation>-tag scan that already carries its own
                    # correct label -- there's no assumed-amendment question
                    # to ask about it. Validating that extractor's own
                    # precision would be a distinct spot-check, out of scope
                    # here.
                    continue
                if ident is None:
                    continue
            else:
                ident = resolve_identifier(source, id_maps)
                if ident is None:
                    continue
                cache_dir = RAW_ROOT / f"{layer.lower()}_spotcheck"

            try:
                xml_bytes, from_cache = fetch_xml(ident["xml_url"], cache_dir, ident["year"], ident["number"])
            except Exception as ex:
                print(f"  FAILED fetch for {fetch_name!r}: {type(ex).__name__}: {ex}")
                continue
            if xml_bytes is None:
                continue

            try:
                root = etree.fromstring(xml_bytes)
            except Exception:
                continue

            support = find_supporting_text(root, target)
            if support is None:
                # the edge's target name didn't match anything in this XML
                # under our normalize() -- likely a name-variant mismatch
                # (the same class of issue documented throughout this
                # pipeline). Skip rather than guess at a snippet.
                continue

            prompt = CLASSIFY_PROMPT_TEMPLATE.format(
                source_act=source, target_act=target, snippet=support["text"][:2000]
            )
            sample.append({
                "layer": layer,
                "source": source,
                "target": target,
                "rule_based_edge_type": e["edge_type"],
                "rule_based_weight": e["weight"],
                "snippet_source": support["snippet_source"],
                "snippet_text": support["text"],
                "prompt": prompt,
            })
            taken += 1
            status = "cached" if from_cache else "fetched"
            print(f"  [{taken}/{n_target}] {source[:50]!r} -> {target[:50]!r} ({support['snippet_source']}, {status})")

    out_path = OUT_DIR / "sample.json"
    out_path.write_text(json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*70}")
    print(f"Sample built: {len(sample)} edges across {len(set(s['layer'] for s in sample))} layers")
    by_snip = defaultdict(int)
    for s in sample:
        by_snip[s["snippet_source"]] += 1
    for k, v in by_snip.items():
        print(f"  {k}: {v}")
    print(f"\nSaved -> {out_path}")
    print("Next: python src/slm_spotcheck_02_classify_with_slm.py")


if __name__ == "__main__":
    main()