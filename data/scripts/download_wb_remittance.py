"""Download World Bank indicators relevant for the cross-border block.

Two endpoints:
    1. Personal remittances received as share of GDP   (BX.TRF.PWKR.DT.GD.ZS)
       Full panel via https://api.worldbank.org/v2/country/all/indicator/<code>?format=json
    2. Remittance Prices Worldwide quarterly Excel dataset.
       The exact URL changes per quarter; the script tries the latest and
       falls back to a manual instruction printed to stdout.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

from common import RAW_DIR, append_manifest, ensure_raw_dir, utc_date

WB_INDICATOR = "BX.TRF.PWKR.DT.GD.ZS"
WB_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/"
    f"{WB_INDICATOR}?format=json&per_page=20000"
)
RPW_URL_CANDIDATES = [
    "https://remittanceprices.worldbank.org/sites/default/files/rpw_dataset_Q1_2026.xlsx",
    "https://remittanceprices.worldbank.org/sites/default/files/rpw_dataset_Q4_2025.xlsx",
    "https://remittanceprices.worldbank.org/sites/default/files/rpw_dataset_Q3_2025.xlsx",
]


def fetch_indicator() -> dict:
    return requests.get(WB_URL, timeout=120).json()


def try_rpw() -> tuple[bytes, str] | None:
    for url in RPW_URL_CANDIDATES:
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and len(r.content) > 1024:
                return r.content, url
        except Exception as exc:
            print(f"  RPW {url} failed: {exc}")
    return None


def main() -> int:
    ensure_raw_dir()
    date_tag = utc_date()

    payload = fetch_indicator()
    ind_path = RAW_DIR / f"wb_remittance_share_gdp_{date_tag}.json"
    ind_path.write_text(json.dumps(payload, ensure_ascii=False))
    append_manifest(
        dataset="World Bank BX.TRF.PWKR.DT.GD.ZS",
        source=WB_URL,
        script=Path(__file__).name,
        output=ind_path,
    )
    print(f"  wrote {ind_path.name}")

    rpw = try_rpw()
    if rpw is None:
        print(
            "RPW dataset auto-download failed; visit "
            "https://remittanceprices.worldbank.org/ to grab the latest manually."
        )
        return 0
    content, url = rpw
    rpw_path = RAW_DIR / f"wb_remittance_prices_{date_tag}.xlsx"
    rpw_path.write_bytes(content)
    append_manifest(
        dataset="World Bank Remittance Prices Worldwide",
        source=url,
        script=Path(__file__).name,
        output=rpw_path,
    )
    print(f"  wrote {rpw_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
