"""Fetch USDT mint/burn on Tron around the May 2022 Terra window (Tronscan API).

TRC-20 mints/burns appear as transfers involving the zero address
(T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb): mint = from zero, burn = to zero. We pull
all such USDT transfers in the window, classify, and aggregate to hourly net
redemption (burn - mint). The Tronscan key is read from the environment
(TRONSCAN_API_KEY) and never written to disk.

Output: data/processed/tron_redemptions_USDT_Terra.csv, ..._summary.json
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

PROC = Path(__file__).resolve().parents[2] / "data" / "processed"
KEY = os.environ.get("TRONSCAN_API_KEY")
assert KEY, "set TRONSCAN_API_KEY"

USDT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
ZERO = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
T0, T1 = 1651363200000, 1653523200000   # 2022-05-01 .. 2022-05-26 (ms)
BASE = "https://apilist.tronscanapi.com/api/token_trc20/transfers"


def get(start, limit=50):
    url = (f"{BASE}?contract_address={USDT}&relatedAddress={ZERO}"
           f"&start_timestamp={T0}&end_timestamp={T1}&limit={limit}&start={start}")
    req = urllib.request.Request(url, headers={"TRON-PRO-API-KEY": KEY, "User-Agent": "Mozilla/5.0"})
    for _ in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(1.0)
    raise RuntimeError("tronscan call failed")


def main():
    import collections
    hourly = collections.defaultdict(lambda: [0.0, 0.0])   # hour -> [mint, burn]
    start, limit, seen = 0, 50, 0
    rangetotal = None
    while True:
        j = get(start, limit)
        if rangetotal is None:
            rangetotal = j.get("rangeTotal", j.get("total"))
        batch = j.get("token_transfers", []) or []
        if not batch:
            break
        for e in batch:
            amt = int(e["quant"]) / 1e6
            h = (int(e["block_ts"]) // 1000) // 3600 * 3600
            if e["from_address"] == ZERO:
                hourly[h][0] += amt          # mint
            elif e["to_address"] == ZERO:
                hourly[h][1] += amt          # burn
        seen += len(batch)
        start += limit
        if len(batch) < limit or seen >= (rangetotal or 0) or seen >= 5000:
            break
        time.sleep(0.3)

    path = PROC / "tron_redemptions_USDT_Terra.csv"
    tot_m = tot_b = 0.0
    with path.open("w", encoding="utf-8") as f:
        f.write("hour_ts,mint,burn,net_redemption\n")
        for h in sorted(hourly):
            m, b = hourly[h]; tot_m += m; tot_b += b
            f.write(f"{h},{m:.2f},{b:.2f},{b-m:.2f}\n")
    summary = {"token": "USDT", "chain": "Tron", "window": "2022-05-01..2022-05-26",
               "events_seen": seen, "rangeTotal": rangetotal,
               "total_mint_usd": round(tot_m, 0), "total_burn_usd": round(tot_b, 0),
               "net_redemption_usd": round(tot_b - tot_m, 0),
               "hours_with_activity": len(hourly)}
    (PROC / "tron_redemptions_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
