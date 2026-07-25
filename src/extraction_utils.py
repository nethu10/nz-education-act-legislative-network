"""
Shared utilities for Stage 3 SLM extraction — the prompt template and
the function that calls Ollama. Imported by test scripts and the final
full-dataset extraction script, so there's one source of truth for the
prompt rather than copies drifting out of sync.
"""

import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"

PROMPT_TEMPLATE = """You are extracting structured legal information from New Zealand legislative text.

Read the following provision from the Education and Training Act 2020 and return ONLY a JSON object with this exact structure:

{{
  "entities": ["list of legal actors, roles, or defined concepts mentioned"],
  "relations": [
    {{"type": "one of the four types below", "description": "short description of the relationship"}}
  ],
  "summary": "one-sentence plain-English summary of what this provision does",
  "topic_tags": ["2-4 short keywords describing the policy area"]
}}

Relation type definitions — use exactly one of these:
- "definition_reference": use ONLY when this text itself states what a term means, using patterns like "X means...", "X has the meaning given in...", or "X includes...". If no term is being defined, do not use this category.
- "citation": this text refers to another Act, regulation, or provision to establish context, a condition, an exemption, or how/when it applies — without itself defining a term and without changing that other Act's wording
- "amendment": this text formally changes the wording of another Act or Schedule, or records that another Act changed this one
- "cross_reference": an internal, procedural pointer within this Act that is not a definition, citation, or amendment (e.g. commencement dates, references between sections of this same Act)

Provision heading: {heading}
Provision text: {text}

Return ONLY the JSON object, nothing else."""


def extract(heading: str, text: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(heading=heading, text=text)
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        },
        timeout=180,
    )
    raw = response.json()["response"]
    return json.loads(raw)