"""Cross-section of fiat-backed stablecoin depegs in the two systemic episodes,
for the descriptive panel that documents the heterogeneity beyond the two
calibrated coins. Hourly close from CryptoCompare / CoinDesk Data (key from env,
never written to disk). Output: data/processed/cross_section_depeg.json
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROC = Path(__file__).resolve().parents[2] / "data" / "processed"
KEY = os.environ.get("CRYPTOCOMPARE_API_KEY")
assert KEY, "set CRYPTOCOMPARE_API_KEY"

COINS = ["USDC", "USDT", "DAI", "BUSD", "TUSD", "USDP", "GUSD", "FRAX"]
WINDOWS = {"SVB_Mar2023": (1679097600, 240), "Terra_May2022": (1653523200, 600)}


def histo(sym, to_ts, limit):
    url = (f"https://min-api.cryptocompare.com/data/v2/histohour"
           f"?fsym={sym}&tsym=USD&limit={limit}&toTs={to_ts}")
    req = urllib.request.Request(url, headers={"authorization": f"Apikey {KEY}",
                                               "User-Agent": "afa2027/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    out = {}
    for sym in COINS:
        out[sym] = {}
        for win, (to_ts, limit) in WINDOWS.items():
            try:
                j = histo(sym, to_ts, limit)
                if j.get("Response") != "Success":
                    out[sym][win] = {"error": j.get("Message", "no success")[:80]}
                    continue
                d = [x for x in j["Data"]["Data"] if x["close"] > 0]
                lows = [x["low"] for x in d if x["low"] > 0]
                mins = min(d, key=lambda x: x["close"])
                out[sym][win] = {
                    "n_hours": len(d),
                    "min_close": round(mins["close"], 4),
                    "min_low": round(min(lows), 4) if lows else None,
                    "trough_date": datetime.fromtimestamp(mins["time"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
                    "max_depeg_bps": round((1 - mins["close"]) * 1e4),
                    "mean_close": round(sum(x["close"] for x in d) / len(d), 5),
                }
            except Exception as e:
                out[sym][win] = {"error": f"{type(e).__name__}: {str(e)[:60]}"}
            time.sleep(0.3)
    (PROC / "cross_section_depeg.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    # console summary
    print(f"{'coin':6s} {'SVB trough':>11s} {'SVB depeg bps':>13s} {'Terra trough':>13s} {'Terra depeg bps':>15s}")
    for s in COINS:
        sv = out[s].get("SVB_Mar2023", {}); te = out[s].get("Terra_May2022", {})
        print(f"{s:6s} {sv.get('min_close','--'):>11} {sv.get('max_depeg_bps','--'):>13} "
              f"{te.get('min_close','--'):>13} {te.get('max_depeg_bps','--'):>15}")


if __name__ == "__main__":
    main()
