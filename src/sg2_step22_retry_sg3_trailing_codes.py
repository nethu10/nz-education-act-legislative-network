"""
sg2_step22_retry_sg3_trailing_codes.py

Fifth resolution pass, over whatever step21 left unresolved (52/901 after
that pass). Looking at that list, nearly every remaining entry carries a
trailing parenthetical CITATION CODE that pollutes the search query enough
to knock the real result out of the top 5 -- not a URL-pattern gap (that
was step21's fix) and not a genuine miss. Patterns seen:

  'Water Services (Levies on Water Services) Regulations 2025 (SL 2025/89)'
      -- trailing "(SL year/number)" secondary-legislation code
  'Palmerston North Reserves Empowering Act 1966 (1966 No 28 (L))'
      -- trailing "(year No N (L))" local-Act citation
  'Loyal Orange Institution of New Zealand (Incorporated) Trust Act 1954
   (1954 No 3 (P))'
      -- trailing "(year No N (P))" private-Act citation -- note this one
      *also* has a harmless parenthetical ("(Incorporated)") in the middle
      of the real title, which must NOT be touched
  'Support Workers (Pay Equity) Settlements Act 2017 (previously named the
   Care and Support Workers (Pay Equity) Settlement Act 2017)'
      -- trailing "(previously named ...)" explanatory note (itself
      containing a nested parenthetical)
  'Transport (Driving Hours Logbook Exemption) Notice 2003
   ( Gazette 2003 p 2689)'
      -- trailing Gazette citation

Rather than special-case every code type, this pass strips ONE trailing
parenthetical group (allowing one level of nesting, so "(1954 No 3 (P))"
and the nested "(previously named ... (Pay Equity) ...)" case both come
off cleanly) and searches what's left, against step21's corrected
multi-pattern regex. A parenthetical in the MIDDLE of a name (e.g.
"(Incorporated)", "(General)", "(Pay Equity)") is untouched, since the
match is anchored to the end of the string.

Three more targeted patterns, handled before the generic strip:

  1. Land Transport Rules -- reuses step19's prefix/suffix strip (strip
     "Land Transport Rule: " and the trailing numeric code), but this time
     paired with step21's corrected regex. step19 tried this exact
     transformation against the OLD regex and went 0/22 -- worth retrying
     now that the regex itself is fixed.
  2. Fragment citations -- "Part 3 and section 114 of the Legislation Act
     2019" / "Part 2 and sections 25 and 26(1) and (2) of the Contempt of
     Court Act 2019" aren't standalone documents at all; extract the
     Act name after "of the" and search that.
  3. Alternate/bilingual names -- "Te Ture mo Te Reo Maori 2016/the Maori
     Language Act 2016": split on "/", drop a leading "the ", search the
     second name.

Anything left after all of this (expected: "Children's Commissioner Act
2003" per step21's note, and a handful of plain Regulations/Orders with no
parenthetical at all) is a genuine search-ranking miss or a low-value
citation fragment, not a pipeline bug -- final ranked summary as before so
that's a documented, evidence-based decision rather than a guess.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

SG3_PATH = Path("data/processed/sg3_final_list.json")
IDENTIFIERS_PATH = Path("data/processed/sg3_act_identifiers.json")
DELAY_SECONDS = 1.0
MAX_ATTEMPTS = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Same corrected multi-pattern regex from step21 (old /act|.../ scheme plus
# both secondary-legislation schemes).
RESULT_LINK_RE = re.compile(
    r'href="(?P<path>'
    r'/(?P<type1>act|regulation|rule|order|notice)/(?P<status1>public|private|local|imperial)/(?P<year1>\d{4})/(?P<number1>\d+)/en/latest/[^"]*'
    r'|/secondary-legislation/(?P<subtype2>pco-drafted)/(?P<year2>\d{4})/(?P<number2>\d+)/en/latest/[^"]*'
    r'|/secondary-legislation/(?P<subtype3>agency-drafted)/~(?P<year3>\d{4})/~(?P<number3>\d+)/en/latest/[^"]*'
    r')"'
)

LAND_TRANSPORT_RULE_RE = re.compile(
    r"^Land Transport Rule:\s*(.+?)\s*\([0-9/]+\)\s*$", re.IGNORECASE
)
FRAGMENT_CITATION_RE = re.compile(
    r"^(?:Parts?|Sections?|Schedules?)\b.*?\bof the\s+(.+)$", re.IGNORECASE
)
# One trailing "(...)" group, allowing exactly one level of nested parens,
# anchored to the end of the string so a mid-title "(General)"-style
# parenthetical is left untouched.
TRAILING_PAREN_RE = re.compile(r"\s*\((?:[^()]|\([^()]*\))*\)\s*$")


def build_query(name):
    """Return (query, resolved_via) -- the transformed search text and a
    tag recording which rule produced it, or (name, None) if untransformed."""
    m = LAND_TRANSPORT_RULE_RE.match(name)
    if m:
        return m.group(1).strip(), "land_transport_rule_v2"

    m = FRAGMENT_CITATION_RE.match(name)
    if m:
        return m.group(1).strip(), "fragment_citation"

    # Only treat "/" as an alternate-name separator (e.g. "Te Ture mo Te
    # Reo Maori 2016/the Maori Language Act 2016") when it appears BEFORE
    # any parenthetical -- otherwise a trailing code like "(SL 2025/89)"
    # gets mis-split on the slash inside it.
    slash_idx = name.find("/")
    paren_idx = name.find("(")
    if slash_idx != -1 and (paren_idx == -1 or slash_idx < paren_idx):
        _, _, after = name.partition("/")
        after = after.strip()
        if re.match(r"^the\s+", after, re.IGNORECASE):
            after = re.sub(r"^the\s+", "", after, flags=re.IGNORECASE)
        if after:
            return after, "alt_name_after_slash"

    stripped = TRAILING_PAREN_RE.sub("", name).strip()
    if stripped and stripped != name:
        return stripped, "trailing_parenthetical_stripped"

    return name, None


def search(name, timeout=25):
    url = f"https://www.legislation.govt.nz/items/?search_term={quote(name)}&per_page=5"
    return requests.get(url, headers=HEADERS, timeout=timeout)


def parse_first_result(html):
    m = RESULT_LINK_RE.search(html)
    if not m:
        return None
    gd = m.groupdict()
    url = f"https://www.legislation.govt.nz{gd['path']}"

    if gd["year1"]:
        doc_type, status, year, number = gd["type1"], gd["status1"], int(gd["year1"]), gd["number1"]
        return {
            "type": doc_type,
            "status": status,
            "year": year,
            "number": number,
            "url": url,
            "xml_url": f"https://legislation.govt.nz/{doc_type}/{status}/{year}/{number}/en/latest.xml",
        }
    if gd["year2"]:
        year, number = int(gd["year2"]), gd["number2"]
        return {
            "type": "secondary-legislation",
            "subtype": "pco-drafted",
            "status": None,
            "year": year,
            "number": number,
            "url": url,
            "xml_url": f"https://legislation.govt.nz/secondary-legislation/pco-drafted/{year}/{number}/en/latest.xml",
        }
    if gd["year3"]:
        year, number = int(gd["year3"]), gd["number3"]
        return {
            "type": "secondary-legislation",
            "subtype": "agency-drafted",
            "status": None,
            "year": year,
            "number": number,
            "url": url,
            "xml_url": f"https://legislation.govt.nz/secondary-legislation/agency-drafted/~{year}/~{number}/en/latest.xml",
        }
    return None


def search_with_retries(name):
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            r = search(name, timeout=25)
            return parse_first_result(r.text), None
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(2 * attempt)
    return None, last_err


with open(SG3_PATH, encoding="utf-8") as f:
    sg3 = json.load(f)
with open(IDENTIFIERS_PATH, encoding="utf-8") as f:
    identifiers = json.load(f)

by_act = {d["act"]: d for d in identifiers}
unresolved_names = [d["act"] for d in identifiers if not d.get("resolved")]
print(f"Retrying {len(unresolved_names)} still-unresolved SG3 Acts with "
      f"trailing-code stripping...\n")

n_fixed = 0
n_still_unresolved = 0

for i, name in enumerate(unresolved_names, 1):
    query, resolved_via = build_query(name)
    parsed, err = search_with_retries(query)

    entry = by_act[name]
    if parsed:
        entry.update(parsed)
        entry["resolved"] = True
        entry["resolved_via"] = resolved_via or "direct_retry_pass5"
        entry["searched_as"] = query if query != name else None
        n_fixed += 1
        tag = f" (as {resolved_via}, query={query!r})" if resolved_via else ""
        print(f"  [{i}/{len(unresolved_names)}] FIXED: {name!r}{tag} -> "
              f"{parsed['type']}/{parsed.get('subtype', parsed.get('status'))}/{parsed['year']}/{parsed['number']}")
    else:
        entry["resolved"] = False
        if err:
            entry["error"] = err
        n_still_unresolved += 1
        print(f"  [{i}/{len(unresolved_names)}] still unresolved: {name!r}" + (f" [{err}]" if err else ""))

    time.sleep(DELAY_SECONDS)

with open(IDENTIFIERS_PATH, "w", encoding="utf-8") as f:
    json.dump(identifiers, f, indent=2, ensure_ascii=False)

n_total_resolved = sum(1 for d in identifiers if d.get("resolved"))
print(f"\nFixed this pass: {n_fixed}")
print(f"Still unresolved: {n_still_unresolved}")
print(f"Overall: {n_total_resolved}/{len(sg3)} resolved")
print(f"Saved -> {IDENTIFIERS_PATH}")

if n_still_unresolved:
    print("\nStill-unresolved Acts, with their SG3 combined_score:")
    score_by_name = {c["act"]: c["combined_score"] for c in sg3}
    remaining = sorted(
        (d for d in identifiers if not d.get("resolved")),
        key=lambda d: -score_by_name.get(d["act"], 0),
    )
    for d in remaining:
        print(f"  {score_by_name.get(d['act']):>4}  {d['act']!r}")