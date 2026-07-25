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
    {{"type": "one of the five types below", "description": "short description of the relationship"}}
  ],
  "summary": "one-sentence plain-English summary of what this provision does",
  "topic_tags": ["2-4 short keywords describing the policy area"]
}}

Relation type definitions — use exactly one of these five, and nothing else:
- "definition_reference": use ONLY when this text itself states what a term means, using patterns like "X means...", "X has the meaning given in...", or "X includes..."
- "citation": this text refers to another Act, regulation, or provision to establish context, a condition, or an exemption — without defining a term and without changing that other Act's wording
- "amendment": this text formally changes the wording of another Act or Schedule, or records that another Act changed this one
- "cross_reference": an internal, procedural pointer within this Act that is not a definition, citation, or amendment (e.g. commencement dates, references between sections of this same Act)
- "power_or_duty": this text grants, describes, or constrains a power, function, duty, or discretion held by a person or body under this Act (e.g. "the Minister may...", "the board must...", conditions for exercising a power, validating or invalidating a decision). Do NOT use "amendment" or "definition_reference" for this — use "power_or_duty" instead.

Do not invent any other category name under any circumstances. Respond only in English for every "type" and "description" value, even though entity names may legitimately include Māori terms exactly as written in the source text (e.g. wānanga, Kura Kaupapa Māori, te reo Māori).

Provision heading: {heading}
Provision text: {text}

Return ONLY the JSON object, nothing else."""

ALLOWED_RELATION_TYPES = {"definition_reference", "citation", "amendment", "cross_reference", "power_or_duty"}


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


def validate_extraction(extraction):
    warnings = []
    relations = extraction.get("relations", [])
    for rel in relations:
        rel_type = rel.get("type")
        if rel_type not in ALLOWED_RELATION_TYPES:
            warnings.append("Unexpected relation type: " + repr(rel_type))
    return warnings