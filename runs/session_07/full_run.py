"""Session 07 — Step 3: full calibration run with warm-start.

Loads the warm-start phi vector produced by `warmup_run.py`, then invokes
scipy.optimize.minimize(Nelder-Mead) directly with N=200 draws, maxiter=60,
recording phi at each iteration via a callback. Saves:
- manifest.json
- phi_history.csv
- moments_comparison.csv
in `data/processed/usdc_calibration_<UTC_TIMESTAMP>/`.

The script does NOT modify the simulation package. It mirrors the structure
of `calibrate_usdc` but uses a custom x0 (the warm-start) and exposes the
callback hook.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "simulation"))

from stablecoin_ms.calibration import (  # noqa: E402
    PARAM_NAMES,
    USDCMarch2023Targets,
    default_bounds,
    model_moments_pair,
    template_scenario,
    usdc_loss,
)


def find_latest_warmup() -> Path:
    proc = PROJECT_ROOT / "data" / "processed"
    candidates = sorted(proc.glob("usdc_calibration_warmup_*.json"))
    if not candidates:
        raise FileNotFoundError("No warmup manifest found in data/processed/")
    return candidates[-1]


def main() -> int:
    warmup_path = find_latest_warmup()
    print(f"Loading warm-start from {warmup_path}")
    warmup = json.loads(warmup_path.read_text(encoding="utf-8"))
    x0 = np.array([warmup["phi_star"][n] for n in PARAM_NAMES], dtype=float)
    print(f"Warm-start loss reported: {warmup['loss']:.4f}")
    print("Warm-start phi:")
    for name, v in zip(PARAM_NAMES, x0):
        print(f"  {name:25s} = {v:.6f}")

    targets = USDCMarch2023Targets.from_json()

    seed = 42
    n_draws_eval = 200
    maxiter = 60

    base_tmpl = template_scenario("usdc_calib_baseline", n_draws_eval, seed)
    stress_tmpl = template_scenario("usdc_calib_stress", n_draws_eval, seed + 1)
    bounds = default_bounds()

    phi_history: list[tuple[int, float, list[float]]] = []
    eval_counter = {"n": 0, "best_loss": float("inf"), "best_phi": None}

    def fn(phi: np.ndarray) -> float:
        clipped = np.array([np.clip(v, lo, hi) for v, (lo, hi) in zip(phi, bounds)])
        loss = usdc_loss(clipped, targets, base_tmpl, stress_tmpl)
        eval_counter["n"] += 1
        if loss < eval_counter["best_loss"]:
            eval_counter["best_loss"] = loss
            eval_counter["best_phi"] = clipped.copy()
        if eval_counter["n"] % 5 == 0:
            print(
                f"  eval {eval_counter['n']:3d}  loss={loss:10.3f}  "
                f"best={eval_counter['best_loss']:10.3f}"
            )
        return float(loss)

    iter_counter = {"k": 0}

    def cb(xk: np.ndarray) -> None:
        iter_counter["k"] += 1
        clipped = np.array([np.clip(v, lo, hi) for v, (lo, hi) in zip(xk, bounds)])
        loss_here = usdc_loss(clipped, targets, base_tmpl, stress_tmpl)
        phi_history.append((iter_counter["k"], loss_here, list(clipped)))
        print(f"  iter {iter_counter['k']:3d}  loss={loss_here:10.3f}")

    print(f"\nStarting full calibration: N={n_draws_eval}, maxiter={maxiter}, seed={seed}")
    t0 = time.time()
    result = minimize(
        fn,
        x0,
        method="Nelder-Mead",
        options={"maxiter": maxiter, "xatol": 1e-3, "fatol": 1e-3, "disp": True},
        callback=cb,
    )
    elapsed = time.time() - t0
    print(f"\nFull calibration finished in {elapsed:.1f} s (n_eval={eval_counter['n']})")

    # Recover the best phi seen (Nelder-Mead's result.x is best at termination)
    phi_final = np.array(
        [np.clip(v, lo, hi) for v, (lo, hi) in zip(result.x, bounds)]
    )
    loss_final = usdc_loss(phi_final, targets, base_tmpl, stress_tmpl)
    print(f"Final loss at result.x: {loss_final:.4f}")

    phi_star = dict(zip(PARAM_NAMES, [float(v) for v in phi_final]))
    print("Calibrated phi:")
    for name in PARAM_NAMES:
        print(f"  {name:25s} = {phi_star[name]:.6f}")

    base_m, stress_m = model_moments_pair(phi_final, base_tmpl, stress_tmpl)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = PROJECT_ROOT / "data" / "processed" / f"usdc_calibration_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    target_dict = {
        "baseline_mean_close": targets.baseline_mean_close,
        "baseline_std_close": targets.baseline_std_close,
        "baseline_large_depeg_freq": targets.baseline_large_depeg_freq,
        "stress_min_close": targets.stress_min_close,
        "stress_mean_abs_depeg_bps": targets.stress_mean_abs_depeg_bps,
        "stress_large_depeg_freq": targets.stress_large_depeg_freq,
    }

    manifest = {
        "session": "07",
        "stage": "full",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "n_draws_eval": n_draws_eval,
        "maxiter": maxiter,
        "walltime_seconds": elapsed,
        "n_eval": eval_counter["n"],
        "warm_start_source": str(warmup_path.relative_to(PROJECT_ROOT)),
        "warm_start_loss": warmup["loss"],
        "loss": loss_final,
        "phi_star": phi_star,
        "targets": target_dict,
        "model_moments_baseline": base_m,
        "model_moments_stress": stress_m,
        "nelder_mead_result": {
            "success": bool(result.success),
            "status": int(result.status),
            "message": str(result.message),
            "nit": int(result.nit),
            "nfev": int(result.nfev),
            "fun": float(result.fun),
        },
    }

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    # phi_history.csv: one row per Nelder-Mead iteration
    history_path = out_dir / "phi_history.csv"
    with history_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["iteration", "loss", *PARAM_NAMES])
        for k, loss_here, phi_vec in phi_history:
            w.writerow([k, loss_here, *phi_vec])

    # moments_comparison.csv: six rows, target vs model
    moments_path = out_dir / "moments_comparison.csv"
    rows = [
        ("baseline_mean_close", target_dict["baseline_mean_close"], base_m["mean_p_sec"]),
        ("baseline_std_close", target_dict["baseline_std_close"], base_m["std_p_sec"]),
        (
            "baseline_large_depeg_freq",
            target_dict["baseline_large_depeg_freq"],
            base_m["large_depeg_freq"],
        ),
        ("stress_min_close", target_dict["stress_min_close"], stress_m["min_p_sec"]),
        (
            "stress_mean_abs_depeg_bps",
            target_dict["stress_mean_abs_depeg_bps"],
            stress_m["mean_abs_depeg_bps"],
        ),
        (
            "stress_large_depeg_freq",
            target_dict["stress_large_depeg_freq"],
            stress_m["large_depeg_freq"],
        ),
    ]
    with moments_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["moment", "target", "model", "abs_error", "rel_error"])
        for name, tgt, mdl in rows:
            abs_err = mdl - tgt
            rel_err = abs_err / tgt if tgt != 0 else float("nan")
            w.writerow([name, tgt, mdl, abs_err, rel_err])

    print(f"\nWrote artefacts under {out_dir}")
    print(f"  manifest.json")
    print(f"  phi_history.csv ({len(phi_history)} rows)")
    print(f"  moments_comparison.csv")

    # Sanity-check summary
    print("\n--- Sanity check ---")
    print(f"Final loss: {loss_final:.4f}")
    print("Per-moment errors:")
    for name, tgt, mdl in rows:
        abs_err = mdl - tgt
        rel_err = abs_err / tgt if tgt != 0 else float("inf")
        print(
            f"  {name:30s} target={tgt:>10.6f}  model={mdl:>10.6f}  "
            f"abs={abs_err:>+10.6f}  rel={rel_err*100:>+8.1f}%"
        )

    # Targets within 10%
    within = []
    outside = []
    for name, tgt, mdl in rows:
        if tgt == 0:
            # use a 5 bps absolute tolerance for the zero target
            if abs(mdl - tgt) < 5e-4:
                within.append(name)
            else:
                outside.append(name)
        else:
            if abs((mdl - tgt) / tgt) <= 0.10:
                within.append(name)
            else:
                outside.append(name)
    print(f"\nWithin 10% (or 5bps for zero target): {within}")
    print(f"Outside:                                {outside}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
