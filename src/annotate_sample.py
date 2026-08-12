"""
Interactive terminal annotator for the Stage 4 manual validation sample.
Shows one relation at a time against its real source text, records your
judgement, and saves after every single answer — so stopping partway
through and resuming later never loses work.
"""

import json
from pathlib import Path

SAMPLE_PATH = Path("data/processed/stage4_manual_sample.json")

sample = json.loads(SAMPLE_PATH.read_text())

todo = [r for r in sample if not r["judgement"]]
done = len(sample) - len(todo)
print(f"{done}/{len(sample)} already judged. {len(todo)} remaining.\n")
print("Judgement guide:")
print("  c = correct        (relation type AND content both accurate)")
print("  i = incorrect       (wrong type, or fabricated/unsupported content)")
print("  p = partially right (right general idea, but imprecise or incomplete)")
print("  s = skip for now (revisit later)")
print("  q = save and quit\n")

for record in sample:
    if record["judgement"]:
        continue

    print("=" * 70)
    print(f"[{record['provision_id']}] {record['heading']}  |  type: {record['type']}")
    print("=" * 70)
    print("SOURCE TEXT:")
    print(record["source_text"] or "(empty)")
    print("\nSLM DESCRIPTION:")
    print(record["slm_description"])
    print()

    answer = input("Judgement [c/i/p/s/q]: ").strip().lower()

    if answer == "q":
        SAMPLE_PATH.write_text(json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")
        print("\nSaved. Run this script again anytime to resume.")
        break

    if answer == "s":
        print()
        continue

    if answer not in ("c", "i", "p"):
        print("Not recognised, treating as skip.\n")
        continue

    label = {"c": "correct", "i": "incorrect", "p": "partial"}[answer]
    notes = input("Optional note (Enter to skip): ").strip()

    record["judgement"] = label
    record["notes"] = notes

    SAMPLE_PATH.write_text(json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {label}\n")
else:
    print("All records judged!")