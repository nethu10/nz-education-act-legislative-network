"""
audit_fix_09_sg4_resolve_unresolved_identifiers.py

Resolves 39 of the 40 previously unresolved SG4 identifiers in
data/processed/sg4_act_identifiers.json. Each was found manually and verified
live on legislation.govt.nz (page title / parent-regulation version history /
source-XML citation), and collision-checked on (year, number).

Left unresolved on purpose: "Mental Health Act 1969" (cited 1969 No 16 in
source XML) -- no page exists on the live site (404 in every URL form).
Reported as an irrecoverable case in the thesis limitations.

Matching is on the NBSP-normalised act name. Re-running is a no-op error.
"""
import json
from pathlib import Path

P = Path("data/processed/sg4_act_identifiers.json")
# name -> (kind, year, number); kind: sr (pco-drafted), pub, local
R = {
"Securities Amendment Regulations (No 2) 2014 (LI 2014/339).": ("sr",2014,339),
"War Pensions Regulations 1956, Amendment No 29": ("sr",1989,99),
"Government Superannuation Fund Amendment Act 1959": ("pub",1959,85),
"Maori Land Act 1931": ("pub",1931,31),
"Ombudsmen (Schedule 1) Order 2002": ("sr",2002,385),
"Freshwater Fisheries Regulations 1983, Amendment No 9": ("sr",1990,209),
"Securities Trustees and Statutory Supervisors Act 2011": ("pub",2011,10),
"Building Regulations 1992, Amendment No 1": ("sr",1994,263),
"Land Act Regulations 1949, Amendment No 6": ("sr",1974,283),
"Health Reforms (Transitional Provisions) Act 1993": ("pub",1993,23),
"Wellington Regional Water Board Amendment Act 1976": ("local",1976,11),
"Patents Regulations 1954, Amendment No 3": ("sr",1975,58),
"War Pensions Amendment Regulations 2000": ("sr",2000,45),
"Fisheries (Challenger Area Commercial Fishing) Regulations 1986, Amendment No 14": ("sr",1993,281),
"Government Superannuation Fund Amendment Act 1960": ("pub",1960,90),
"Building Amendment Regulations 2000": ("sr",2000,119),
"Fisheries (Challenger Area Commercial Fishing) Regulations 1986, Amendment No 15": ("sr",1993,352),
"Rock Oyster Farming Regulations 1964, Amendment No 2": ("sr",1975,192),
"Takeovers Code Approval Order 2000 (SR 2000/210)": ("sr",2000,210),
"Geographical Indications (Wine and Spirits) Registration Act 2006": ("pub",2006,60),
"War Pensions Regulations 1956, Amendment No 7": ("sr",1966,135),
"Wildlife Regulations 1955, Amendment No 5": ("sr",1971,270),
"Heavy Motor Vehicle Regulations 1974, Amendment No 8": ("sr",1992,182),
"Port Companies Amendment Act 1990": ("pub",1990,120),
"Tokelau (Exclusive Economic Zone) Fishing Regulations 1988, Amendment No 1": ("sr",1989,268),
"War Pensions Regulations 1956, Amendment No 12": ("sr",1971,81),
"Government Superannuation Fund Amendment Act 1967": ("pub",1967,141),
"Queen Elizabeth the Second National Trust Amendment Act 1987": ("pub",1988,208),
"Maori Community Development Amendment Act 1963": ("pub",1963,53),
"Married Women's Property Act 1952": ("pub",1952,53),
"United Nations Sanctions (Côte d'Ivoire) Amendment Regulations 2008": ("sr",2008,389),
"Government Superannuation Fund Amendment Act 1963": ("pub",1963,126),
"Wellington Regional Water Board Amendment Act 1983": ("local",1983,11),
"Income Tax (Witholding Payments) Regulations 1979, Amendment No 11": ("sr",1996,378),
"War Pensions Regulations 1956, Amendment No 8": ("sr",1967,66),
"Road User Charges Regulations 1978, Amendment No 8": ("sr",1993,71),
"Government Superannuation Fund Amendment Act 1964": ("pub",1964,125),
"Freshwater Fisheries Regulations 1983, Amendment No 14": ("sr",1993,153),
"Fisheries (Southland and Sub-Antarctic Areas Commercial Fishing) Regulations 1986, Amendment No 12": ("sr",1992,86),
}
norm = lambda s: s.replace("\xa0", " ").replace("’", "'").strip()
R = {norm(k): v for k, v in R.items()}
data = json.load(open(P, encoding="utf-8"))
used = {(d["year"], str(d["number"]), d.get("type"), d.get("status")) for d in data if d.get("resolved")}
done = 0
for d in data:
    if d.get("resolved") or norm(d["act"]) not in R:
        continue
    kind, y, n = R[norm(d["act"])]
    if kind == "sr":
        path, extra = f"secondary-legislation/pco-drafted/{y}/{n}", {"type": "secondary-legislation", "subtype": "pco-drafted", "status": None}
    else:
        st = "public" if kind == "pub" else "local"
        path, extra = f"act/{st}/{y}/{n}", {"type": "act", "status": st}
    key = (y, str(n), extra["type"], extra["status"])
    assert key not in used, f"collision {key} for {d['act']!r}"
    used.add(key)
    d.update({"resolved": True, **extra, "year": y, "number": str(n),
              "url": f"https://www.legislation.govt.nz/{path}/en/latest/",
              "xml_url": f"https://legislation.govt.nz/{path}/en/latest.xml",
              "resolved_via": "audit_fix_09_manual_verified", "searched_as": None})
    done += 1
assert done == 39, f"expected 39, resolved {done}"
json.dump(data, open(P, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"resolved {done}; still unresolved: {[d['act'] for d in data if not d.get('resolved')]}")
