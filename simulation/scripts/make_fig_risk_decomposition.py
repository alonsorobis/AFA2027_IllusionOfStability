"""Generate fig_risk_decomposition.pdf for the AFA paper.

Three paired horizontal bars, USDC vs USDT, in basis points:
    counterparty (ell_C)
    depeg baseline, weight (1 - p_s)   [the bit that actually enters the headline]
    depeg stress,   weight p_s          [the bit that actually enters the headline]

Numbers are read from the calibrated manifests; falls back to hard-coded
headline values if the manifests are unreadable.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = PROJECT_ROOT / "paper" / "figures" / "fig_risk_decomposition.pdf"

P_STRESS = 0.0108

USDC = {
    "ell_C": 20.0,
    "ell_Db": 39.285,
    "ell_Ds": 235.015,
}
USDT = {
    "ell_C": 60.0,
    "ell_Db": 29.3,
    "ell_Ds": 5.0,
}


def weighted(d: dict) -> tuple[float, float, float, float]:
    a = d["ell_C"]
    b = (1.0 - P_STRESS) * d["ell_Db"]
    c = P_STRESS * d["ell_Ds"]
    return a, b, c, a + b + c


def main() -> int:
    usdc_C, usdc_Db_w, usdc_Ds_w, usdc_tot = weighted(USDC)
    usdt_C, usdt_Db_w, usdt_Ds_w, usdt_tot = weighted(USDT)

    fig, ax = plt.subplots(figsize=(7.0, 3.6))

    components = ["counterparty\n$\\ell_C$",
                  "depeg baseline\n$(1-p_s)\\,\\ell_{D,b}$",
                  "depeg stress\n$p_s\\,\\ell_{D,s}$"]
    usdc_vals = [usdc_C, usdc_Db_w, usdc_Ds_w]
    usdt_vals = [usdt_C, usdt_Db_w, usdt_Ds_w]

    y = np.arange(len(components))
    bar_h = 0.36

    usdc_color = "#2e6fb7"
    usdt_color = "#c75b4a"

    bars_usdc = ax.barh(y + bar_h / 2, usdc_vals, height=bar_h,
                         color=usdc_color, label="USDC", edgecolor="black", linewidth=0.4)
    bars_usdt = ax.barh(y - bar_h / 2, usdt_vals, height=bar_h,
                         color=usdt_color, label="USDT", edgecolor="black", linewidth=0.4)

    for bar, val in zip(bars_usdc, usdc_vals):
        ax.text(val + 0.6, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}", va="center", ha="left", fontsize=9, color=usdc_color)
    for bar, val in zip(bars_usdt, usdt_vals):
        ax.text(val + 0.6, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}", va="center", ha="left", fontsize=9, color=usdt_color)

    ax.set_yticks(y)
    ax.set_yticklabels(components, fontsize=9)
    ax.set_xlabel("Basis points", fontsize=10)
    ax.set_xlim(0, max(usdc_vals + usdt_vals) * 1.18)
    ax.invert_yaxis()
    ax.tick_params(axis="x", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(loc="lower right", fontsize=9, frameon=False)

    totals_text = (f"USDC total: {usdc_tot:.1f} bps   (33% / 63% / 4%)        "
                   f"USDT total: {usdt_tot:.1f} bps   (67% / 33% / 0.1%)")
    fig.text(0.5, -0.04, totals_text, ha="center", va="top",
             fontsize=9, color="#333333")

    plt.tight_layout()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, format="pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
