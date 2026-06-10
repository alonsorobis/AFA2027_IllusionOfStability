"""Inverse-variance moment weighting: one-row sensitivity for the internet appendix.

The headline calibrations minimise a weighted SSE with fixed scale-normalisation
weights. This script answers the natural referee question (why these weights?)
by re-running each calibration once under weights equal to the inverse of the
block-bootstrap variances of the empirical moments (the efficient-GMM diagonal),
and reporting how far the risk premium moves from its headline value.

Moment variances: the three stress moments are block-bootstrapped (12-hour
blocks) from the issuer's stress window; the three baseline moments are
block-bootstrapped (168-hour blocks) from the 2024 baseline year. 2,000
moment replications each (no recalibration inside the variance step).

Output: data/processed/iv_weight_sensitivity.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stablecoin_ms.simple_calibration import (  # noqa: E402
    USDCTargets, risk_components_at, simple_bounds_vector, simple_loss,
)
from stablecoin_ms.usdt_calibration import (  # noqa: E402
    USDTTargets, risk_components_usdt, usdt_loss,
)

ROOT = Path(__file__).resolve().parents[2]
P_S = 0.0108
BOUNDS = np.array(simple_bounds_vector())
RES = json.loads((ROOT / "data" / "processed" / "h1_recalibration_results.json").read_text())

MOMENT_NAMES = ["baseline_mean_close", "baseline_std_close", "baseline_large_depeg_freq",
                "stress_min_close", "stress_mean_abs_depeg_bps", "stress_large_depeg_freq"]


def block_resample(x, rng, block):
    n = len(x)
    out = []
    while len(out) < n:
        s = rng.integers(0, n)
        out.extend(x[(s + k) % n] for k in range(block))
    return np.array(out[:n])


def load_closes(parquet, t0, t1):
    df = pd.read_parquet(ROOT / "data" / "raw" / parquet)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time")
    return df[(df["time"] >= t0) & (df["time"] <= t1)]["close"].to_numpy(float)


def moment_variances(baseline, stress, thr, n_boot=2000, seed=20260610):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_boot):
        b = block_resample(baseline, rng, block=168)
        s = block_resample(stress, rng, block=12)
        rows.append([b.mean(), b.std(), np.mean(b < thr),
                     s.min(), np.mean(np.abs(1 - s)) * 1e4, np.mean(s < thr)])
    var = np.var(np.array(rows), axis=0, ddof=1)
    # floor each variance at (1e-6 of the moment scale)^2 to keep degenerate
    # moments (e.g. a baseline depeg frequency that is identically zero in
    # nearly every replication) from receiving an unbounded weight
    scale = np.array([1.0, 1e-3, 1e-2, 1.0, 100.0, 1e-1])
    var = np.maximum(var, (1e-3 * scale) ** 2)
    return {n: float(v) for n, v in zip(MOMENT_NAMES, var)}


def run_asset(asset):
    if asset == "USDC":
        targ = USDCTargets.from_json()
        thr = 0.975
        baseline = load_closes("cryptocompare_usdc_usd_3600s_20260601.parquet",
                               "2024-01-01", "2024-12-31 23:00")
        stress = load_closes("cryptocompare_usdc_usd_3600s_20260601.parquet",
                             "2023-03-10", "2023-03-13 23:00")
        phi0 = np.array(RES["USDC | constant_h1=0"]["phi"])
        loss_fn, comp_fn = simple_loss, lambda p: risk_components_at(
            p, issuer_hazard=0.01, issuer_lgd=0.20, n_draws=400, seed=42)
        headline = 48.9
    else:
        targ = USDTTargets.from_json()
        thr = targ.p_threshold
        baseline = load_closes("cryptocompare_usdt_usd_3600s_20260601.parquet",
                               "2024-01-01", "2024-12-31 23:00")
        stress = load_closes("cryptocompare_usdt_usd_3600s_20260601.parquet",
                             "2022-05-11", "2022-05-15 00:00")
        phi0 = np.array(RES["USDT | constant_h1=0"]["phi"])
        loss_fn, comp_fn = usdt_loss, lambda p: risk_components_usdt(p, n_draws=400, seed=42)
        headline = 71.2

    var = moment_variances(baseline, stress, thr)
    weights = {n: 1.0 / v for n, v in var.items()}
    print(f"{asset} IV weights:", {k: f"{v:.3g}" for k, v in weights.items()}, flush=True)

    def objective(phi):
        phi = np.clip(phi, BOUNDS[:, 0], BOUNDS[:, 1])
        return loss_fn(phi, targ, n_draws=120, weights=weights, seed=42)

    t0 = time.time()
    res = minimize(objective, phi0, method="Nelder-Mead",
                   options={"maxiter": 300, "xatol": 1e-4, "fatol": 1e-6})
    phi = np.clip(res.x, BOUNDS[:, 0], BOUNDS[:, 1])
    rc = comp_fn(phi)
    cp, db, ds = (rc["counterparty_loss_bps"], rc["depeg_loss_baseline_bps"],
                  rc["depeg_loss_stress_bps"])
    pi = cp + (1 - P_S) * db + P_S * ds
    print(f"{asset}: Pi_IV={pi:.2f} (headline {headline}); "
          f"cp={cp:.1f} db={db:.2f} ds={ds:.1f}  [{time.time()-t0:.0f}s]", flush=True)
    return {"headline": headline, "pi_iv": float(pi), "cp": float(cp),
            "db": float(db), "ds": float(ds), "phi_iv": phi.tolist(),
            "weights": weights, "moment_variances": var,
            "nm_iters": int(res.nit), "nm_converged": bool(res.success)}


def main():
    out = {a: run_asset(a) for a in ("USDC", "USDT")}
    (ROOT / "data" / "processed" / "iv_weight_sensitivity.json").write_text(
        json.dumps(out, indent=2))
    print("Wrote iv_weight_sensitivity.json")


if __name__ == "__main__":
    main()
