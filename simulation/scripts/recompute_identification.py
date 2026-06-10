"""Recompute A3 identification diagnostics at the corrected (counterparty-in-V_H) phi*.

Outputs to data/processed/identification_corrected.json:
  - USDC moments at phi* vs targets
  - USDT moments at phi* vs targets
  - Jacobian per-parameter identification strength at USDC phi*
  - SVD singular values, effective rank, condition number
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stablecoin_ms.simple_calibration import (
    SIMPLE_PARAM_NAMES,
    USDCTargets,
    simple_bounds_vector,
    simple_moments,
)
from stablecoin_ms.usdt_calibration import USDTTargets, usdt_moments

MOMENT_NAMES = (
    "baseline_mean_close",
    "baseline_std_close",
    "baseline_large_depeg_freq",
    "stress_min_close",
    "stress_mean_abs_depeg_bps",
    "stress_large_depeg_freq",
)

# Corrected phi* from h1_recalibration_results.json (constant-h spec)
PHI_USDC = np.array([0.19368812639123134, 0.27459061603325163, 1.740548754749086,
                     0.052691159616821664, 0.507352543351488, 0.21247327324753199,
                     9.881810438888362])
PHI_USDT = np.array([0.2366794100547257, 0.10806092952834376, 4.0,
                     0.02191403141624647, 0.4527849028439752, 0.23075705814896785,
                     7.980707184433772])

N_DRAWS = 400
SEED = 44


def moments_vec(phi, which):
    if which == "usdc":
        m = simple_moments(phi, n_draws=N_DRAWS, seed=SEED)
    else:
        m = usdt_moments(phi, n_draws=N_DRAWS, seed=SEED)
    return np.array([m[n] for n in MOMENT_NAMES]), m


def main() -> int:
    usdc_t = USDCTargets.from_json()
    usdt_t = USDTTargets.from_json()

    mc_usdc, dc_usdc = moments_vec(PHI_USDC, "usdc")
    mc_usdt, dc_usdt = moments_vec(PHI_USDT, "usdt")

    # Jacobian at USDC phi*: central differences, step = 0.05 * bound width
    bounds = simple_bounds_vector()
    base_m, _ = moments_vec(PHI_USDC, "usdc")
    J = np.zeros((len(MOMENT_NAMES), len(PHI_USDC)))
    for j in range(len(PHI_USDC)):
        lo, hi = bounds[j]
        step = 0.05 * (hi - lo)
        php = PHI_USDC.copy(); php[j] += step
        phm = PHI_USDC.copy(); phm[j] -= step
        mp, _ = moments_vec(php, "usdc")
        mm, _ = moments_vec(phm, "usdc")
        J[:, j] = (mp - mm) / (2 * step)

    # Normalise: each column by |phi*_j|, each row by |target_j| (where > 1e-8)
    targ = np.array([getattr(usdc_t, n) for n in MOMENT_NAMES])
    Jn = J.copy()
    for j in range(len(PHI_USDC)):
        Jn[:, j] *= abs(PHI_USDC[j])
    for i in range(len(MOMENT_NAMES)):
        if abs(targ[i]) > 1e-8:
            Jn[i, :] /= abs(targ[i])

    strength = np.linalg.norm(Jn, axis=0)
    sv = np.linalg.svd(Jn, compute_uv=False)
    eff_rank = int(np.sum(sv > 0.01))
    above = sv[sv > 0.01]
    kappa = float(above[0] / above[-1]) if len(above) > 1 else float("nan")

    out = {
        "usdc": {
            "phi_star": dict(zip(SIMPLE_PARAM_NAMES, [float(v) for v in PHI_USDC])),
            "moments_model": {n: float(v) for n, v in zip(MOMENT_NAMES, mc_usdc)},
            "moments_target": {n: float(getattr(usdc_t, n)) for n in MOMENT_NAMES},
        },
        "usdt": {
            "phi_star": dict(zip(SIMPLE_PARAM_NAMES, [float(v) for v in PHI_USDT])),
            "moments_model": {n: float(v) for n, v in zip(MOMENT_NAMES, mc_usdt)},
            "moments_target": {n: float(getattr(usdt_t, n)) for n in MOMENT_NAMES},
        },
        "identification_usdc": {
            "strength": {n: float(s) for n, s in zip(SIMPLE_PARAM_NAMES, strength)},
            "singular_values": [float(s) for s in sv],
            "effective_rank": eff_rank,
            "condition_number": kappa,
        },
    }
    out_path = ROOT.parent / "data" / "processed" / "identification_corrected.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
