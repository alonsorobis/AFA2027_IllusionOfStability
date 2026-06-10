"""Background runner for USDT-specific calibration."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from simulation.stablecoin_ms.usdt_calibration import (
    SIMPLE_PARAM_NAMES,
    USDTTargets,
    usdt_loss,
    usdt_moments,
    risk_components_usdt,
    simple_bounds_vector,
)

ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out_dir = Path("data") / "processed" / f"usdt_calibration_{ts}"
out_dir.mkdir(parents=True, exist_ok=True)
print(f"out_dir = {out_dir}", flush=True)

targets = USDTTargets.from_json()

# Warm-start from USDC phi* and adjust theta_stress, tau_stress for USDT's milder stress
usdc_manifest = json.loads(Path("data/processed/simple_calibration_20260602T092829Z/manifest.json").read_text())
usdc_phi = usdc_manifest["phi_star"]
phi0 = np.array([
    usdc_phi["sigma"],
    usdc_phi["psi"],
    usdc_phi["nu"],
    usdc_phi["mu_q"],
    usdc_phi["zeta"],
    0.7,    # theta_stress closer to par for USDT mild event
    20.0,   # tau_stress higher (tighter prior) for USDT mild event
])

bounds = simple_bounds_vector()

def clipped(x):
    return np.array([max(bounds[i][0], min(bounds[i][1], x[i])) for i in range(len(x))])

print("--- Warmup N=100 maxiter=30 ---", flush=True)
t0 = time.time()
res_warm = minimize(
    lambda x: usdt_loss(clipped(x), targets, n_draws=100, seed=42),
    phi0,
    method="Nelder-Mead",
    options={"maxiter": 30, "xatol": 0.01, "fatol": 0.05, "adaptive": True},
)
print(f"warmup: {(time.time()-t0)/60:.2f} min, loss={res_warm.fun:.4f}", flush=True)

print("--- Main N=300 maxiter=80 ---", flush=True)
t0 = time.time()
res_main = minimize(
    lambda x: usdt_loss(clipped(x), targets, n_draws=300, seed=42),
    res_warm.x,
    method="Nelder-Mead",
    options={"maxiter": 80, "xatol": 0.005, "fatol": 0.02, "adaptive": True},
)
print(f"main: {(time.time()-t0)/60:.2f} min, loss={res_main.fun:.4f}", flush=True)

phi_star = clipped(res_main.x)
print(f"\nphi* = {dict(zip(SIMPLE_PARAM_NAMES, phi_star.round(4).tolist()))}", flush=True)

mom_star = usdt_moments(phi_star, n_draws=500, seed=42, threshold=targets.p_threshold)
print("\nMoments fit:")
for name, m in mom_star.items():
    target_val = getattr(targets, name)
    err = abs(m - target_val)
    print(f"  {name:30s} model {m:7.5f}  target {target_val:7.5f}  err {err:7.5f}", flush=True)

rc = risk_components_usdt(phi_star, n_draws=500, seed=42)
print("\nRisk components at phi*:")
for k, v in rc.items():
    print(f"  {k}: {v}", flush=True)

P_STRESS = 96.0 / 8856.0
total_bps = rc["counterparty_loss_bps"] + (1-P_STRESS)*rc["depeg_loss_baseline_bps"] + P_STRESS*rc["depeg_loss_stress_bps"]
print(f"\nTotal weighted risk premium at p_stress={P_STRESS:.4f}: {total_bps:.2f} bps", flush=True)

manifest = {
    "run": ts,
    "phi_star": dict(zip(SIMPLE_PARAM_NAMES, phi_star.tolist())),
    "theta_baseline_fixed": 1.0,
    "tau_baseline_fixed": 400.0,
    "USDT_hazard": 0.02,
    "USDT_lgd": 0.30,
    "loss_warmup": float(res_warm.fun),
    "loss_main": float(res_main.fun),
    "main_walltime_min": float((time.time()-t0)/60),
    "moments_at_optimum": mom_star,
    "risk_components": rc,
    "targets": targets.__dict__,
    "total_bps": float(total_bps),
    "p_stress": P_STRESS,
}
(out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"\nwrote {out_dir}/manifest.json", flush=True)
