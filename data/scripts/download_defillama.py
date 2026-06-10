"""Download DefiLlama stablecoin supply snapshot.

Public endpoint:
    https://stablecoins.llama.fi/stablecoins?includePrices=true
returns the full list of tracked stablecoins with current supply by chain.

A longer history is available via
    https://stablecoins.llama.fi/stablecoincharts/all
and per-asset via
    https://stablecoins.llama.fi/stablecoin/<id>

This script grabs the full list snapshot and the historical chart for the
top 5 stablecoins by current circulating supply.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

from common import RAW_DIR, append_manifest, ensure_raw_dir, utc_date

SNAPSHOT_URL = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
HISTORY_URL_TPL = "https://stablecoins.llama.fi/stablecoincharts/all"
PER_ASSET_URL_TPL = "https://stablecoins.llama.fi/stablecoin/{id}"
TOP_N = 5


def main() -> int:
    ensure_raw_dir()
    date_tag = utc_date()

    snap = requests.get(SNAPSHOT_URL, timeout=60).json()
    snap_path = RAW_DIR / f"defillama_stablecoins_snapshot_{date_tag}.json"
    snap_path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    append_manifest("DefiLlama stablecoins snapshot", SNAPSHOT_URL, Path(__file__).name, snap_path)

    hist = requests.get(HISTORY_URL_TPL, timeout=60).json()
    hist_path = RAW_DIR / f"defillama_stablecoins_history_all_{date_tag}.json"
    hist_path.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    append_manifest("DefiLlama stablecoins history (all)", HISTORY_URL_TPL, Path(__file__).name, hist_path)

    top_ids = [
        str(x["id"]) for x in sorted(
            snap.get("peggedAssets", []),
            key=lambda x: x.get("circulating", {}).get("peggedUSD", 0),
            reverse=True,
        )[:TOP_N]
    ]
    for pid in top_ids:
        url = PER_ASSET_URL_TPL.format(id=pid)
        data = requests.get(url, timeout=60).json()
        out_path = RAW_DIR / f"defillama_stablecoin_{pid}_{date_tag}.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        append_manifest(f"DefiLlama per-asset id={pid}", url, Path(__file__).name, out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
