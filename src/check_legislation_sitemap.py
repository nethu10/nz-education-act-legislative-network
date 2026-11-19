"""
Check whether legislation.govt.nz's sitemap.xml is reachable via the
same requests.get() + custom User-Agent approach that successfully
fetched all 37 SG1 Act XML files (sg2_step1_fetch_targets.py) -- and if
so, whether it actually enumerates individual Acts with year/number in
their URLs. If it does, we can resolve all 437 SG2 Act names to
citation numbers from one file instead of ~437 individual lookups.
"""
import requests

url = "https://www.legislation.govt.nz/sitemap.xml"
headers = {"User-Agent": "Nethmi-Unitec-Thesis-Research/1.0"}

response = requests.get(url, headers=headers, timeout=30)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print(f"Length: {len(response.text):,} chars")
print()
print("First 3000 chars:")
print(response.text[:3000])