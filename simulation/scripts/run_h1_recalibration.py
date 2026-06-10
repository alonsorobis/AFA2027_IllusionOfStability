"""Recalibrate the corrected model (counterparty out of the price, in V_H),
comparing the constant-hazard spec (h1=0) against the state-dependent spec
h(theta)=min(1, h0 + h1*max(0,1-theta)), for USDC and USDT.

Reports, per (asset, spec): final loss, phi*, the risk-premium decomposition
(counterparty / baseline depeg / stress depeg / total at p_s) and, for the
state-dependent spec, the coupling wedge = Pi(h1*) - Pi(h1=0 at the same phi*).
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stablecoin_ms.simple_calibration import (
    simple_loss, risk_components_at, USDCTargets, simple_bounds_vector)
from stablecoin_ms.usdt_calibration import (
    usdt_loss, risk_components_usdt, USDTTargets)

P_S = 0.0108
BOUNDS8 = list(simple_bounds_vector())            # 8 bounds (last is h1)
LO = np.array([lo for lo, _ in BOUNDS8]); HI = np.array([hi for _, hi in BOUNDS8])

def premium(comp):
    cp = comp["counterparty_loss_bps"]; db = comp["depeg_loss_baseline_bps"]; ds = comp["depeg_loss_stress_bps"]
    return cp + (1 - P_S) * db + P_S * ds, cp, db, ds

def calibrate(loss_fn, targets, ndim, x0, n_warm=60, n_main=150, mi_warm=25, mi_main=60):
    lo, hi = LO[:ndim], HI[:ndim]
    def obj(phi, n):
        return loss_fn(np.clip(phi, lo, hi), targets, n_draws=n)
    w = minimize(lambda p: obj(p, n_warm), np.array(x0[:ndim], float),
                 method="Nelder-Mead", options={"maxiter": mi_warm, "xatol": 1e-3, "fatol": 1e-3})
    m = minimize(lambda p: obj(p, n_main), w.x,
                 method="Nelder-Mead", options={"maxiter": mi_main, "xatol": 1e-3, "fatol": 1e-3})
    return np.clip(m.x, lo, hi), float(m.fun)

X0 = [0.20, 0.26, 1.8, 0.05, 0.49, 0.21, 10.0, 0.2]   # last entry = h1 start
results = {}

for asset, loss_fn, risk_fn, Targets in [
    ("USDC", simple_loss, risk_components_at, USDCTargets),
    ("USDT", usdt_loss,   risk_components_usdt, USDTTargets),
]:
    tg = Targets.from_json()
    for spec, ndim in [("constant_h1=0", 7), ("state_dependent_h(theta)", 8)]:
        t0 = time.time()
        phi, loss = calibrate(loss_fn, tg, ndim, X0)
        comp = risk_fn(phi, n_draws=800)
        Pi, cp, db, ds = premium(comp)
        rec = {"loss": loss, "phi": [float(x) for x in phi],
               "counterparty": cp, "depeg_b": db, "depeg_s": ds, "Pi": Pi,
               "elapsed_min": (time.time() - t0) / 60}
        if ndim == 8:
            phi0 = phi.copy(); phi0[7] = 0.0     # same phi*, switch coupling off
            comp0 = risk_fn(phi0, n_draws=800)
            Pi0, *_ = premium(comp0)
            rec["h1"] = float(phi[7]); rec["Pi_h1_off"] = Pi0; rec["coupling_wedge"] = Pi - Pi0
        results[f"{asset} | {spec}"] = rec
        print(f"=== {asset} | {spec} ===")
        print(f"   loss={loss:.4f}  Pi={Pi:.2f} bps  (cp={cp:.1f} depeg_b={db:.2f} depeg_s={ds:.2f})  [{rec['elapsed_min']:.1f} min]")
        if ndim == 8:
            print(f"   h1={phi[7]:.3f}  coupling wedge={rec['coupling_wedge']:.2f} bps  (Pi_h1off={rec['Pi_h1_off']:.2f})")

out = ROOT.parent / "data" / "processed" / "h1_recalibration_results.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nWrote {out}")
print("\nSUMMARY (loss: lower=better fit)")
for k, r in results.items():
    extra = f"  wedge={r['coupling_wedge']:.2f}bps h1={r['h1']:.3f}" if "coupling_wedge" in r else ""
    print(f"  {k:38s} loss={r['loss']:8.3f}  Pi={r['Pi']:6.2f}bps{extra}")
