"""Block-bootstrap standard errors for the USDT risk premium.

Mirror of `bootstrap_calibration.py` for the USDT May-2022 stress window
(Terra/UST fallout, 97 hours, 2022-05-11 to 2022-05-15). Each replication:
circular-block-resample the hourly secondary price, recompute the three
stress moments, re-run the calibration warm-started at phi*, and recompute
the premium. Baseline moments and Monte Carlo seeds are held fixed so the
spread reflects data resampling, not simulation noise.

Usage: bootstrap_calibration_usdt.py <n_reps>
Output: data/processed/bootstrap_usdt.json
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stablecoin_ms.simple_calibration import simple_bounds_vector  # noqa: E402
from stablecoin_ms.usdt_calibration import (  # noqa: E402
    USDT_WEIGHTS, USDTTargets, risk_components_usdt, usdt_loss,
)

ROOT = Path(__file__).resolve().parents[2]
P_S = 0.0108
BOUNDS = np.array(simple_bounds_vector())
PHI0 = np.array(json.loads((ROOT / "data" / "processed" / "h1_recalibration_results.json")
                           .read_text())["USDT | constant_h1=0"]["phi"])
TARG = USDTTargets.from_json()

# the Terra-fallout 97h window, reproduced exactly from the parquet
# (min 0.9751, mad 27.72, freq<0.99 = 0.0515)
_df = pd.read_parquet(ROOT / "data" / "raw" / "cryptocompare_usdt_usd_3600s_20260601.parquet")
_df["time"] = pd.to_datetime(_df["time"], utc=True)
_df = _df.sort_values("time")
STRESS = _df[(_df["time"] >= "2022-05-11") & (_df["time"] <= "2022-05-15 00:00")]["close"].to_numpy(float)
assert len(STRESS) == 97, len(STRESS)
P_THR = TARG.p_threshold  # 0.99 for USDT


def block_resample(x, rng, block=12):
    n = len(x)
    out = []
    while len(out) < n:
        s = rng.integers(0, n)
        out.extend(x[(s + k) % n] for k in range(block))
    return np.array(out[:n])


def stress_moments(w):
    return (float(w.min()), float(np.mean(np.abs(1 - w)) * 1e4), float(np.mean(w < P_THR)))


def objective(phi, targets):
    phi = np.clip(phi, BOUNDS[:, 0], BOUNDS[:, 1])
    return usdt_loss(phi, targets, n_draws=120, weights=USDT_WEIGHTS, seed=42)


def one_rep(rng):
    w = block_resample(STRESS, rng)
    mn, mad, freq = stress_moments(w)
    targets = replace(TARG, stress_min_close=mn, stress_mean_abs_depeg_bps=mad,
                      stress_large_depeg_freq=freq)
    res = minimize(objective, PHI0, args=(targets,), method="Nelder-Mead",
                   options={"maxiter": 50, "xatol": 1e-3, "fatol": 1e-3})
    phi = np.clip(res.x, BOUNDS[:, 0], BOUNDS[:, 1])
    rc = risk_components_usdt(phi, n_draws=400, seed=42)
    cp, db, ds = rc["counterparty_loss_bps"], rc["depeg_loss_baseline_bps"], rc["depeg_loss_stress_bps"]
    pi = cp + (1 - P_S) * db + P_S * ds
    return {"pi": pi, "cp": cp, "db": db, "ds": ds, "moments": [mn, mad, freq]}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    rng = np.random.default_rng(20260610)
    reps = []
    t0 = time.time()
    for r in range(n):
        out = one_rep(rng)
        reps.append(out)
        print(f"rep {r+1}/{n}: Pi={out['pi']:.2f}  ({(time.time()-t0)/(r+1):.1f}s/rep)", flush=True)
    pis = np.array([x["pi"] for x in reps])
    summary = {
        "n_reps": n, "point_estimate": 71.2,
        "boot_mean": float(pis.mean()), "boot_se": float(pis.std(ddof=1)),
        "ci90": [float(np.percentile(pis, 5)), float(np.percentile(pis, 95))],
        "ci95": [float(np.percentile(pis, 2.5)), float(np.percentile(pis, 97.5))],
        "reps": reps,
    }
    (ROOT / "data" / "processed" / "bootstrap_usdt.json").write_text(json.dumps(summary, indent=2))
    print(f"\nPi=71.2  boot_mean={summary['boot_mean']:.2f}  SE={summary['boot_se']:.2f}  "
          f"90% CI=[{summary['ci90'][0]:.1f},{summary['ci90'][1]:.1f}]")


if __name__ == "__main__":
    main()
