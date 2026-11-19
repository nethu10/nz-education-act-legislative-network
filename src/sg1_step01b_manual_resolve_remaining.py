"""
sg1_step01b_manual_resolve_remaining.py

sg1_step01_resolve_identifiers.py resolved 22/37 SG1 Acts automatically but
left 15 unresolved -- 14 because its regex only matches legislation.govt.nz's
primary-legislation URL pattern (/act|regulation|rule|order|notice/{status}/
{year}/{number}/en/latest/...) and never matches the site's SEPARATE
/secondary-legislation/pco-drafted/{year}/{number}/... URL scheme that
regulations/rules/orders with SR/LI citations actually live under. This is
the exact same gap sg2_step9c hit for SG2 (42 of its Acts), and sg3/sg4/sg5
hit again (192/375/33) -- in every prior case it was fixed by manual lookup,
tagged resolved_via="manual_lookup", not by patching the regex (sg2_step9d's
own retry pass tried other fixes -- timeouts, schedule-fragment names,
reprint suffixes -- and never added secondary-legislation support either).
This does the same thing for SG1's remaining 15.

14 of the 15 are regulations/rules/orders resolved via the pattern above,
with year/number taken directly from their own SR/LI citation (NZ secondary
legislation citations already ARE "{year}/{number}" -- confirmed against
live legislation.govt.nz pages for every one of them before writing this).

One -- "Education (School Trustee Elections) Regulations 2000" (SR 2000/195)
-- has since been renamed on the site to "Education (Board Elections)
Regulations 2000" and revoked in 2022 (replaced by SL 2022/132). Its
pre-revocation "latest" text is still live at the confirmed URL, which is
enough for this pipeline's purposes (it's being fetched for amendment/
citation tags written while it was still in force).

The 15th, "Children's Act 2014" (2014 No 40), is NOT a secondary-legislation
case at all -- it's an ordinary primary Act that SHOULD have matched the
original regex. legislation.govt.nz's own internal search returned nothing
for it when sg1_step01 queried it (reason unconfirmed -- possibly the
apostrophe). Resolved here by direct lookup instead: act/public/2014/40.

Run from the repo root, AFTER sg1_step01_resolve_identifiers.py:
    python src/sg1_step01b_manual_resolve_remaining.py

Updates data/processed/sg1_act_identifiers.json in place (the 22 already-
resolved entries are left untouched). Then run sg1_step02_find_internal_links.py.
"""
import json
from pathlib import Path

IDENTIFIERS_PATH = Path("data/processed/sg1_act_identifiers.json")

# name (exact "act" string, matching sg1_final_list.json) -> (type, status, year, number)
MANUAL_RESOLUTIONS = {
    "Teaching Council Rules 2016 (LI 2016/122)":
        ("secondary-legislation", "pco-drafted", "2016", "122"),
    "Education (Stand-Down, Suspension, Exclusion, and Expulsion) Rules 1999 (SR 1999/202)":
        ("secondary-legislation", "pco-drafted", "1999", "202"),
    "Social Security Regulations 2018 (LI 2018/202)":
        ("secondary-legislation", "pco-drafted", "2018", "202"),
    "Education (Early Childhood Services) Regulations 2008 (SR 2008/204)":
        ("secondary-legislation", "pco-drafted", "2008", "204"),
    "Education (Surrender, Retention, and Search) Rules 2013 (SR 2013/469)":
        ("secondary-legislation", "pco-drafted", "2013", "469"),
    "Education (School Trustee Elections) Regulations 2000 (SR 2000/195)":
        ("secondary-legislation", "pco-drafted", "2000", "195"),
    "Education (Registration of Early Childhood Services Teachers) Regulations 2004 (SR 2004/236)":
        ("secondary-legislation", "pco-drafted", "2004", "236"),
    "Education (School Risk Management Scheme) Regulations 2003 (SR 2003/39)":
        ("secondary-legislation", "pco-drafted", "2003", "39"),
    "Student Allowances Regulations 1998 (SR 1998/277)":
        ("secondary-legislation", "pco-drafted", "1998", "277"),
    "Education (Hostels) Regulations 2005 (SR 2005/332)":
        ("secondary-legislation", "pco-drafted", "2005", "332"),
    "Education (2020 School Staffing) Order 2019 (LI 2019/180)":
        ("secondary-legislation", "pco-drafted", "2019", "180"),
    "International Student Contract Dispute Resolution Scheme Rules 2016 (LI 2016/42)":
        ("secondary-legislation", "pco-drafted", "2016", "42"),
    "Education (Playgroups) Regulations 2008 (SR 2008/205)":
        ("secondary-legislation", "pco-drafted", "2008", "205"),
    "Teaching Council of Aotearoa New Zealand Election Rules 2018 (LI 2018/234)":
        ("secondary-legislation", "pco-drafted", "2018", "234"),
    # curly apostrophe -- must match exactly as stored in sg1_final_list.json
    "Children\u2019s Act 2014 (2014 No 40)":
        ("act", "public", 2014, "40"),
}

NOTES = {
    "Education (School Trustee Elections) Regulations 2000 (SR 2000/195)":
        "Renamed on site to 'Education (Board Elections) Regulations 2000'; "
        "revoked 2022, replaced by SL 2022/132. Resolving to pre-revocation "
        "latest text, which is what was in force when SG1's citing Acts "
        "referenced it.",
    "Children\u2019s Act 2014 (2014 No 40)":
        "Ordinary primary Act -- unresolved by sg1_step01 for an unrelated "
        "reason (site search returned nothing), not the secondary-legislation "
        "URL gap. Resolved by direct lookup.",
}


def build_entry(act_name, type_, status, year, number):
    if type_ == "secondary-legislation":
        url = f"https://legislation.govt.nz/secondary-legislation/{status}/{year}/{number}/en/latest/"
    else:
        url = f"https://www.legislation.govt.nz/{type_}/{status}/{year}/{number}/en/latest/"
    xml_url = url.rstrip("/") + ".xml" if url.endswith("latest/") else url + ".xml"
    # (both branches above end in ".../en/latest/", so this always yields ".../en/latest.xml")
    xml_url = url[:-1] + ".xml"

    entry = {
        "act": act_name,
        "resolved": True,
        "type": type_,
        "status": status,
        "year": year,
        "number": number,
        "url": url,
        "xml_url": xml_url,
        "resolved_via": "manual_lookup",
    }
    if act_name in NOTES:
        entry["note"] = NOTES[act_name]
    return entry


def main():
    with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
        identifiers = json.load(f)

    by_act = {d["act"]: d for d in identifiers}
    n_patched = 0
    n_not_found = 0

    for act_name, (type_, status, year, number) in MANUAL_RESOLUTIONS.items():
        if act_name not in by_act:
            print(f"  !! NOT FOUND in {IDENTIFIERS_PATH}: {act_name!r}")
            print("     Check for an exact-string mismatch (e.g. apostrophe style) "
                  "against sg1_final_list.json before re-running.")
            n_not_found += 1
            continue
        idx = identifiers.index(by_act[act_name])
        identifiers[idx] = build_entry(act_name, type_, status, year, number)
        print(f"  [OK] {act_name!r} -> {type_}/{status}/{year}/{number}")
        n_patched += 1

    with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
        json.dump(identifiers, f, indent=2, ensure_ascii=False)

    n_resolved = sum(1 for d in identifiers if d.get("resolved"))
    print(f"\nPatched {n_patched} entries ({n_not_found} not found -- check manually if > 0).")
    print(f"Overall: {n_resolved}/{len(identifiers)} resolved.")
    print(f"Saved -> {IDENTIFIERS_PATH}")
    print("\nNext: python src/sg1_step02_find_internal_links.py")


if __name__ == "__main__":
    main()