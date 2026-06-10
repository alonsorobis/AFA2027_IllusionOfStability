"""Baseline-prior precision sensitivity for the USDC headline risk premium.

Re-runs the risk-component decomposition at phi* over a grid of tau_baseline
values, holding all other parameters fixed. Tests whether the externally
fixed tau_baseline = 400 is in the saturating range claimed in the paper.

Writes data/processed/tau_baseline_sensitivity.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import stablecoin_ms.simple_calibration as sc

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USDC_MANIFEST = PROJECT_ROOT / "data" / "processed" / "simple_calibration_20260602T092829Z" / "manifest.json"

P_STRESS = 0.0108
TAU_GRID = [100.0, 400.0, 1600.0]


def headline_at(phi_vec: np.ndarray, tau_b: float, n_draws: int = 500, seed: int = 42) -> dict:
    """Evaluate the three risk components and the probability-weighted total
    at a given tau_baseline, holding phi* fixed."""
    original_tau = sc.TAU_BASELINE
    sc.TAU_BASELINE = tau_b
    try:
        comps = sc.risk_components_at(phi_vec, n_draws=n_draws, seed=seed)
    finally:
        sc.TAU_BASELINE = original_tau

    ell_C = comps["counterparty_loss_bps"]
    ell_Db = comps["depeg_loss_baseline_bps"]
    ell_Ds = comps["depeg_loss_stress_bps"]
    total = ell_C + (1.0 - P_STRESS) * ell_Db + P_STRESS * ell_Ds
    return {
        "tau_baseline": tau_b,
        "sigma_theta": float(1.0 / np.sqrt(tau_b)),
        "ell_C": ell_C,
        "ell_Db": ell_Db,
        "ell_Ds": ell_Ds,
        "ell_Db_weighted": (1.0 - P_STRESS) * ell_Db,
        "ell_Ds_weighted": P_STRESS * ell_Ds,
        "total_bps": total,
    }


def main() -> int:
    manifest = json.loads(USDC_MANIFEST.read_text())
    phi_star = manifest["phi_star"]
    phi_vec = np.array([
        phi_star["sigma"], phi_star["psi"], phi_star["nu"],
        phi_star["mu_q"], phi_star["zeta"],
        phi_star["theta_stress"], phi_star["tau_stress"],
    ])

    rows = []
    print(f"{'tau_b':>8} {'sigma_th':>10} {'ell_C':>8} {'ell_Db':>8} {'ell_Ds':>8} {'total':>8}")
    for tau_b in TAU_GRID:
        row = headline_at(phi_vec, tau_b)
        rows.append(row)
        print(f"{row['tau_baseline']:>8.0f} {row['sigma_theta']:>10.4f} "
              f"{row['ell_C']:>8.2f} {row['ell_Db']:>8.2f} {row['ell_Ds']:>8.2f} "
              f"{row['total_bps']:>8.2f}")

    out = {
        "phi_star_source": str(USDC_MANIFEST.relative_to(PROJECT_ROOT)),
        "p_stress": P_STRESS,
        "rows": rows,
    }
    out_path = PROJECT_ROOT / "data" / "processed" / "tau_baseline_sensitivity.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
