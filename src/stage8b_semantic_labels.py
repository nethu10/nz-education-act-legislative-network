"""
stage8b_semantic_labels.py -- Stage 8b: semantic labelling of the Leiden communities with the local SLM.

Why: Leiden finds groups from link patterns only. This step gives each group a short plain-English policy-area name
by reading the TITLES of the Acts in it, using the same local small language model as Stages 3/4 and the spot-checks
(Qwen2.5:7b-instruct via Ollama, temperature 0, JSON output).

Method (designed so the labels can be defended, not just produced)
  * Input: the headline partition (substantive_only, directed, weighted, gamma = 1).
  * Evidence given to the SLM: Act titles only (no links, no layers, no hints about which group contains the seed Act).
  * Three independent prompts per community with different samples of its members:
        A = the 30 most-connected Acts; B = 30 Acts chosen at random; C = the 15 most-connected + 15 random.
    Groups with 30 Acts or fewer are given all their Acts in every prompt.
  * Output per prompt: label (6 words max), one-sentence plain-English description, broad domain from a FIXED list,
    confidence, and whether the group looks mixed.
  * Consistency check: do the three prompts give the same broad domain? The final label is prompt A's, unless the
    domain is not the majority domain, in which case the group is flagged for review.
  * Cross-check: the SLM's broad domain is compared with the draft labels written earlier (coarse domain mapping below).
  * Human-in-the-loop: nothing is final until the researcher reviews the flagged groups (review column in the outputs).

Needs Ollama running locally with qwen2.5:7b-instruct pulled (same as Stage 3).
Run from repo root:
    python src/stage8b_semantic_labels.py             # full run (resumable; about 10 to 25 minutes)
    python src/stage8b_semantic_labels.py --dry-run   # print two example prompts, no model call
Outputs: outputs/leiden_labels/{labels.csv, labels.json, raw_responses.json, summary.md}
"""
import csv, json, random, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import requests

sys.path.insert(0, "src")
try:
    from extraction_utils import OLLAMA_URL, MODEL
except ImportError:
    OLLAMA_URL, MODEL = "http://localhost:11434/api/generate", "qwen2.5:7b-instruct"
    print(f"!! extraction_utils import failed; using {OLLAMA_URL} / {MODEL}")

OUT = Path("outputs/leiden_labels"); OUT.mkdir(parents=True, exist_ok=True)
MEMBERSHIP = Path("outputs/leiden/membership_substantive_only__directed__weighted.csv")
EDGES = Path("outputs/graph_typed_substantive_only/edges.json")
RAW = OUT / "raw_responses.json"
VARIANTS = ("A", "B", "C")
DOMAINS = ["Justice and policing", "Environment and natural resources", "Business and finance", "Public administration and governance",
           "Social policy and welfare", "Education", "Health and safety", "Transport and infrastructure", "Defence and security",
           "Maori affairs", "Tax and revenue", "International and trade", "Communications and technology", "Other or mixed"]
# Draft labels written earlier (policy area, coarse domain) -- used only as a cross-check, never shown to the SLM.
DRAFT = {1: ("Land, environment, conservation and fisheries (incl. Treaty settlements)", "Environment and natural resources"),
 2: ("Criminal justice, policing and border control", "Justice and policing"), 3: ("Family, children and the courts", "Justice and policing"),
 4: ("Company and financial-markets law", "Business and finance"), 5: ("Public sector, public finance, privacy and official information", "Public administration and governance"),
 6: ("Local government, building and water services", "Public administration and governance"), 7: ("Social support, ACC, employment, housing and health workforce", "Social policy and welfare"),
 8: ("Land and maritime transport", "Transport and infrastructure"), 9: ("Biosecurity, food, telecommunications and hazardous substances", "Other or mixed"),
 10: ("Education and training", "Education"), 11: ("Workplace safety, gas and electricity", "Health and safety"), 12: ("Tax and KiwiSaver", "Tax and revenue"),
 13: ("Fisheries regulations", "Environment and natural resources"), 14: ("Climate change", "Environment and natural resources"),
 15: ("Overseas investment, trade and intellectual property", "International and trade"), 16: ("Maori land and affairs", "Maori affairs"),
 17: ("Government superannuation (mixed with older Acts)", "Other or mixed"), 18: ("Defence, military justice, coroners and burial", "Defence and security"),
 19: ("Professional regulation (lawyers, real estate, security, tribunals)", "Business and finance"), 20: ("Elections and juries", "Public administration and governance"),
 21: ("Firearms", "Justice and policing"), 22: ("Cook Islands", "International and trade"), 23: ("Radiocommunications and signals intelligence", "Communications and technology"),
 24: ("Smokefree and regulated products", "Health and safety"), 25: ("Weights and measures", "Business and finance"), 26: ("War pensions", "Social policy and welfare"),
 27: ("Anti-money laundering", "Business and finance"), 28: ("Energy efficiency", "Environment and natural resources"), 29: ("Court of Appeal rules", "Justice and policing"),
 30: ("Child protection", "Social policy and welfare"), 31: ("Patriotic and canteen funds", "Social policy and welfare"), 32: ("Gas governance", "Transport and infrastructure"),
 33: ("Greater Christchurch regeneration", "Public administration and governance"), 34: ("Maori Purposes Acts", "Maori affairs")}


def clean(t): return re.sub(r"\s+", " ", re.sub(r"\s*\((?:[^()]*)\)", "", t)).strip()


def make_prompt(titles, n_total):
    lst = "\n".join(f"- {t}" for t in titles)
    return f"""You are helping label groups of New Zealand laws for a non-lawyer, policy-facing audience.
Below are the titles of {len(titles)} Acts and regulations from one group of {n_total} (the group was found automatically because these laws amend or cite each other much more than they connect to other laws).

{lst}

Task: using ONLY these titles, say what policy area this group covers.
Return JSON with exactly these keys:
- "label": a short plain-English policy-area name, at most 6 words (for example "Criminal justice and policing")
- "description": one sentence, plain English, saying what these laws are about
- "domain": exactly one of {json.dumps(DOMAINS)}
- "confidence": "high", "medium" or "low"
- "mixed": true if the titles clearly cover two or more unrelated policy areas, otherwise false
Do not invent laws that are not listed. If the titles are mixed, name the two main areas in the label."""


def titles_for(variant, members, strength, cn):
    ranked = sorted(members, key=lambda n: -strength[n]); n = len(ranked)
    rng = random.Random(f"{cn}-{variant}")
    if n <= 30: pick = ranked
    elif variant == "A": pick = ranked[:30]
    elif variant == "B": pick = rng.sample(ranked, 30)
    else:
        top = ranked[:15]; rest = [x for x in ranked if x not in top]; pick = top + rng.sample(rest, 15)
    return [clean(x) for x in pick]


def call(prompt, timeout=240):
    for attempt in range(3):
        try:
            r = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}}, timeout=timeout)
            r.raise_for_status(); return json.loads(r.json()["response"])
        except (json.JSONDecodeError, requests.RequestException) as e:
            err = e
    raise RuntimeError(f"model call failed after 3 attempts: {err}")


def norm(res):
    d = res.get("domain"); d = d if d in DOMAINS else "Other or mixed"
    return {"label": str(res.get("label", "")).strip()[:80], "description": str(res.get("description", "")).strip(),
            "domain": d, "confidence": str(res.get("confidence", "")).lower(), "mixed": bool(res.get("mixed", False))}


def main():
    rows = list(csv.DictReader(open(MEMBERSHIP, encoding="utf-8")))
    com = defaultdict(list)
    for r in rows: com[int(r["community"])].append(r["node"])
    st = defaultdict(float)
    for e in json.loads(EDGES.read_text(encoding="utf-8")): st[e["source"]] += e["weight"]; st[e["target"]] += e["weight"]
    assert len(com) == 34 and sum(len(v) for v in com.values()) == 2475, "unexpected partition; run Stage 8 first"

    if "--dry-run" in sys.argv:
        for cn in (10, 22):
            print(f"\n===== community {cn} ({len(com[cn])} Acts), variant A =====\n" + make_prompt(titles_for("A", com[cn], st, cn), len(com[cn])))
        return

    raw = json.loads(RAW.read_text(encoding="utf-8")) if RAW.exists() else {}
    print(f"Model {MODEL}; {len(raw)} responses already saved\n")
    for cn in sorted(com, key=lambda c: -len(com[c])):
        for v in VARIANTS:
            key = f"{cn}|{v}"
            if key in raw: continue
            if len(com[cn]) <= 30 and v != "A": continue   # all Acts shown in A; B and C are copies, filled in below
            prompt = make_prompt(titles_for(v, com[cn], st, cn), len(com[cn]))
            raw[key] = norm(call(prompt))
            RAW.write_text(json.dumps(raw, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"community {cn:2d} ({len(com[cn]):3d} Acts) variant {v}: {raw[key]['label']}  [{raw[key]['domain']}]")
        # small groups: make sure B and C exist (copies of A)
        if len(com[cn]) <= 30:
            for v in ("B", "C"): raw.setdefault(f"{cn}|{v}", raw[f"{cn}|A"])
            RAW.write_text(json.dumps(raw, indent=1, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------ assemble
    final, L = [], []
    def line(s=""): L.append(s); print(s)
    for cn in sorted(com, key=lambda c: -len(com[c])):
        rs = {v: raw[f"{cn}|{v}"] for v in VARIANTS}
        doms = Counter(r["domain"] for r in rs.values()); maj, cnt = doms.most_common(1)[0]
        a = rs["A"]; flags = []
        if cnt < 3 and len(com[cn]) > 30: flags.append("domain differs between prompts")
        if a["domain"] != maj: flags.append("prompt A domain is not the majority");
        if a["mixed"] or a["confidence"] == "low": flags.append("SLM says mixed or low confidence")
        if a["domain"] != DRAFT[cn][1]: flags.append("differs from draft domain")
        final.append({"community": cn, "acts": len(com[cn]), "slm_label": a["label"], "slm_description": a["description"], "slm_domain": a["domain"],
                      "slm_confidence": a["confidence"], "slm_mixed": a["mixed"], "domain_agreement_across_prompts": f"{cnt}/3",
                      "draft_label": DRAFT[cn][0], "draft_domain": DRAFT[cn][1], "domain_matches_draft": a["domain"] == DRAFT[cn][1],
                      "needs_review": bool(flags), "review_reason": "; ".join(flags), "final_label_researcher": ""})
    (OUT / "labels.json").write_text(json.dumps(final, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(OUT / "labels.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(final[0].keys())); w.writeheader(); w.writerows(final)

    line("# Stage 8b: semantic labels for the 34 Leiden communities (SLM: " + MODEL + ")\n")
    n_ok = sum(1 for f in final if f["domain_agreement_across_prompts"] == "3/3"); n_m = sum(1 for f in final if f["domain_matches_draft"])
    line(f"- Same broad domain in all 3 prompts: **{n_ok} of 34** groups")
    line(f"- SLM domain matches the draft domain: **{n_m} of 34** groups")
    line(f"- Flagged for researcher review: **{sum(1 for f in final if f['needs_review'])} of 34**\n")
    line("| # | Acts | SLM label | SLM domain | Prompts agreeing | Draft label | Match | Review reason |"); line("|---|---|---|---|---|---|---|---|")
    for f in final:
        line(f"| {f['community']} | {f['acts']} | {f['slm_label']} | {f['slm_domain']} | {f['domain_agreement_across_prompts']} | {f['draft_label'][:45]} | {'yes' if f['domain_matches_draft'] else 'NO'} | {f['review_reason']} |")
    line("\n## SLM descriptions (plain English)\n")
    for f in final: line(f"- **{f['community']} {f['slm_label']}** ({f['acts']} Acts): {f['slm_description']}")
    (OUT / "summary.md").write_text("\n".join(L), encoding="utf-8"); print("\nSaved -> outputs/leiden_labels/")


if __name__ == "__main__":
    main()
