"""
One-off connectivity test — confirms Ollama is running and the model
responds, before we build any real extraction logic on top of it.
"""

import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2.5:7b-instruct",
        "prompt": "Reply with exactly the word: working",
        "stream": False,
        "options": {"temperature": 0},
    },
    timeout=60,
)

print("Status:", response.status_code)
print("Response:", response.json()["response"])