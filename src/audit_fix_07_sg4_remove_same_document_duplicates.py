"""
audit_fix_07_sg4_remove_same_document_duplicates.py

Removes the 25 SAME_DOCUMENT pairs found in the SG4 filename-collision
audit (data/processed/sg4_collision_full_audit.md) -- cases where two
different candidate-name strings in SG4 both resolved to the exact same
real document (confirmed live: rename/previous-title, Schedule-of-parent
fragment, or truncated/reordered/prefix-variant of the same title).

For each pair, one name is kept (the canonical/current/clean title) and
the other is dropped entirely from SG4's candidate lists and identifiers
-- same pattern as audit_fix_03/04/05's SG3 cross-layer duplicate
removals, just applied intra-layer within SG4 this time.

DROP_NAMES below are the 25 names being removed, each paired with a
one-line reason. Where "keep vs drop" was a judgment call rather than a
clean canonical-title match (one case: 2017_24, both candidate strings
carry extra baggage -- the cleaner, grammatically normal title was kept
over the messier one that had a "(previously named the ...)" clause
baked into the title field itself), it's called out explicitly.
"""
import json
from pathlib import Path

FINAL_LIST = Path("data/processed/sg4_final_list.json")
COMBINED_FINAL_LIST = Path("data/processed/sg4_combined_final_list.json")
IDENTIFIERS = Path("data/processed/sg4_act_identifiers.json")

# act name (exact string, dropped) -> reason
DROP_NAMES = {
    "Schedule 1 of the Financial Markets Authority Act 2011":
        "fragment of Financial Markets Authority Act 2011 (user-confirmed anchor)",
    "Schedule 1 of the Resource Management Act 1991":
        "fragment of Resource Management Act 1991",
    "Transit New Zealand Act 1989":
        "previous title of Government Roading Powers Act 1989 (user-confirmed)",
    "Schedule 7 of the Local Government Act 2002":
        "fragment of Local Government Act 2002",
    "Summary Proceedings Act 1957 (1957 No 87) (RS Vol 9, p 583)":
        "citation-suffix variant of Summary Proceedings Act 1957",
    "Personal and Property Rights Act 1988":
        "short-form variant of Protection of Personal and Property Rights Act 1988",
    "Births, Deaths, and Marriages Registration Act 1995":
        "previous title of Births, Deaths, Marriages, and Relationships Registration Act 1995",
    "Local Government Act 1974 (1974 No 66) (RS Vol 25, p 1)":
        "citation-suffix variant of Local Government Act 1974",
    "Securities Act 1978 (1978 No 103) (RS Vol 15, p 533)":
        "citation-suffix variant of Securities Act 1978",
    "Justice (Restructuring) Act 1995":
        "short-form variant of Department of Justice (Restructuring) Act 1995",
    "Ombudsmen Act 1975 (1975 No 9) (RS Vol 21, p 657)":
        "citation-suffix variant of Ombudsmen Act 1975",
    "Persons with Disabilities) Act 2008":
        "truncated citation fragment of Disability (United Nations Convention on the "
        "Rights of Persons with Disabilities) Act 2008 (user-confirmed anchor)",
    "Parliament) Amendment Act 2002":
        "truncated fragment of Remuneration Authority (Members of Parliament) Amendment Act 2002",
    "Support Workers (Pay Equity) Settlements Act 2017 (previously named the Care and "
    "Support Workers (Pay Equity) Settlement Act 2017)":
        "same document as Care and Support Workers (Pay Equity) Settlement Act 2017 "
        "(user-confirmed rename); dropped the messier string that has the "
        "'previously named' clause embedded in the title field itself -- judgment "
        "call, kept the clean grammatical title over the technically-current one",
    "New Zealand Act 2002":
        "truncated fragment of Sport and Recreation New Zealand Act 2002",
    "Child, Youth and Family Services Act 1999":
        "short-form variant of Department of Child, Youth and Family Services Act 1999",
    "Children Act 2004":
        "truncated fragment of Care of Children Act 2004",
    "National Bank of New Zealand Limited Act 1994 (1994 No 3(P))":
        "citation-suffix variant of National Bank of New Zealand Limited Act 1994",
    "Reserve Bank of New Zealand Act 1989":
        "previous title of Banking (Prudential Supervision) Act 1989 (live autocomplete-confirmed)",
    "Te Ture mā Te Reo Māori 2016":
        "short-form substring of Te Ture mā Te Reo Māori 2016/the Māori Language Act 2016",
    "Institute of Chartered Accountants of New Zealand Act 1996":
        "word-reordered variant of New Zealand Institute of Chartered Accountants Act 1996",
    "Industry Training Act 1992":
        "informal short form of Industry Training and Apprenticeships Act 1992 (same number, no official previous-title record)",
    "Schedule 8 of the Public Service Act 2020":
        "fragment of Public Service Act 2020",
    "Agriculture and Fisheries (Restructuring) Act 1995":
        "drops 'Ministry of' prefix from Ministry of Agriculture and Fisheries (Restructuring) Act 1995",
    "Regulation 3":
        "fragment (a clause) of Traffic Amendment Regulations (No 3) 2004",
}

assert len(DROP_NAMES) == 25, f"expected 25 drop names, got {len(DROP_NAMES)}"


def remove_from(path, key="act"):
    if not path.exists():
        print(f"{path}: not found, skipped")
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    before = len(data)
    matched = [d.get(key) for d in data if d.get(key) in DROP_NAMES]
    new_data = [d for d in data if d.get(key) not in DROP_NAMES]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print(f"{path}: {before} -> {len(new_data)} ({before - len(new_data)} removed)")
    missing = set(DROP_NAMES) - set(matched)
    if missing:
        print(f"  WARNING -- {len(missing)} drop names not found in this file:")
        for m in missing:
            print(f"    {m!r}")
    return new_data


final_after = remove_from(FINAL_LIST)
remove_from(COMBINED_FINAL_LIST)
identifiers_after = remove_from(IDENTIFIERS)

if final_after is not None:
    print(f"\nSG4 final list now {len(final_after)} entries.")
if identifiers_after is not None:
    n_resolved = sum(1 for d in identifiers_after if d.get("resolved"))
    print(f"SG4 identifiers: {n_resolved}/{len(identifiers_after)} resolved")
