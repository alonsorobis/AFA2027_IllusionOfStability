"""Download CryptoCompare aggregated USDC-USD candles.

Used because Coinbase Advanced Trade no longer lists USDC-USD as a direct
pair (USDC is treated as ~USD natively on Coinbase). CryptoCompare is the
same source used in Ahmed, Aldasoro and Duley (2024, BIS WP 1164, Figure 1)
for their minute-frequency USDC peg illustration, so the lineage of this
data choice is directly defensible in the literature review.

API:
    GET https://min-api.cryptocompare.com/data/v2/histohour
        ?fsym=USDC&tsym=USD&limit=<<=2000>>&toTs=<unix_seconds>
Returns up to 2000 candles strictly <= toTs. Chunk backwards.

We default to USDC and USDT (both are useful as cross-checks of Coinbase).
DAI is also fetched as a cross-check. Outputs go to data/raw/.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from common import RAW_DIR, append_manifest, ensure_raw_dir, utc_date

CC_URL = "https://min-api.cryptocompare.com/data/v2/histohour"
DEFAULT_FSYMS = ("USDC", "USDT", "DAI")
MAX_LIMIT = 2000
TSYM = "USD"


def fetch_chunk(fsym: str, to_ts: int, limit: int = MAX_LIMIT) -> pd.DataFrame:
    params = {"fsym": fsym, "tsym": TSYM, "limit": limit, "toTs": to_ts}
    r = requests.get(CC_URL, params=params, timeout=30, headers={"User-Agent": "afa2027/0.1"})
    r.raise_for_status()
    payload = r.json()
    if payload.get("Response") != "Success":
        raise RuntimeError(f"CryptoCompare error: {payload.get('Message')}")
    rows = payload.get("Data", {}).get("Data", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for col in ("open", "high", "low", "close", "volumefrom", "volumeto"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    keep = [c for c in ("time", "open", "high", "low", "close", "volumefrom", "volumeto") if c in df]
    return df[keep].sort_values("time").reset_index(drop=True)


def fetch_full_range(fsym: str, start: datetime, end: datetime) -> pd.DataFrame:
    cursor_ts = int(end.timestamp())
    start_ts = int(start.timestamp())
    out = []
    while True:
        df = fetch_chunk(fsym, cursor_ts, MAX_LIMIT)
        if df.empty:
            break
        first_ts = int(df["time"].min().timestamp())
        out.append(df)
        if first_ts <= start_ts:
            break
        cursor_ts = first_ts - 3600     # step back one hour to avoid the overlap
        time.sleep(0.3)                 # CryptoCompare free tier rate limit
    if not out:
        return pd.DataFrame()
    full = pd.concat(out, ignore_index=True).drop_duplicates(subset="time").sort_values("time")
    return full[(full["time"] >= start) & (full["time"] <= end)].reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="CryptoCompare USDC-USD (and others) downloader")
    parser.add_argument("--start", default="2022-01-01T00:00:00")
    parser.add_argument("--end", default="2026-05-31T23:59:59")
    parser.add_argument("--fsyms", nargs="+", default=list(DEFAULT_FSYMS))
    args = parser.parse_args()

    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)

    ensure_raw_dir()
    date_tag = utc_date()
    for fsym in args.fsyms:
        print(f"Fetching CryptoCompare {fsym}-USD hourly, {start} -> {end} ...")
        df = fetch_full_range(fsym, start, end)
        if df.empty:
            print(f"  WARNING: no rows for {fsym}-USD")
            continue
        out_path = RAW_DIR / f"cryptocompare_{fsym.lower()}_usd_3600s_{date_tag}.parquet"
        df.to_parquet(out_path, index=False)
        print(f"  wrote {out_path.name} ({len(df)} rows, {df['time'].min()} -> {df['time'].max()})")
        append_manifest(
            dataset=f"CryptoCompare {fsym}-USD hourly",
            source=f"{CC_URL}?fsym={fsym}&tsym={TSYM}",
            script=Path(__file__).name,
            output=out_path,
            note=f"window {start.isoformat()} to {end.isoformat()}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
