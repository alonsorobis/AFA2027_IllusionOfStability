"""Download macro controls from FRED.

Requires FRED_API_KEY in the environment. Falls back to ALFRED CSV mirror
when the key is missing, so the script is still usable without auth.

Default series:
    DGS10           10-year Treasury constant maturity
    T10Y2Y          10Y-2Y term premium
    BAMLH0A0HYM2    US high-yield OAS
    DCOILWTICO      WTI oil
    DTWEXBGS        Trade-weighted broad dollar
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import requests

from common import RAW_DIR, append_manifest, ensure_raw_dir, utc_date

SERIES = ("DGS10", "T10Y2Y", "BAMLH0A0HYM2", "DCOILWTICO", "DTWEXBGS")
API_URL = "https://api.stlouisfed.org/fred/series/observations"
CSV_MIRROR = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"


def fetch_via_api(series: str, api_key: str) -> pd.DataFrame:
    params = {"series_id": series, "api_key": api_key, "file_type": "json"}
    r = requests.get(API_URL, params=params, timeout=60)
    r.raise_for_status()
    rows = r.json().get("observations", [])
    df = pd.DataFrame(rows)[["date", "value"]]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_via_csv(series: str) -> pd.DataFrame:
    url = CSV_MIRROR.format(series=series)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def main() -> int:
    ensure_raw_dir()
    date_tag = utc_date()
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    for series in SERIES:
        try:
            if api_key:
                df = fetch_via_api(series, api_key)
                source = API_URL + f"?series_id={series}"
            else:
                df = fetch_via_csv(series)
                source = CSV_MIRROR.format(series=series)
        except Exception as exc:
            print(f"WARNING: failed to fetch {series}: {exc}")
            continue
        out_path = RAW_DIR / f"fred_{series}_{date_tag}.parquet"
        df.to_parquet(out_path, index=False)
        append_manifest(
            dataset=f"FRED {series}",
            source=source,
            script=Path(__file__).name,
            output=out_path,
            note=f"{len(df)} obs",
        )
        print(f"  wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
