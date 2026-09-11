"""
Targeted SLM pass focused specifically on external-Act citations --
runs only over the short, already-extracted relation descriptions
(not full provision text), so it's fast even on a laptop. Ollama must
be running (check with test_ollama.py first).
"""

import json
import re
import requests
from pathlib import Path

extractions = json.loads(Path("data/processed/extractions_full.json").read_text())

# Only check descriptions that plausibly mention another Act/Regulation/Rule
candidate_pattern = re.compile(r"\b(Act|Regulation|Rule)s?\b", re.IGNORECASE)
candidates = []
for e in extractions:
    for rel in e["extraction"].get("relations", []):
        if isinstance(rel, dict) and candidate_pattern.search(rel.get("description", "")):
            candidates.append({"provision_id": e["provision_id"], "type": rel.get("type"), "description": rel.get("description")})

print(f"Candidate descriptions to check: {len(candidates)} (out of full dataset -- most already filtered out)")

PROMPT = """You are checking one short sentence for a mention of a DIFFERENT law (not the Education and Training Act 2020 itself).

Sentence: "{description}"

If it names another Act, Regulation, or Rule, respond with ONLY this JSON, nothing else:
{{"external_act_mentioned": true, "act_name": "the exact name mentioned", "relationship": "citation"}}

If it does NOT name another specific law (e.g. it's about internal sections, people, or generic terms), respond with ONLY:
{{"external_act_mentioned": false}}
"""

results = []
for i, c in enumerate(candidates):
    prompt = PROMPT.format(description=c["description"])
    try:
        r = requests.post("http://localhost:11434/api/generate",
                           json={"model": "qwen2.5:7b-instruct", "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}},
                           timeout=60)
        parsed = json.loads(r.json()["response"])
        if parsed.get("external_act_mentioned"):
            results.append({**c, "act_name": parsed.get("act_name"), "relationship": "citation"})
    except Exception as ex:
        print(f"  skipped {c['provision_id']} ({type(ex).__name__})")
    if (i + 1) % 20 == 0:
        print(f"  {i+1}/{len(candidates)} checked, {len(results)} confirmed so far")

Path("data/processed/citation_relationships_slm.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nConfirmed citation relationships: {len(results)}")
print(f"Saved to data/processed/citation_relationships_slm.json")