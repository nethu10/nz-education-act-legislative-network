"""
Fetch the raw, unparsed response for the one record that keeps failing
JSON parsing, so we can see exactly what the model produced instead of
just Python's error message about it.
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
    json={"model": MODEL, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}},
    timeout=180,
)
raw = response.json()["response"]

print("RAW OUTPUT:")
print(raw)
print("\n\nLENGTH:", len(raw), "characters")