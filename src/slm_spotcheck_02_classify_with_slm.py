"""
slm_spotcheck_02_classify_with_slm.py

Second half of the SLM validation spot-check. Reads outputs/spotcheck/sample.json
(built by slm_spotcheck_01_build_sample.py) and sends each entry's prompt to
the same local SLM used in Stage 3/4 -- Qwen2.5:7b-instruct via Ollama, same
endpoint, same temperature=0 -- reusing the connection settings from
src/extraction_utils.py so this stays consistent with the rest of the
pipeline rather than drifting onto different settings.

For each sampled edge, records:
  - what the rule-based (tag-only) extraction assumed: always "amendment"
    (amendment_outgoing/amendment_incoming/final_list_link/internal_link
    are all, by construction, found via <history-note> or
    <schedule.amendments.group2> -- the two tags the rule-based method
    reads -- so "amendment" is the implicit label on every one of them)
  - what the SLM independently classified it as, reading the real text
  - whether they agree

Prints an agreement-rate summary (overall, and broken down by layer and by
snippet_source, since history_note-sourced snippets have much less text for
the SLM to work with than schedule_amendment ones and may validate
differently -- that split is itself worth reporting, not just the topline
number).

Requires Ollama running locally with qwen2.5:7b-instruct pulled (same
requirement as Stage 3 -- if that worked before, this will too).

Run from the repo root:
    python src/slm_spotcheck_02_classify_with_slm.py

Output: outputs/spotcheck/results.json + a printed summary to paste back.
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

sys.path.insert(0, "src")
try:
    from extraction_utils import OLLAMA_URL, MODEL  # reuse Stage 3's exact settings
except ImportError:
    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen2.5:7b-instruct"
    print("!! couldn't import src/extraction_utils.py -- falling back to hardcoded "
          f"OLLAMA_URL={OLLAMA_URL!r} MODEL={MODEL!r}. Check these match Stage 3 if this "
          "script is in a different location than expected.")

SAMPLE_PATH = Path("outputs/spotcheck/sample.json")
RESULTS_PATH = Path("outputs/spotcheck/results.json")
ALLOWED_TYPES = {"definition_reference", "citation", "amendment", "cross_reference", "power_or_duty"}


def classify(prompt, timeout=180):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    raw = response.json()["response"]
    return json.loads(raw)


def main():
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(sample)} sampled edges from {SAMPLE_PATH}")
    print(f"Classifying with {MODEL} via {OLLAMA_URL} ...\n")

    results = []
    n_ok, n_failed = 0, 0

    for i, entry in enumerate(sample, 1):
        try:
            slm_out = classify(entry["prompt"])
            slm_type = slm_out.get("type")
            if slm_type not in ALLOWED_TYPES:
                print(f"  [{i}/{len(sample)}] !! unexpected type {slm_type!r} from SLM -- keeping as-is")
            result = {
                **{k: v for k, v in entry.items() if k != "prompt"},
                "slm_type": slm_type,
                "slm_confidence": slm_out.get("confidence"),
                "slm_justification": slm_out.get("justification"),
                "agrees_with_rule_based": slm_type == "amendment",
            }
            results.append(result)
            n_ok += 1
            mark = "AGREE" if result["agrees_with_rule_based"] else f"DISAGREE (SLM says {slm_type})"
            print(f"  [{i}/{len(sample)}] {entry['source'][:40]!r} -> {entry['target'][:40]!r}: {mark}")
        except Exception as e:
            print(f"  [{i}/{len(sample)}] FAILED: {type(e).__name__}: {e}")
            n_failed += 1
        time.sleep(0.2)

    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*70}")
    print(f"Classified {n_ok}/{len(sample)} ({n_failed} failed)")
    print(f"{'='*70}")

    n_agree = sum(1 for r in results if r["agrees_with_rule_based"])
    print(f"\nOverall agreement with rule-based 'amendment' label: {n_agree}/{len(results)} "
          f"({100*n_agree/len(results):.1f}%)" if results else "no results")

    print("\nBy layer:")
    by_layer = defaultdict(lambda: [0, 0])
    for r in results:
        by_layer[r["layer"]][1] += 1
        if r["agrees_with_rule_based"]:
            by_layer[r["layer"]][0] += 1
    for layer in ["SG1", "SG2", "SG3", "SG4", "SG5"]:
        if layer in by_layer:
            a, t = by_layer[layer]
            print(f"  {layer}: {a}/{t} ({100*a/t:.1f}%)")

    print("\nBy snippet source (schedule_amendment = real prose, history_note = thin evidence):")
    by_snip = defaultdict(lambda: [0, 0])
    for r in results:
        by_snip[r["snippet_source"]][1] += 1
        if r["agrees_with_rule_based"]:
            by_snip[r["snippet_source"]][0] += 1
    for k, (a, t) in by_snip.items():
        print(f"  {k}: {a}/{t} ({100*a/t:.1f}%)")

    disagreements = [r for r in results if not r["agrees_with_rule_based"]]
    if disagreements:
        print(f"\nWhere the SLM disagreed ({len(disagreements)} cases) -- what it called them instead:")
        by_type = defaultdict(int)
        for r in disagreements:
            by_type[r["slm_type"]] += 1
        for t, c in sorted(by_type.items(), key=lambda kv: -kv[1]):
            print(f"  {t}: {c}")
        print("\nFull disagreement details are in results.json (slm_justification field per row).")

    print(f"\nSaved -> {RESULTS_PATH}")
    print("Paste back the printed summary above (not the full file) so we can write this up.")


if __name__ == "__main__":
    main()