"""Fetch on-chain mint/burn (primary issuance/redemption) for USDC and USDT on
Ethereum around the two stress windows, as an hourly redemption-pressure proxy.

Mint  = ERC-20 Transfer with from = 0x0 (issuer creates units).
Burn  = ERC-20 Transfer with to   = 0x0 (issuer redeems/destroys units).
Net redemption per hour = burns - mints (supply contraction).

The Etherscan API key is read from the environment (ETHERSCAN_API_KEY); it is
never written to disk. Output (aggregated flows only, no key):
    data/processed/onchain_redemptions_<token>_<window>.csv
    data/processed/onchain_redemptions_summary.json
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROC = Path(__file__).resolve().parents[2] / "data" / "processed"
KEY = os.environ.get("ETHERSCAN_API_KEY")
assert KEY, "set ETHERSCAN_API_KEY in the environment"

BASE = "https://api.etherscan.io/v2/api"
CHAIN = 1
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x" + "0" * 64
TOKENS = {
    "USDC": {"addr": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "dec": 6},
    "USDT": {"addr": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "dec": 6},
}
WINDOWS = {  # (start_ts, end_ts) UTC
    "USDC_SVB":   (1678233600, 1679097600),   # 2023-03-08 .. 2023-03-18
    "USDT_Terra": (1651363200, 1653523200),   # 2022-05-01 .. 2022-05-26
}


def call(params):
    params = {**params, "chainid": CHAIN, "apikey": KEY}
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                j = json.loads(r.read())
            if j.get("message") == "NOTOK" and "rate limit" in str(j.get("result", "")).lower():
                time.sleep(1.0); continue
            return j
        except Exception as e:
            time.sleep(1.0)
            if attempt == 4:
                raise
    return {}


def block_at(ts, closest):
    j = call({"module": "block", "action": "getblocknobytime", "timestamp": ts, "closest": closest})
    return int(j["result"])


def get_logs(addr, fb, tb, topic_zero_pos):
    """topic_zero_pos = 1 (mint, from=0) or 2 (burn, to=0)."""
    out = []
    page = 1
    while True:
        p = {"module": "logs", "action": "getLogs", "address": addr,
             "fromBlock": fb, "toBlock": tb, "topic0": TRANSFER,
             f"topic{topic_zero_pos}": ZERO, f"topic0_{topic_zero_pos}_opr": "and",
             "page": page, "offset": 1000}
        j = call(p)
        res = j.get("result", [])
        if not isinstance(res, list) or not res:
            break
        out.extend(res)
        if len(res) < 1000:
            break
        page += 1
        time.sleep(0.25)
    return out


def main():
    summary = {}
    for win, (t0, t1) in WINDOWS.items():
        token = win.split("_")[0]
        addr, dec = TOKENS[token]["addr"], TOKENS[token]["dec"]
        fb, tb = block_at(t0, "after"), block_at(t1, "before")
        mints = get_logs(addr, fb, tb, 1)
        burns = get_logs(addr, fb, tb, 2)

        def rows(logs):
            r = []
            for e in logs:
                val = int(e["data"], 16) / (10 ** dec)
                ts = int(e["timeStamp"], 16)
                r.append((ts // 3600 * 3600, val))
            return r

        mrows, brows = rows(mints), rows(burns)
        import collections
        hourly = collections.defaultdict(lambda: [0.0, 0.0])  # hour -> [mint, burn]
        for h, v in mrows: hourly[h][0] += v
        for h, v in brows: hourly[h][1] += v
        # write hourly csv
        path = PROC / f"onchain_redemptions_{win}.csv"
        with path.open("w", encoding="utf-8") as f:
            f.write("hour_ts,mint,burn,net_redemption\n")
            for h in sorted(hourly):
                m, b = hourly[h]
                f.write(f"{h},{m:.2f},{b:.2f},{b-m:.2f}\n")
        tot_mint = sum(v for _, v in mrows)
        tot_burn = sum(v for _, v in brows)
        summary[win] = {
            "token": token, "blocks": [fb, tb],
            "n_mint_events": len(mints), "n_burn_events": len(burns),
            "total_mint_usd": round(tot_mint, 0), "total_burn_usd": round(tot_burn, 0),
            "net_redemption_usd": round(tot_burn - tot_mint, 0),
            "hours_with_activity": len(hourly), "csv": path.name,
        }
        print(win, summary[win])
    (PROC / "onchain_redemptions_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nwrote summary")


if __name__ == "__main__":
    main()
