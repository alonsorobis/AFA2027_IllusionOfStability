#!/usr/bin/env python3
"""Google Trends retail-attention figure for the internet appendix.

Data: weekly/monthly relative search interest (0-100) for the terms
'stablecoin', 'USDC', 'USDT', pulled via pytrends. Produces a descriptive
time-series figure with vertical markers at the dated episodes referenced in
the regulatory-uncertainty discussion.
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

df = pd.read_csv("google_trends_stablecoins_long.csv", parse_dates=["date"]).set_index("date")

episodes = [
    ("2022-05-09", "Terra/UST\ncollapse"),
    ("2023-03-10", "USDC depeg\n(SVB)"),
    ("2024-12-30", "MiCA\nTitle V"),
    ("2025-11-15", "BCB Res.\n561/2026"),
]

fig, ax = plt.subplots(figsize=(9, 4.2))
styles = {"stablecoin": ("-", "#1f4e79"), "USDC": ("--", "#2e8b57"), "USDT": ("-.", "#b22222")}
for col, (ls, c) in styles.items():
    ax.plot(df.index, df[col], ls, color=c, lw=1.6, label=col)

ymax = df[["stablecoin", "USDC", "USDT"]].values.max()
for date, label in episodes:
    d = pd.Timestamp(date)
    ax.axvline(d, color="0.45", ls=":", lw=1.0)
    ax.text(d, ymax * 1.02, label, rotation=0, ha="center", va="bottom",
            fontsize=7.5, color="0.30")

ax.set_ylabel("Relative search interest (0-100)")
ax.set_xlabel("")
ax.set_ylim(0, ymax * 1.18)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.legend(frameon=False, loc="upper left", ncol=3, fontsize=9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
fig.tight_layout()
fig.savefig("google_trends_stablecoins.png", dpi=200, bbox_inches="tight")
print("saved google_trends_stablecoins.png")
