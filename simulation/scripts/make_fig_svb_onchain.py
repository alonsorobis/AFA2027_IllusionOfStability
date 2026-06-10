"""Descriptive figure: USDC secondary price vs on-chain redemptions during the
March 2023 SVB episode. Shows that the depeg (secondary discount) is borne while
primary redemption is suspended, and that on-chain burns (at-par redemptions)
surge only after the peg is restored -- the cost the global game prices.

Sources: CryptoCompare hourly USDC close; on-chain mint/burn from Etherscan
(data/processed/onchain_redemptions_USDC_SVB.csv). Output: paper/figures/fig_svb_onchain.pdf
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "data" / "raw"
PROC = ROOT.parent / "data" / "processed"

LO, HI = pd.Timestamp("2023-03-09", tz="UTC"), pd.Timestamp("2023-03-16", tz="UTC")

px = pd.read_parquet(RAW / "cryptocompare_usdc_usd_3600s_20260601.parquet")
px["t"] = pd.to_datetime(px["time"], utc=True)
px = px[(px["t"] >= LO) & (px["t"] <= HI)].copy()

flow = pd.read_csv(PROC / "onchain_redemptions_USDC_SVB.csv")
flow["t"] = pd.to_datetime(flow["hour_ts"], unit="s", utc=True)
flow = flow[(flow["t"] >= LO) & (flow["t"] <= HI)].copy()
flow["burn_bn"] = flow["burn"] / 1e9

fig, ax1 = plt.subplots(figsize=(7.4, 4.0), dpi=170)

# right axis: hourly burns (redemptions) as bars
ax2 = ax1.twinx()
ax2.bar(flow["t"], flow["burn_bn"], width=0.03, color="#E8973A", alpha=0.85,
        zorder=1, label="On-chain redemptions (burns)")
ax2.set_ylabel("On-chain USDC redeemed per hour (USD bn)", color="#B5651D", fontsize=9.5)
ax2.tick_params(axis="y", labelcolor="#B5651D", labelsize=8.5)
ax2.set_ylim(0, max(flow["burn_bn"].max() * 1.15, 0.1))

# left axis: secondary price, with below-par shading
ax1.plot(px["t"], px["close"], color="#2F5C8A", lw=1.8, zorder=3, label="USDC secondary price")
ax1.fill_between(px["t"], px["close"], 1.0, where=(px["close"] < 1.0),
                 color="#C0392B", alpha=0.18, zorder=2)
ax1.axhline(1.0, color="#777777", lw=0.8, ls="--", zorder=2)
ax1.set_ylabel("USDC secondary price (USD)", color="#2F5C8A", fontsize=9.5)
ax1.tick_params(axis="y", labelcolor="#2F5C8A", labelsize=8.5)
ax1.set_ylim(0.86, 1.01)
ax1.set_zorder(ax2.get_zorder() + 1)
ax1.patch.set_visible(False)

# event markers
events = [
    (pd.Timestamp("2023-03-10 18:00", tz="UTC"), "SVB closed;\nCircle exposure disclosed"),
    (pd.Timestamp("2023-03-13 04:00", tz="UTC"), "backstop announced;\nredemption reopens"),
]
for ts, lab in events:
    ax1.axvline(ts, color="#444444", lw=0.8, ls=":", zorder=2)
    ax1.text(ts, 0.875, lab, fontsize=7.6, ha="center", va="bottom", color="#333333")

ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.set_xlim(LO, HI)
for s in ("top",):
    ax1.spines[s].set_visible(False); ax2.spines[s].set_visible(False)

# combined legend
l1, lb1 = ax1.get_legend_handles_labels()
l2, lb2 = ax2.get_legend_handles_labels()
ax1.legend(l1 + l2, lb1 + lb2, loc="lower left", bbox_to_anchor=(0.0, 1.01),
           ncol=2, frameon=False, fontsize=8.5)

fig.tight_layout()
out = ROOT.parent / "paper" / "figures" / "fig_svb_onchain.pdf"
fig.savefig(out, bbox_inches="tight")
fig.savefig(out.with_suffix(".png"), bbox_inches="tight", facecolor="white")
print("wrote", out)
