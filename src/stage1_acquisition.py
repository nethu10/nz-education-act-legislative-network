"""
Stage 1: Data source and scoping.
Fetches the XML for the Education and Training Act 2020 (the seed Act)
from the official New Zealand Legislation website.
"""

import requests
from pathlib import Path

ACT_YEAR = 2020
ACT_NUMBER = "38"
VERSION_DATE = "2026-07-01"  # pinned, not "latest" — reproducibility for the thesis

RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_act_xml(year: int, number: str) -> str:
    url = f"https://legislation.govt.nz/act/public/{ACT_YEAR}/{ACT_NUMBER}/en/{VERSION_DATE}.xml"
    headers = {"User-Agent": "Nethmi-Unitec-Thesis-Research/1.0"}

    response = requests.get(url, headers=headers, timeout=30)
    print(f"Requested {url} -> status {response.status_code}")

    if response.status_code == 200 and response.text.strip().startswith("<?xml"):
        return response.text

    raise RuntimeError(
        f"Unexpected response (status {response.status_code}). "
        "First 200 characters of response:\n" + response.text[:200]
    )


def save_xml(xml_text: str, filename: str) -> Path:
    out_path = RAW_DATA_DIR / filename
    out_path.write_text(xml_text, encoding="utf-8")
    print(f"Saved to {out_path} ({len(xml_text):,} characters)")
    return out_path


if __name__ == "__main__":
    xml_content = fetch_act_xml(ACT_YEAR, ACT_NUMBER)
    save_xml(xml_content, "education_and_training_act_2020.xml")