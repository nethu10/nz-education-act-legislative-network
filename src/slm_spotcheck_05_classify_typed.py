"""
slm_spotcheck_05_classify_typed.py

Classifies every edge in outputs/spotcheck/sample_typed.json with the same local SLM as
Stage 3/4 (Qwen2.5:7b-instruct via Ollama, temperature 0, via src/extraction_utils.py) and
reports agreement with the rule-based label, separately for AMENDMENT and CITATION edges.

Agreement definitions
  amendment edge : SLM type == "amendment"
  citation edge  : strict  = SLM type == "citation"
                   lenient = SLM type in {"citation", "definition_reference"}
                   (a definition that points at another Act is still a legitimate citation of it)
Also reports Wilson 95% confidence intervals, agreement by layer, by evidence source, by SLM
confidence, and what the SLM called the disagreements.

Resumable: results are written after every call; re-running skips already-classified rows.
Run from repo root:  python src/slm_spotcheck_05_classify_typed.py
Outputs: outputs/spotcheck/results_typed.json, outputs/spotcheck/results_typed_summary.md
"""
import json, math, sys, time
from collections import defaultdict, Counter
from pathlib import Path
import requests

sys.path.insert(0, "src")
try:
    from extraction_utils import OLLAMA_URL, MODEL
except ImportError:
    OLLAMA_URL, MODEL = "http://localhost:11434/api/generate", "qwen2.5:7b-instruct"
    print(f"!! extraction_utils import failed; using {OLLAMA_URL} / {MODEL}")

SAMPLE = Path("outputs/spotcheck/sample_typed.json")
RESULTS = Path("outputs/spotcheck/results_typed.json")
SUMMARY = Path("outputs/spotcheck/results_typed_summary.md")
ALLOWED = {"definition_reference", "citation", "amendment", "cross_reference", "power_or_duty"}


def classify(prompt, timeout=180):
    r = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False,
                                        "format": "json", "options": {"temperature": 0}}, timeout=timeout)
    r.raise_for_status()
    return json.loads(r.json()["response"])


def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def agree(r, lenient=False):
    t = r["slm_type"]
    if r["rule_based_edge_type"] == "amendment": return t == "amendment"
    return t in (("citation", "definition_reference") if lenient else ("citation",))


def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100*k/n:.1f}%, 95% CI {100*lo:.0f}-{100*hi:.0f}%)" if n else "0/0"


def main():
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    done = {(r["layer"], r["source"], r["target"], r["rule_based_edge_type"]): r
            for r in (json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else [])}
    print(f"{len(sample)} sampled edges; {len(done)} already classified. Model {MODEL}\n")
    results = list(done.values())
    for i, e in enumerate(sample, 1):
        key = (e["layer"], e["source"], e["target"], e["rule_based_edge_type"])
        if key in done: continue
        try:
            out = classify(e["prompt"])
            res = {**{k: v for k, v in e.items() if k != "prompt"},
                   "slm_type": out.get("type"), "slm_confidence": out.get("confidence"),
                   "slm_justification": out.get("justification")}
            results.append(res)
            RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[{i}/{len(sample)}] {e['layer']} {e['rule_based_edge_type'][:4]} -> SLM {res['slm_type']}"
                  f"{'' if agree(res) else '  <-- differs'}")
        except Exception as ex:
            print(f"[{i}/{len(sample)}] FAILED {type(ex).__name__}: {ex}")
        time.sleep(0.2)

    L = []
    def line(s=""): L.append(s); print(s)
    line("# SLM spot-check on the final typed graph\n")
    line(f"Model: {MODEL}; classified {len(results)}/{len(sample)} sampled edges\n")
    line("## Headline\n")
    line("| Edge type | Agreement | Lenient agreement |"); line("|---|---|---|")
    for et in ("amendment", "citation"):
        rows = [r for r in results if r["rule_based_edge_type"] == et]
        k = sum(agree(r) for r in rows); kl = sum(agree(r, True) for r in rows)
        line(f"| {et} | {fmt(k, len(rows))} | {fmt(kl, len(rows)) if et == 'citation' else 'n/a'} |")
    tot = sum(agree(r) for r in results)
    line(f"| **all** | {fmt(tot, len(results))} | |\n")

    line("## By layer and edge type (strict)\n")
    line("| Layer | Amendment | Citation |"); line("|---|---|---|")
    for layer in ("SG1", "SG2", "SG3", "SG4", "SG5"):
        cells = []
        for et in ("amendment", "citation"):
            rows = [r for r in results if r["layer"] == layer and r["rule_based_edge_type"] == et]
            cells.append(f"{sum(agree(r) for r in rows)}/{len(rows)}" if rows else "-")
        line(f"| {layer} | {cells[0]} | {cells[1]} |")
    line("\n## By evidence source (strict)\n")
    line("| Evidence | Agreement |"); line("|---|---|")
    by = defaultdict(list)
    for r in results: by[(r["rule_based_edge_type"], r["snippet_source"])].append(r)
    for (et, ss), rows in sorted(by.items()):
        line(f"| {et} / {ss} | {fmt(sum(agree(r) for r in rows), len(rows))} |")
    line("\n## By SLM confidence (strict)\n")
    line("| Confidence | Agreement |"); line("|---|---|")
    byc = defaultdict(list)
    for r in results: byc[r.get("slm_confidence")].append(r)
    for c, rows in sorted(byc.items(), key=lambda kv: str(kv[0])):
        line(f"| {c} | {fmt(sum(agree(r) for r in rows), len(rows))} |")
    line("\n## What the SLM called the disagreements\n")
    line("| Rule-based | SLM type | Count |"); line("|---|---|---|")
    dis = Counter((r["rule_based_edge_type"], r["slm_type"]) for r in results if not agree(r))
    for (rb, st), c in sorted(dis.items(), key=lambda kv: -kv[1]): line(f"| {rb} | {st} | {c} |")
    SUMMARY.write_text("\n".join(L), encoding="utf-8")
    print(f"\nSaved -> {RESULTS}, {SUMMARY}\nPaste back the summary tables above.")


if __name__ == "__main__":
    main()
