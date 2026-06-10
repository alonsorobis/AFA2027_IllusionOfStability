"""Reserve comparative statics for the referee response (P4).

Proposition 2 states dD*/dR >= 0 (more reserves -> weakly more conversion).
The policy-relevant object is the premium: this script verifies numerically
that dPi_risk/dR < 0 at the calibrated parameters, i.e. deeper liquid
reserves LOWER the expected-loss adjustment even though they weakly raise
the equilibrium conversion mass. Writes data/processed/reserve_static.json.
"""
from __future__ import annotations
import json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stablecoin_ms.simple_calibration import build_scenario
from stablecoin_ms.usdt_calibration import build_scenario_usdt
from stablecoin_ms.montecarlo import run_scenario

PROOT = ROOT.parent
P_S = 0.0108
res = json.loads((PROOT / "data" / "processed" / "h1_recalibration_results.json").read_text())
PHI = {"USDC": np.array(res["USDC | constant_h1=0"]["phi"]),
       "USDT": np.array(res["USDT | constant_h1=0"]["phi"])}
BUILD = {"USDC": build_scenario, "USDT": build_scenario_usdt}
H0 = {"USDC": 0.01, "USDT": 0.02}
XI0 = {"USDC": 0.20, "USDT": 0.30}
R_GRID = [0.40, 0.50, 0.60, 0.70, 0.80]
N = 800

out = {}
for a in ("USDC", "USDT"):
    rows = []
    for R in R_GRID:
        vals = {}
        for regime, seed in (("baseline", 42), ("stress", 84)):
            sc = BUILD[a](f"rs_{a}_{regime}_{R}", PHI[a], regime, n_draws=N, seed=seed)
            sc = replace(sc, issuer=replace(sc.issuer, R=R))
            d = run_scenario(sc)
            p = np.array([x.secondary_price for x in d])
            r = np.array([x.redemption_rate["retail"] for x in d])
            vals[regime] = {"depeg_bps": float(np.mean(r * (1 - p)) * 1e4),
                            "D_mean": float(r.mean()),
                            "p_mean": float(p.mean())}
        cp = H0[a] * XI0[a] * 1e4
        Pi = cp + (1 - P_S) * vals["baseline"]["depeg_bps"] + P_S * vals["stress"]["depeg_bps"]
        rows.append({"R": R, "Pi": Pi,
                     "depeg_b": vals["baseline"]["depeg_bps"],
                     "depeg_s": vals["stress"]["depeg_bps"],
                     "D_b": vals["baseline"]["D_mean"], "D_s": vals["stress"]["D_mean"],
                     "p_b": vals["baseline"]["p_mean"], "p_s": vals["stress"]["p_mean"]})
        print(f"{a} R={R:.2f}: Pi={Pi:7.2f}  depeg_b={rows[-1]['depeg_b']:7.2f}  "
              f"depeg_s={rows[-1]['depeg_s']:7.2f}  D_b={rows[-1]['D_b']:.4f}  D_s={rows[-1]['D_s']:.4f}")
    out[a] = rows

(PROOT / "data" / "processed" / "reserve_static.json").write_text(json.dumps(out, indent=2))
print("Wrote reserve_static.json")
