"""Calibration runner: warmup pass + full Nelder-Mead pass.

Writes
    data/processed/usdc_calibration_<UTC_TS>/
        manifest.json           — phi*, loss, targets, baseline+stress moments
        phi_history.csv         — Nelder-Mead iterates (one row per iter)
        moments_comparison.csv  — target vs model per moment
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stablecoin_ms.calibration import (
    PARAM_NAMES,
    USDCMarch2023Targets,
    default_bounds,
    model_moments_pair,
    template_scenario,
    usdc_loss,
)


def make_runner(targets, tb, ts, history):
    def fn(phi: np.ndarray) -> float:
        clipped = np.clip(phi, [lo for lo, _ in default_bounds()], [hi for _, hi in default_bounds()])
        loss = usdc_loss(clipped, targets, tb, ts)
        history.append((time.time(), [float(v) for v in clipped], float(loss)))
        return loss
    return fn


def run_pass(label: str, x0: np.ndarray, targets, n_draws: int, maxiter: int, seed: int):
    tb = template_scenario(f"usdc_calib_{label}_baseline", n_draws=n_draws, seed=seed)
    ts = template_scenario(f"usdc_calib_{label}_stress", n_draws=n_draws, seed=seed + 1)
    history: list = []
    fn = make_runner(targets, tb, ts, history)
    t0 = time.time()
    res = minimize(
        fn,
        x0,
        method="Nelder-Mead",
        options={"maxiter": maxiter, "xatol": 1e-3, "fatol": 1e-3, "disp": False},
    )
    elapsed = time.time() - t0
    return res, history, elapsed, tb, ts


def main() -> int:
    targets = USDCMarch2023Targets.from_json()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT.parent / "data" / "processed" / f"usdc_calibration_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}Z] Starting calibration")
    print(f"out_dir = {out_dir.relative_to(ROOT.parent)}")

    x0_warm = np.array(
        [0.20, 0.15, 0.25, 0.10, 0.30, 1.5, 0.05, 0.50, 1.0, 0.2],
        dtype=float,
    )
    print(f"x0 warmup = {x0_warm.tolist()}")

    print("--- Warmup pass: N=100, maxiter=20 ---")
    warm_res, warm_hist, warm_elapsed, _, _ = run_pass(
        "warm", x0_warm, targets, n_draws=100, maxiter=20, seed=42
    )
    print(f"warmup done in {warm_elapsed/60:.2f} min; loss={warm_res.fun:.4f}")
    print(f"warmup phi* = {dict(zip(PARAM_NAMES, [round(v,4) for v in warm_res.x]))}")

    print("--- Main pass: N=200, maxiter=60, x0=warmup phi* ---")
    main_res, main_hist, main_elapsed, tb, ts = run_pass(
        "main", warm_res.x, targets, n_draws=200, maxiter=60, seed=44
    )
    print(f"main done in {main_elapsed/60:.2f} min; loss={main_res.fun:.4f}")
    phi_star = {k: float(v) for k, v in zip(PARAM_NAMES, main_res.x)}
    print(f"phi* = {phi_star}")

    bm, sm = model_moments_pair(main_res.x, tb, ts)
    moments_at_optimum = {"baseline": bm, "stress": sm}
    print(f"baseline at phi*: mean={bm['mean_p_sec']:.5f}, std={bm['std_p_sec']:.5f}, large_depeg_freq={bm['large_depeg_freq']:.4f}")
    print(f"stress at phi*:   min={sm['min_p_sec']:.5f}, mean_abs_bps={sm['mean_abs_depeg_bps']:.2f}, large_depeg_freq={sm['large_depeg_freq']:.4f}")

    moments_rows = [
        ("baseline_mean_close",       targets.baseline_mean_close,       bm["mean_p_sec"]),
        ("baseline_std_close",        targets.baseline_std_close,        bm["std_p_sec"]),
        ("baseline_large_depeg_freq", targets.baseline_large_depeg_freq, bm["large_depeg_freq"]),
        ("stress_min_close",          targets.stress_min_close,          sm["min_p_sec"]),
        ("stress_mean_abs_depeg_bps", targets.stress_mean_abs_depeg_bps, sm["mean_abs_depeg_bps"]),
        ("stress_large_depeg_freq",   targets.stress_large_depeg_freq,   sm["large_depeg_freq"]),
    ]

    manifest = {
        "calibration_run": stamp,
        "phi_star": phi_star,
        "loss": float(main_res.fun),
        "loss_warmup": float(warm_res.fun),
        "loss_template": 18152.85,
        "warmup_n_draws": 100,
        "warmup_maxiter": 20,
        "warmup_elapsed_sec": float(warm_elapsed),
        "main_n_draws": 200,
        "main_maxiter": 60,
        "main_elapsed_sec": float(main_elapsed),
        "targets": targets.__dict__,
        "moments_at_optimum": moments_at_optimum,
        "moments_comparison": [
            {"name": n, "target": float(t), "model": float(m), "abs_err": float(abs(t - m)), "rel_err": float(abs(t - m) / max(abs(t), 1e-9))}
            for n, t, m in moments_rows
        ],
        "convergence_message": str(main_res.message),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with (out_dir / "phi_history.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pass", "iter", "t_sec", *PARAM_NAMES, "loss"])
        for i, (t, phi, loss) in enumerate(warm_hist):
            w.writerow(["warm", i, t, *phi, loss])
        for i, (t, phi, loss) in enumerate(main_hist):
            w.writerow(["main", i, t, *phi, loss])

    with (out_dir / "moments_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["moment", "target", "model", "abs_err", "rel_err"])
        for n, t, m in moments_rows:
            w.writerow([n, t, m, abs(t - m), abs(t - m) / max(abs(t), 1e-9)])

    print(f"wrote manifest, phi_history, moments_comparison to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
