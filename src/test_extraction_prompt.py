"""
Stage 3, first test: run the joint extraction prompt on ONE provision,
to validate the JSON schema and prompt design before scaling to all
~1700 records in provisions.json.
"""

import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"

# A real, non-trivial record from provisions.json — has actual content
# and an internal reference, without being the giant Interpretation blob.
test_record = {
    "id": "LMS1554927",
    "heading": "Interpretation",
    "text": "academic freedom has the meaning given in section 267(4)",
}

PROMPT_TEMPLATE = """You are extracting structured legal information from New Zealand legislative text.

Read the following provision from the Education and Training Act 2020 and return ONLY a JSON object with this exact structure:

{{
  "entities": ["list of legal actors, roles, or defined concepts mentioned"],
  "relations": [
    {{"type": "one of: definition_reference, citation, amendment, cross_reference", "description": "short description of the relationship"}}
  ],
  "summary": "one-sentence plain-English summary of what this provision does",
  "topic_tags": ["2-4 short keywords describing the policy area"]
}}

Provision heading: {heading}
Provision text: {text}

Return ONLY the JSON object, nothing else."""

prompt = PROMPT_TEMPLATE.format(heading=test_record["heading"], text=test_record["text"])

response = requests.post(
    OLLAMA_URL,
    json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",       # tells Ollama to constrain output to valid JSON
        "options": {"temperature": 0},  # deterministic, per your methodology
    },
    timeout=60,
)

raw_output = response.json()["response"]
print("Raw model output:\n", raw_output)

parsed = json.loads(raw_output)
print("\nParsed successfully:")
print(json.dumps(parsed, indent=2))