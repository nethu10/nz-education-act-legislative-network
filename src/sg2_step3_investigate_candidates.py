"""
SG2, step 3: diagnose self-referential and bulk/omnibus candidates
before deciding the SG2 threshold. Flags for review rather than
auto-excluding -- same practice as SG1's cleaning stage.
"""
import json
import re
from pathlib import Path

OUT_DIR = Path("data/processed")
candidates = json.loads((OUT_DIR / "sg2_amendment_candidates.json").read_text())
sg1_acts = json.loads((OUT_DIR / "sg1_final_list.json").read_text())

def base_words(name):
    """Strip year, 'Amendment', 'Act', '(No N)', punctuation -- leaves the
    core topic words to compare a candidate against its source Act."""
    n = re.sub(r"\(.*?\)", "", name)              # drop parenthetical bits
    n = re.sub(r"\b(19|20)\d{2}\b", "", n)         # drop years
    n = re.sub(r"\b(Amendment|Act|No)\b", "", n, flags=re.IGNORECASE)
    words = [w.lower() for w in re.findall(r"[A-Za-zĀ-ſ]+", n)]
    return set(words)

source_names = [a["act"] for a in sg1_acts]

self_ref_flags = []
for c in candidates:
    cand_base = base_words(c["act"])
    if not cand_base:
        continue
    for src in c["linked_from"]:
        src_base = base_words(src)
        if src_base and cand_base.issubset(src_base) | src_base.issubset(cand_base):
            if "amendment" in c["act"].lower():  # only flag if it's actually an Amendment Act
                self_ref_flags.append({"candidate": c["act"], "score": c["combined_score"],
                                        "likely_self_ref_to": src})
                break

print(f"Flagged as likely self-referential ({len(self_ref_flags)} candidates):")
for f in self_ref_flags:
    print(f"  {f['candidate']} (score {f['score']}) -- likely {f['likely_self_ref_to']}'s own history")

# omnibus/bulk pattern: NZ's annual "Taxation (Annual Rates for ..., ...) Act"
# naming convention, plus any repeat of confirmed SG1 bulk-event Acts
OMNIBUS_PATTERN = re.compile(r"^Taxation \(Annual Rates for", re.IGNORECASE)
omnibus_flags = [c for c in candidates if OMNIBUS_PATTERN.match(c["act"])]
known_bulk_repeat = [c for c in candidates if c["act"] in
                      ("Secondary Legislation Act 2021", "Public Service Act 2020",
                       "Employment Relations (Pay Deductions) Act 2025")]

print(f"\nOmnibus 'Taxation (Annual Rates...)' Acts found: {len(omnibus_flags)}")
total_omnibus_score = sum(c["combined_score"] for c in omnibus_flags)
print(f"  Combined score across all of them: {total_omnibus_score}")
for c in sorted(omnibus_flags, key=lambda x: -x["combined_score"])[:10]:
    print(f"    {c['act']} (score {c['combined_score']}, {len(c['linked_from'])} SG1 links)")

print(f"\nKnown bulk-event Acts reappearing from SG1: {len(known_bulk_repeat)}")
for c in known_bulk_repeat:
    print(f"    {c['act']} (score {c['combined_score']}, {len(c['linked_from'])} SG1 links)")