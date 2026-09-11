"""
Builds one complete, categorized list of every external Act connected
to the seed Act, labelled by relationship type -- amendment (both
directions, with operation type: repeal/insert/replace/omit) and
citation (best-effort, extracted from the SLM's own Stage 3 findings).
Uses only data already on disk -- no new fetching required.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# ---------- Part 1: Amendment-type connections (confirmed, complete) ----------

outgoing = json.loads(Path("data/processed/outgoing_amendments.json").read_text())
incoming = json.loads(Path("data/processed/amendment_records.json").read_text())

def classify_operation(text):
    """Classifies the specific type of amendment from the actual amendment
    text -- outgoing_amendments.json doesn't carry a structured operation
    field the way incoming records do, so this uses keyword matching on
    the real wording (e.g. 'repeal', 'insert', 'replace')."""
    t = text.lower()
    if re.search(r"\brepeal(s|ed|ing)?\b", t):
        return "repeal"
    if re.search(r"\binsert(s|ed|ing)?\b", t):
        return "insert"
    if re.search(r"\breplace(s|d|ing)?\b", t):
        return "replace"
    if re.search(r"\bomit(s|ted|ting)?\b", t):
        return "omit"
    return "amend (other)"

outgoing_by_act = defaultdict(lambda: {"count": 0, "operations": defaultdict(int)})
for r in outgoing:
    act = r.get("target_act")
    if not act:
        continue
    op = classify_operation(r.get("text", ""))
    outgoing_by_act[act]["count"] += 1
    outgoing_by_act[act]["operations"][op] += 1

incoming_by_act = defaultdict(lambda: {"count": 0, "operations": defaultdict(int)})
for r in incoming:
    act = r.get("amending_act")
    if not act:
        continue
    op = (r.get("operation") or "unspecified").lower()
    incoming_by_act[act]["count"] += 1
    incoming_by_act[act]["operations"][op] += 1

print(f"Outgoing (this Act -> other Acts): {len(outgoing_by_act)} distinct Acts")
print(f"Incoming (other Acts -> this Act): {len(incoming_by_act)} distinct Acts")

# ---------- Part 2: Citation-type connections (best-effort) ----------

extractions = json.loads(Path("data/processed/extractions_full.json").read_text())
ACT_NAME_PATTERN = re.compile(r"[A-Z][A-Za-z,()\u2019' -]+ Act \d{4}")

citation_mentions = defaultdict(lambda: {"count": 0, "example_provisions": []})
for e in extractions:
    pid = e["provision_id"]
    for rel in e["extraction"].get("relations", []):
        if not isinstance(rel, dict) or rel.get("type") not in ("citation", "cross_reference"):
            continue
        for match in ACT_NAME_PATTERN.findall(rel.get("description", "")):
            name = match.strip()
            if "Education and Training Act" in name:
                continue
            citation_mentions[name]["count"] += 1
            if len(citation_mentions[name]["example_provisions"]) < 3:
                citation_mentions[name]["example_provisions"].append(pid)

print(f"Distinct external Acts found via AI citation mentions (best-effort): {len(citation_mentions)}")

# ---------- Part 3: Combine into one master, labelled table ----------

master = {}
def ensure(act):
    if act not in master:
        master[act] = {"amends_this_act": False, "amended_by_this_act": False, "cited_by_this_act": False,
                        "outgoing_count": 0, "incoming_count": 0, "citation_count": 0, "operations": set()}
    return master[act]

for act, info in outgoing_by_act.items():
    m = ensure(act); m["amended_by_this_act"] = True; m["outgoing_count"] = info["count"]; m["operations"] |= set(info["operations"])
for act, info in incoming_by_act.items():
    m = ensure(act); m["amends_this_act"] = True; m["incoming_count"] = info["count"]; m["operations"] |= set(info["operations"])
for act, info in citation_mentions.items():
    m = ensure(act); m["cited_by_this_act"] = True; m["citation_count"] = info["count"]

output = []
for act, m in master.items():
    output.append({
        "act_name": act, "amends_this_act": m["amends_this_act"], "amended_by_this_act": m["amended_by_this_act"],
        "cited_by_this_act": m["cited_by_this_act"], "outgoing_amendment_count": m["outgoing_count"],
        "incoming_amendment_count": m["incoming_count"], "citation_mention_count": m["citation_count"],
        "operation_types": sorted(m["operations"]),
    })
output.sort(key=lambda x: -(x["outgoing_amendment_count"] + x["incoming_amendment_count"] + x["citation_mention_count"]))

Path("data/processed/external_acts_relationship_master.json").write_text(
    json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

amend_only = sum(1 for x in output if (x["amends_this_act"] or x["amended_by_this_act"]) and not x["cited_by_this_act"])
cite_only = sum(1 for x in output if x["cited_by_this_act"] and not (x["amends_this_act"] or x["amended_by_this_act"]))
both = sum(1 for x in output if x["cited_by_this_act"] and (x["amends_this_act"] or x["amended_by_this_act"]))

print(f"\nTOTAL distinct external Acts (all relationship types): {len(output)}")
print(f"  Amendment-type only: {amend_only}")
print(f"  Citation-type only: {cite_only}")
print(f"  Both amendment AND citation: {both}")
print(f"\nSaved to data/processed/external_acts_relationship_master.json")