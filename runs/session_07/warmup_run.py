"""Session 07 — Step 2: warm-up calibration run.

Short N=100, maxiter=20 Nelder-Mead pass against USDC March 2023 targets.
Saves the warm-start phi vector, the loss and the moments-comparison manifest
to `data/processed/usdc_calibration_warmup_<UTC_DATE_TAG>.json`.

This script does NOT modify the simulation package or the calibration code.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "simulation"))

from stablecoin_ms.calibration import (  # noqa: E402
    PARAM_NAMES,
    USDCMarch2023Targets,
    calibrate_usdc,
    model_moments_pair,
    template_scenario,
)


def main() -> int:
    targets = USDCMarch2023Targets.from_json()
    print("Targets loaded:")
    for k in (
        "baseline_mean_close",
        "baseline_std_close",
        "baseline_large_depeg_freq",
        "stress_min_close",
        "stress_mean_abs_depeg_bps",
        "stress_large_depeg_freq",
    ):
        print(f"  {k:30s} = {getattr(targets, k)}")

    seed = 42
    n_draws_eval = 100
    maxiter = 20

    print(f"\nStarting warm-up calibration: N={n_draws_eval}, maxiter={maxiter}, seed={seed}")
    t0 = time.time()
    out = calibrate_usdc(
        targets=targets,
        n_draws_eval=n_draws_eval,
        seed=seed,
        maxiter=maxiter,
    )
    elapsed = time.time() - t0
    print(f"Warm-up finished in {elapsed:.1f} s")

    phi_star = out["phi_star"]
    loss = out["loss"]
    print(f"Final loss: {loss:.4f}")
    print("Calibrated phi:")
    for name in PARAM_NAMES:
        print(f"  {name:25s} = {phi_star[name]:.6f}")

    # Compute moments at the optimum for the manifest
    phi_vec = np.array([phi_star[n] for n in PARAM_NAMES])
    base_tmpl = template_scenario("usdc_calib_baseline", n_draws_eval, seed)
    stress_tmpl = template_scenario("usdc_calib_stress", n_draws_eval, seed + 1)
    base_m, stress_m = model_moments_pair(phi_vec, base_tmpl, stress_tmpl)

    manifest = {
        "session": "07",
        "stage": "warmup",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "n_draws_eval": n_draws_eval,
        "maxiter": maxiter,
        "walltime_seconds": elapsed,
        "loss": loss,
        "phi_star": phi_star,
        "targets": {
            "baseline_mean_close": targets.baseline_mean_close,
            "baseline_std_close": targets.baseline_std_close,
            "baseline_large_depeg_freq": targets.baseline_large_depeg_freq,
            "stress_min_close": targets.stress_min_close,
            "stress_mean_abs_depeg_bps": targets.stress_mean_abs_depeg_bps,
            "stress_large_depeg_freq": targets.stress_large_depeg_freq,
        },
        "model_moments_baseline": base_m,
        "model_moments_stress": stress_m,
    }

    date_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = PROJECT_ROOT / "data" / "processed" / f"usdc_calibration_warmup_{date_tag}.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote warm-start manifest to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
