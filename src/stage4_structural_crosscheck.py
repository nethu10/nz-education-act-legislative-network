"""
Stage 4, Part 1: Structural cross-check.

Compares the SLM's extracted relations against the internal_refs and
external_refs already captured directly from the XML's own <intref>/
<extref> tags in Stage 2 — official, structural evidence requiring no
manual work.

Two different questions, checked two different ways:
  - Provisions WITH a real structural reference: did the SLM engage with
    it at all? (Confirmed: reference content legitimately appears inside
    ANY relation type, not just citation/cross_reference/amendment — so
    this just checks the provision wasn't left with zero relations.)
  - Provisions with NO structural reference: does the SLM claim a
    reference-flavoured relation exists anyway? (A potential false
    positive check — needs the narrower type check, not "any relation".)
"""

import json
from pathlib import Path

provisions = {p["id"]: p for p in json.loads(Path("data/processed/provisions.json").read_text())}
extractions = {e["provision_id"]: e["extraction"] for e in json.loads(Path("data/processed/extractions_full.json").read_text())}

REF_BACKED_TYPES = {"citation", "cross_reference", "amendment"}

has_refs_total = 0
has_refs_and_found = 0
no_refs_total = 0
no_refs_but_found = 0

missed_examples = []
extra_examples = []

for pid, prov in provisions.items():
    extraction = extractions.get(pid)
    if not extraction:
        continue

    has_structural_ref = bool(prov.get("internal_refs")) or bool(prov.get("external_refs"))
    relations = extraction.get("relations", [])

    if has_structural_ref:
        has_refs_total += 1
        found = len(relations) > 0
        if found:
            has_refs_and_found += 1
        elif len(missed_examples) < 5:
            missed_examples.append(pid)
    else:
        no_refs_total += 1
        found = any(isinstance(r, dict) and r.get("type") in REF_BACKED_TYPES for r in relations)
        if found:
            no_refs_but_found += 1
            if len(extra_examples) < 5:
                extra_examples.append(pid)

print(f"Provisions WITH a real structural reference (intref/extref): {has_refs_total}")
print(f"  SLM engaged with it (has at least one relation): {has_refs_and_found} ({100*has_refs_and_found/has_refs_total:.1f}%)")
print(f"  SLM found NONE (genuine possible miss): {has_refs_total - has_refs_and_found}")
print(f"  Example possible misses: {missed_examples}")

print(f"\nProvisions with NO structural reference: {no_refs_total}")
print(f"  SLM still reported citation/cross_reference/amendment: {no_refs_but_found} ({100*no_refs_but_found/no_refs_total:.1f}%)")
print("  (Not automatically wrong \u2014 some citations are prose-only, e.g. naming an Act with no hyperlink \u2014 worth a quick look, not proof of error.)")
print(f"  Example candidates: {extra_examples}")