"""Small email-friendly graphic: per-stablecoin risk premium split into
counterparty vs depeg, marking the depeg slice as the global-game component.

Numbers from data/processed/paper_numbers_corrected.json (session 22).
Output: outreach/email_stablecoin_risk_split.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]

# bps (counterparty, depeg=baseline+stress, total)
DATA = {
    "USDC": {"cp": 20.0, "depeg": 26.4 + 2.6, "total": 48.9},
    "USDT": {"cp": 60.0, "depeg": 10.9 + 0.3, "total": 71.2},
}

CP_COLOR = "#3B6FA0"     # counterparty: steel blue
DEPEG_COLOR = "#E8973A"  # depeg: amber

fig, ax = plt.subplots(figsize=(7.6, 3.4), dpi=170)

bar_h = 0.46
y_pos = {"USDC": 1.0, "USDT": 0.0}

for coin, y in y_pos.items():
    cp = DATA[coin]["cp"]
    dp = DATA[coin]["depeg"]
    tot = DATA[coin]["total"]
    cp_pct = round(100 * cp / tot)
    dp_pct = 100 - cp_pct

    ax.barh(y, cp, height=bar_h, color=CP_COLOR, edgecolor="white", zorder=3)
    ax.barh(y, dp, left=cp, height=bar_h, color=DEPEG_COLOR, edgecolor="white", zorder=3)

    # counterparty label (always wide enough)
    ax.text(cp / 2, y, f"{cp:.0f}\n({cp_pct}%)", ha="center", va="center",
            color="white", fontsize=10.5, fontweight="bold", zorder=4)

    # depeg label: always inside, white; smaller font for thin segments
    dp_fs = 10.5 if dp >= 18 else 9.0
    ax.text(cp + dp / 2, y, f"{dp:.0f}\n({dp_pct}%)", ha="center", va="center",
            color="white", fontsize=dp_fs, fontweight="bold", zorder=4)

    # total at the end
    ax.text(tot + 1.6, y, f"= {tot:.1f} bps", ha="left", va="center",
            fontsize=11, fontweight="bold", color="#222222", zorder=4)

ax.set_yticks([1.0, 0.0])
ax.set_yticklabels(["USDC", "USDT"], fontsize=13, fontweight="bold")
ax.set_xlim(0, 88)
ax.set_ylim(-0.7, 1.85)
ax.set_xlabel("Risk-adjusted premium (basis points)", fontsize=10.5, labelpad=6)
ax.set_title("One global game, two inverted risk profiles",
             fontsize=13.5, fontweight="bold", pad=26)

# legend as colored text chips at top
ax.text(0.0, 1.72, "  ", bbox=dict(facecolor=CP_COLOR, edgecolor="none", pad=4),
        fontsize=9, zorder=5)
ax.text(3.0, 1.72, "Counterparty risk  ($h\\times\\xi$, market-implied, reduced form)",
        ha="left", va="center", fontsize=9.5, zorder=5)
ax.text(0.0, 1.50, "  ", bbox=dict(facecolor=DEPEG_COLOR, edgecolor="none", pad=4),
        fontsize=9, zorder=5)
ax.text(3.0, 1.50, "Depeg risk  =  the global game (self-fulfilling redemption run)",
        ha="left", va="center", fontsize=9.5, fontweight="bold", color="#8a5a12", zorder=5)

for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.grid(axis="x", color="#dddddd", lw=0.6, zorder=0)

fig.subplots_adjust(bottom=0.30)
fig.text(0.5, 0.005,
         "USDC is depeg-driven (59%); USDT is counterparty-driven (84%). "
         "The category 'stablecoin' is too coarse for one rule.",
         ha="center", fontsize=8.8, color="#555555", style="italic")

out_dir = ROOT.parent / "outreach"
out_dir.mkdir(exist_ok=True)
out_path = out_dir / "email_stablecoin_risk_split.png"
fig.savefig(out_path, bbox_inches="tight", facecolor="white")
print("wrote", out_path)
