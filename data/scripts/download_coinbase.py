"""Download Coinbase Advanced Trade candles for USDC, USDT and DAI vs USD.

The legacy Coinbase Exchange public REST endpoint
    https://api.exchange.coinbase.com/products/<P>/candles
was retired and now returns 404. This script pivots to the Advanced Trade
public market endpoint:
    GET https://api.coinbase.com/api/v3/brokerage/market/products/{product_id}/candles
        ?start=<unix_seconds>&end=<unix_seconds>&granularity=<ENUM>

The Advanced Trade endpoint is unauthenticated for the `/market/` subtree.
Granularity is an enum string. Max 300 candles per request. We chunk and
emit one parquet per product.

Outputs go to `data/raw/`. Each successful product write appends a row to
`data/download_log.md`.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

from common import RAW_DIR, append_manifest, ensure_raw_dir, utc_date

COINBASE_URL = "https://api.coinbase.com/api/v3/brokerage/market/products/{product}/candles"
# NOTE 2026-06-01: Coinbase Advanced Trade no longer lists USDC-USD as a
# tradeable pair (Coinbase treats USDC as ~ USD natively after their wallet
# / payments integration). USDC-USD is sourced from CryptoCompare instead,
# via `download_cryptocompare.py`. This matches the data lineage of
# Ahmed-Aldasoro-Duley (2024, BIS WP 1164, Figure 1 source). USDT-USD and
# DAI-USD remain on Coinbase as direct pairs.
PRODUCTS = ("USDT-USD", "DAI-USD")

# (granularity_enum, seconds_per_candle); 1h is the working default.
GRANULARITIES = {
    "ONE_MINUTE": 60,
    "FIVE_MINUTE": 300,
    "FIFTEEN_MINUTE": 900,
    "THIRTY_MINUTE": 1800,
    "ONE_HOUR": 3600,
    "TWO_HOUR": 7200,
    "SIX_HOUR": 21600,
    "ONE_DAY": 86400,
}
DEFAULT_GRANULARITY_ENUM = "ONE_HOUR"
MAX_CANDLES_PER_REQUEST = 300


def fetch_window(product: str, start: datetime, end: datetime, granularity_enum: str) -> pd.DataFrame:
    params = {
        "start": str(int(start.timestamp())),
        "end": str(int(end.timestamp())),
        "granularity": granularity_enum,
    }
    r = requests.get(COINBASE_URL.format(product=product), params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()
    candles = payload.get("candles", [])
    if not candles:
        return pd.DataFrame(columns=["time", "low", "high", "open", "close", "volume"])
    df = pd.DataFrame(candles)
    df["time"] = pd.to_datetime(df["start"].astype(int), unit="s", utc=True)
    for col in ("low", "high", "open", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[["time", "low", "high", "open", "close", "volume"]].sort_values("time").reset_index(drop=True)


def fetch_full_range(product: str, start: datetime, end: datetime, granularity_enum: str) -> pd.DataFrame:
    seconds = GRANULARITIES[granularity_enum]
    chunk = timedelta(seconds=seconds * (MAX_CANDLES_PER_REQUEST - 1))
    out = []
    cursor = start
    while cursor < end:
        window_end = min(cursor + chunk, end)
        try:
            df = fetch_window(product, cursor, window_end, granularity_enum)
        except requests.HTTPError as exc:
            print(f"  HTTP error on window {cursor.isoformat()} -> {window_end.isoformat()}: {exc}")
            cursor = window_end
            time.sleep(1.0)
            continue
        out.append(df)
        cursor = window_end
        time.sleep(0.2)   # be polite
    if not out:
        return pd.DataFrame()
    return pd.concat(out, ignore_index=True).drop_duplicates(subset="time")


def main() -> int:
    parser = argparse.ArgumentParser(description="Coinbase Advanced Trade candles downloader")
    parser.add_argument("--start", default="2022-01-01T00:00:00")
    parser.add_argument("--end", default="2026-05-31T23:59:59")
    parser.add_argument("--granularity", default=DEFAULT_GRANULARITY_ENUM, choices=list(GRANULARITIES))
    parser.add_argument("--products", nargs="+", default=list(PRODUCTS))
    args = parser.parse_args()

    if args.granularity not in GRANULARITIES:
        raise SystemExit(f"unknown granularity {args.granularity!r}; pick one of {list(GRANULARITIES)}")

    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    seconds = GRANULARITIES[args.granularity]

    ensure_raw_dir()
    date_tag = utc_date()
    for product in args.products:
        print(f"Fetching {product} {args.granularity} candles, {start} -> {end} ...")
        df = fetch_full_range(product, start, end, args.granularity)
        if df.empty:
            print(f"  WARNING: no rows for {product}")
            continue
        out_path = RAW_DIR / f"coinbase_adv_{product.lower().replace('-', '_')}_{seconds}s_{date_tag}.parquet"
        df.to_parquet(out_path, index=False)
        print(f"  wrote {out_path.name} ({len(df)} rows, {df['time'].min()} -> {df['time'].max()})")
        append_manifest(
            dataset=f"Coinbase Advanced Trade {product} candles ({args.granularity})",
            source=COINBASE_URL.format(product=product),
            script=Path(__file__).name,
            output=out_path,
            note=f"window {start.isoformat()} to {end.isoformat()}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
