"""Closed-game heterogeneity figure (view b): counterparty vs stress-depeg severity.
USDC and USDT occupy opposite corners: USDC low counterparty / deep stress depeg,
USDT high counterparty / shallow stress depeg. The conversion basis is a circuit
fee and is NOT plotted here (it is not a holding risk)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
# x = counterparty loss ell_C (bps); y = stress-depeg severity (trough below par, bps)
pts = {"USDC": (20.0, 978.0, "#2e6fb7"), "USDT": (60.0, 249.0, "#c75b4a")}
fig, ax = plt.subplots(figsize=(6.4, 4.4))
for name, (x, y, col) in pts.items():
    ax.scatter([x], [y], s=320, color=col, edgecolor="black", linewidth=0.6, zorder=3)
    dy = 60 if name == "USDC" else -90
    ax.annotate(name, (x, y), xytext=(x + 2.5, y + dy), fontsize=12, fontweight="bold", color=col)
ax.annotate("depeg-vulnerable\n(secondary market,\nprimary access)", (24, 880),
            fontsize=8.5, color="#2e6fb7", ha="left", va="top")
ax.annotate("counterparty-vulnerable\n(reserve composition,\nattestation)", (44, 360),
            fontsize=8.5, color="#c75b4a", ha="left", va="top")
ax.set_xlabel(r"Counterparty exposure $\ell_C = h\xi$  (basis points)", fontsize=10)
ax.set_ylabel("Stress-depeg severity (trough below par, bps)", fontsize=10)
ax.set_xlim(10, 70); ax.set_ylim(150, 1080)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(alpha=0.25, linestyle=":")
plt.tight_layout()
out = ROOT / "paper" / "figures" / "fig_decomp_closed_game.pdf"
fig.savefig(out, format="pdf", bbox_inches="tight"); plt.close(fig)
print("wrote", out)
