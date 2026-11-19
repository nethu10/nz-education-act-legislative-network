"""
sg2_step9b_probe_site.py

Step 9's blind URL guesses all hit the same generic 404 page, so instead
of guessing further, read the site itself for the real structure:

  1. Fetch the legislation.govt.nz homepage and pull out any <form> tag
     (action + method + input names) -- that's the actual search
     endpoint and parameter name, straight from the source.
  2. Check robots.txt and a couple of likely sitemap paths. If there's a
     real sitemap, it may let us resolve all 437 Acts by matching titles
     against a bulk URL list instead of doing 437 individual searches.

Run this, paste the full output back.
"""
import re
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

FORM_RE = re.compile(r"<form\b[^>]*>.*?</form>", re.IGNORECASE | re.DOTALL)
INPUT_RE = re.compile(r'<input\b[^>]*name="([^"]+)"[^>]*>', re.IGNORECASE)
ACTION_RE = re.compile(r'action="([^"]*)"', re.IGNORECASE)
METHOD_RE = re.compile(r'method="([^"]*)"', re.IGNORECASE)

print("=" * 70)
print("1. Homepage search form(s)")
print("=" * 70)
try:
    r = requests.get("https://www.legislation.govt.nz/", headers=HEADERS, timeout=20)
    print(f"GET / -> status {r.status_code}, {len(r.text)} chars")
    forms = FORM_RE.findall(r.text)
    print(f"Found {len(forms)} <form> tag(s)\n")
    for i, form in enumerate(forms):
        action = ACTION_RE.search(form)
        method = METHOD_RE.search(form)
        inputs = INPUT_RE.findall(form)
        print(f"--- form {i} ---")
        print(f"  action: {action.group(1) if action else None}")
        print(f"  method: {method.group(1) if method else None}")
        print(f"  input names: {inputs}")
        # print a trimmed snippet too in case regexes above miss something
        snippet = re.sub(r"\s+", " ", form)[:500]
        print(f"  raw snippet: {snippet}")
        print()
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("=" * 70)
print("2. robots.txt and sitemap candidates")
print("=" * 70)
for path in ["/robots.txt", "/sitemap.xml", "/sitemap_index.xml", "/sitemapindex.xml"]:
    url = f"https://www.legislation.govt.nz{path}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"GET {path} -> status {r.status_code}, {len(r.text)} chars")
        if r.status_code == 200:
            print(re.sub(r"\s+", " ", r.text)[:800])
        print()
    except Exception as e:
        print(f"GET {path} -> ERROR {type(e).__name__}: {e}\n")