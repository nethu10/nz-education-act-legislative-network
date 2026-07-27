"""
Final, bounded attempt to recover LMS267770, the one record that produces
degenerate (endless whitespace) JSON on the standard prompt. Adds a hard
output-length cap and a repetition penalty as a disclosed, one-off
mitigation. If this still fails, the record should be documented as a
single explained exclusion (1 of 1687, 0.06%) rather than pursued further.
"""

import json
from pathlib import Path
import requests
from extraction_utils import PROMPT_TEMPLATE, OLLAMA_URL, MODEL

provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}
record = provisions["LMS267770"]
prompt = PROMPT_TEMPLATE.format(heading=record["heading"], text=record["text"])

response = requests.post(
    OLLAMA_URL,
    json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 800,      # hard cap so it cannot spiral into endless whitespace
            "repeat_penalty": 1.3,   # discourage the repetitive degeneration seen last time
        },
    },
    timeout=180,
)
raw = response.json()["response"]
print("RAW OUTPUT:\n", raw)

try:
    parsed = json.loads(raw)
    print("\nParsed successfully.")
    results = json.loads(Path("data/processed/extractions_full.json").read_text())
    results = [r for r in results if r["provision_id"] != "LMS267770"]
    results.append({"provision_id": "LMS267770", "extraction": parsed})
    Path("data/processed/extractions_full.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Saved. Total records: {len(results)} / {len(provisions)}")
except json.JSONDecodeError as e:
    print(f"\nStill failed: {e}")
    print("Recommendation: document as a single explained exclusion (1/1687, 0.06%).")