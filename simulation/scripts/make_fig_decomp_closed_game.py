"""Closed-game expected-loss decomposition figure (USDC 42 / USDT 72)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
comps = ["counterparty\n$\ell_C$", "baseline depeg\n$\ell_{D,b}$ (basis)", "stress depeg\n$\ell_{D,s}$ (game)"]
usdc = [20.0, 21.0, 1.2]
usdt = [60.0, 12.0, 0.0]
y = np.arange(3); bh = 0.36
fig, ax = plt.subplots(figsize=(7.0, 3.4))
bu = ax.barh(y + bh/2, usdc, height=bh, color="#2e6fb7", label="USDC (42 bps)", edgecolor="black", linewidth=0.4)
bt = ax.barh(y - bh/2, usdt, height=bh, color="#c75b4a", label="USDT (72 bps)", edgecolor="black", linewidth=0.4)
for bar, v in list(zip(bu, usdc)) + list(zip(bt, usdt)):
    ax.text(v + 0.7, bar.get_y() + bar.get_height()/2, f"{v:.1f}", va="center", ha="left", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(comps, fontsize=9)
ax.set_xlabel("Basis points", fontsize=10); ax.set_xlim(0, 66); ax.invert_yaxis()
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.legend(loc="lower right", fontsize=9, frameon=False)
plt.tight_layout()
out = ROOT / "paper" / "figures" / "fig_decomp_closed_game.pdf"
fig.savefig(out, format="pdf", bbox_inches="tight"); plt.close(fig)
print("wrote", out)
