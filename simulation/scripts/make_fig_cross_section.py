"""Cross-stablecoin map: realised depeg in the two systemic episodes.

Reads data/processed/cross_section_depeg.json (seven fiat-backed coins, FRAX
excluded) and plots each on the plane of the March 2023 banking-shock (SVB)
depeg against the May 2022 contagion-shock (Terra) depeg. Bubble area is the
coin's approximate peak circulating supply over 2022-2023, so the largest
issuers (USDT, USDC) read as the biggest bubbles. Vulnerability is
shock-specific: USDC/DAI fall hard in SVB but not Terra, USDT the reverse, so
the two calibrated coins sit in opposite corners. Realised prices only, no model.
Output: paper/figures/fig_cross_section_map.pdf
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
d = json.loads((ROOT / "data" / "processed" / "cross_section_depeg.json").read_text())

COINS = ["USDC", "USDT", "DAI", "USDP", "GUSD", "TUSD", "BUSD"]  # FRAX excluded
# approximate peak circulating supply over 2022-2023, USD billions (size cue only)
CAP = {"USDT": 83.0, "USDC": 50.0, "BUSD": 17.0, "DAI": 9.0, "TUSD": 2.0, "USDP": 1.0, "GUSD": 0.6}
COLOR = {"USDC": "#2F5C8A", "USDT": "#C0392B"}  # the two calibrated poles; others grey
GREY = "#8C8C8C"
# label offsets in points (dx, dy, ha) to avoid overlap
LAB = {
    "USDC": (0, 16, "center"), "USDT": (16, 0, "left"), "DAI": (12, -4, "left"),
    "USDP": (12, 4, "left"), "GUSD": (12, 2, "left"), "TUSD": (12, 4, "left"),
    "BUSD": (13, 2, "left"),
}

fig, ax = plt.subplots(figsize=(7.8, 6.3), dpi=200)

for c in COINS:
    svb = d[c]["SVB_Mar2023"]["max_depeg_bps"]
    terra = d[c]["Terra_May2022"]["max_depeg_bps"]
    col = COLOR.get(c, GREY)
    s = 30 + CAP[c] * 13.0
    ax.scatter([svb], [terra], s=s, color=col, alpha=0.80, edgecolor="white", linewidth=1.2, zorder=3)
    dx, dy, ha = LAB[c]
    ax.annotate(c, (svb, terra), color=col, fontsize=10.5,
                fontweight="bold" if c in COLOR else "normal",
                xytext=(dx, dy), textcoords="offset points", ha=ha, va="center", zorder=4)

# region annotations, placed in clear areas away from the bubbles
ax.text(1255, 288, "vulnerable to\nboth shocks", fontsize=8.5, color="#b0b0b0",
        style="italic", ha="right", va="top")
ax.text(650, 70, "hit by the banking shock,\nrobust to the contagion", fontsize=8.7,
        color="#2F5C8A", style="italic", ha="center", va="center")
ax.text(120, 205, "hit by the contagion,\nrobust to the banking shock", fontsize=8.7,
        color="#C0392B", style="italic", ha="left", va="center")

ax.set_xlim(-60, 1280)
ax.set_ylim(-15, 312)
ax.set_xlabel("Depeg in the March 2023 banking shock, SVB (bps below par)", fontsize=10.5)
ax.set_ylabel("Depeg in the May 2022 contagion shock, Terra (bps below par)", fontsize=10.5)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.grid(True, color="#eeeeee", lw=0.6, zorder=0)
fig.tight_layout()
out = ROOT / "paper" / "figures" / "fig_cross_section_map.pdf"
fig.savefig(out, bbox_inches="tight")
fig.savefig(out.with_suffix(".png"), bbox_inches="tight", facecolor="white")
print("wrote", out)
