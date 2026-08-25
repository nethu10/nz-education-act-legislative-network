"""
Records the methodological reason for using 'latest' rather than the
seed Act's pinned date for the 13 Stage 6 target Acts -- a deliberate,
evidence-based decision, not an inconsistency to gloss over.
"""

import json
from pathlib import Path

note = {
    "decision": "Stage 6 target Acts fetched at 'latest' rather than pinned to 2026-07-01",
    "reason": (
        "Each Act's version history on the NZ Legislation website is independent -- "
        "a dated snapshot only exists for a given Act if that Act itself was amended "
        "on or near that date. The seed Act (Education and Training Act 2020) has a "
        "confirmed snapshot at 2026-07-01. Testing showed only 1 of 13 target Acts "
        "(Income Tax Act 2007, one of the most frequently amended Acts in NZ) shared "
        "that exact date; the remaining 12, including six rarely-amended university "
        "Acts from 1961-1963, returned 404 at that specific date and succeeded only "
        "once switched to 'latest'."
    ),
    "implication": (
        "The 13 Stage 6 target Acts reflect their current version as at the fetch "
        "date, distinct from the seed Act's fixed 1 July 2026 snapshot. This is "
        "considered an acceptable scope decision since these Acts provide "
        "supporting network context and do not undergo the same SLM extraction "
        "and validation rigor applied to the seed Act."
    ),
    "fetch_date": "run this script's own execution date if exact record needed",
}

Path("data/processed/stage6_version_note.json").write_text(
    json.dumps(note, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("Saved to data/processed/stage6_version_note.json")
print(json.dumps(note, indent=2, ensure_ascii=False))