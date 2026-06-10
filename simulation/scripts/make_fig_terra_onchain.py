"""Twin of the SVB figure for USDT during the May 2022 Terra episode.

Contrast with USDC/SVB: Tether's primary redemption stayed open, so Tron USDT
supply contracted by ~$8bn (redemptions honoured at par) and the secondary
depeg was mild and brief. Redemption series = daily contraction of USDT's Tron
circulating supply (DefiLlama, the complete measure; on-chain zero-address
mint/burn via Tronscan undercounts it). Price = hourly USDT (CryptoCompare).

Output: data/processed/tron_usdt_supply_daily.csv, paper/figures/fig_terra_onchain.pdf
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "data" / "raw"
PROC = ROOT.parent / "data" / "processed"
LO, HI = pd.Timestamp("2022-05-03", tz="UTC"), pd.Timestamp("2022-05-26", tz="UTC")

# --- DefiLlama Tron USDT daily circulating -> daily net redemption ---
req = urllib.request.Request("https://stablecoins.llama.fi/stablecoin/1", headers={"User-Agent": "Mozilla/5.0"})
j = json.loads(urllib.request.urlopen(req, timeout=30).read())
tron = j["chainBalances"]["Tron"]["tokens"]
sup = pd.DataFrame({"date": [pd.to_datetime(p["date"], unit="s", utc=True) for p in tron],
                    "circ": [p["circulating"]["peggedUSD"] for p in tron]}).sort_values("date")
sup["net_redemption_bn"] = (-sup["circ"].diff()) / 1e9          # positive = redemption
sup.to_csv(PROC / "tron_usdt_supply_daily.csv", index=False)
sw = sup[(sup["date"] >= LO) & (sup["date"] <= HI)].copy()

# --- USDT hourly price ---
px = pd.read_parquet(RAW / "cryptocompare_usdt_usd_3600s_20260601.parquet")
px["t"] = pd.to_datetime(px["time"], utc=True)
px = px[(px["t"] >= LO) & (px["t"] <= HI)].copy()

fig, ax1 = plt.subplots(figsize=(7.4, 4.0), dpi=170)
ax2 = ax1.twinx()
ax2.bar(sw["date"], sw["net_redemption_bn"].clip(lower=0), width=0.7, color="#E8973A",
        alpha=0.85, zorder=1, label="Net redemption, Tron USDT supply (daily)")
ax2.set_ylabel("Net on-chain redemption per day (USD bn)", color="#B5651D", fontsize=9.5)
ax2.tick_params(axis="y", labelcolor="#B5651D", labelsize=8.5)
ax2.set_ylim(0, max(sw["net_redemption_bn"].max() * 1.15, 1.0))

ax1.plot(px["t"], px["close"], color="#2F5C8A", lw=1.8, zorder=3, label="USDT secondary price")
ax1.fill_between(px["t"], px["close"], 1.0, where=(px["close"] < 1.0), color="#C0392B", alpha=0.18, zorder=2)
ax1.axhline(1.0, color="#777777", lw=0.8, ls="--", zorder=2)
ax1.set_ylabel("USDT secondary price (USD)", color="#2F5C8A", fontsize=9.5)
ax1.tick_params(axis="y", labelcolor="#2F5C8A", labelsize=8.5)
ax1.set_ylim(0.93, 1.005)
ax1.set_zorder(ax2.get_zorder() + 1); ax1.patch.set_visible(False)

ax1.axvline(pd.Timestamp("2022-05-09 12:00", tz="UTC"), color="#444444", lw=0.8, ls=":", zorder=2)
ax1.text(pd.Timestamp("2022-05-09 12:00", tz="UTC"), 0.933, " UST de-pegs;\n Terra collapse",
         fontsize=7.6, ha="left", va="bottom", color="#333333")

ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
ax1.xaxis.set_major_locator(mdates.DayLocator(interval=3))
ax1.set_xlim(LO, HI)
for s in ("top",):
    ax1.spines[s].set_visible(False); ax2.spines[s].set_visible(False)
l1, lb1 = ax1.get_legend_handles_labels()
l2, lb2 = ax2.get_legend_handles_labels()
ax1.legend(l1 + l2, lb1 + lb2, loc="lower left", bbox_to_anchor=(0.0, 1.01),
           ncol=2, frameon=False, fontsize=8.3)
fig.tight_layout()
out = ROOT.parent / "paper" / "figures" / "fig_terra_onchain.pdf"
fig.savefig(out, bbox_inches="tight"); fig.savefig(out.with_suffix(".png"), bbox_inches="tight", facecolor="white")
print("window net redemption (bn):", round(sw["net_redemption_bn"].clip(lower=0).sum(), 2),
      "| min USDT price:", round(px["close"].min(), 4))
print("wrote", out)
