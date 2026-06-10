"""Quadrant view of the inverted risk profiles: each calibrated stablecoin placed
on the (counterparty component, depeg component) plane, bubble area proportional
to the total risk premium. The 45-degree line separates the counterparty-dominant
from the depeg-dominant region; USDC and USDT fall on opposite sides.

Coordinates are the calibrated decomposition (session 22): ell_C, ell_D (=ell_Db
weighted + ell_Ds weighted), Pi. Output: paper/figures/fig_quadrant.pdf
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

# (ell_C, ell_D, Pi)
DATA = {
    "USDC": (20.0, 29.0, 48.9, "#2F5C8A"),
    "USDT": (60.0, 11.2, 71.2, "#C0392B"),
}

fig, ax = plt.subplots(figsize=(5.6, 5.2), dpi=170)
M = 72

# region shading and the equal-split diagonal
ax.fill_between([0, M], [0, M], M, color="#2F5C8A", alpha=0.05, zorder=0)   # above diagonal: depeg-dominant
ax.fill_between([0, M], 0, [0, M], color="#C0392B", alpha=0.05, zorder=0)   # below diagonal: counterparty-dominant
ax.plot([0, M], [0, M], ls="--", color="#888888", lw=1.0, zorder=1)
ax.text(M*0.97, M*0.90, "equal split", color="#888888", fontsize=8, ha="right", rotation=45, rotation_mode="anchor")
ax.text(6, M*0.92, "depeg-dominant", color="#2F5C8A", fontsize=9.5, style="italic")
ax.text(M*0.50, 4.5, "counterparty-dominant", color="#C0392B", fontsize=9.5, style="italic")

for name, (lc, ld, pi, col) in DATA.items():
    ax.scatter([lc], [ld], s=pi*34, color=col, alpha=0.85, edgecolor="white", linewidth=1.2, zorder=3)
    ax.annotate(f"{name}\n{pi:.0f} bps", (lc, ld), color=col, fontsize=10.5, fontweight="bold",
                ha="center", va="center", zorder=4,
                xytext=(0, 0), textcoords="offset points")

ax.set_xlim(0, M); ax.set_ylim(0, M)
ax.set_xlabel(r"Counterparty component $\ell_C$ (bps)", fontsize=10.5)
ax.set_ylabel(r"Depeg component $\ell_{D}$ (bps)", fontsize=10.5)
ax.set_aspect("equal")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(True, color="#eeeeee", lw=0.6, zorder=0)
ax.set_title("Inverted risk profiles of the two stablecoins", fontsize=12.5, fontweight="bold", pad=10)
fig.text(0.5, -0.01, "Bubble area is proportional to the total risk premium; the dashed line is the equal split of the two components.",
         ha="center", fontsize=8.2, color="#555555", style="italic")
fig.tight_layout()
out = ROOT.parent / "paper" / "figures" / "fig_quadrant.pdf"
fig.savefig(out, bbox_inches="tight"); fig.savefig(out.with_suffix(".png"), bbox_inches="tight", facecolor="white")
print("wrote", out)
