"""SANDBOX (not for the paper): the coupling wedge.

Compare the model's coupled premium against a decoupled counterfactual where
the counterparty hazard h does NOT enter the conversion decision / secondary
price. The depeg components are recomputed with h toggled on/off; the standalone
counterparty term (h*xi) is identical in both worlds, so it cancels in the wedge.

    wedge = (1-p_s)*[depeg_b(h>0) - depeg_b(0)] + p_s*[depeg_s(h>0) - depeg_s(0)]
"""
import sys
from pathlib import Path
from dataclasses import replace
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "simulation"))
from stablecoin_ms.simple_calibration import build_scenario
from stablecoin_ms.montecarlo import run_scenario

# phi* neighbourhood (simple 7-param model), from the saved calibration columns
phi = np.array([0.2038, 0.2632, 1.8034, 0.0491, 0.4885, 0.2122, 10.055])
P_S = 0.0108          # stress probability (paper)
H, XI = 0.01, 0.20    # USDC counterparty: hazard, LGD
N = 1500

def depeg_bps(regime, h, seed):
    sc = build_scenario(f"x_{regime}_{h}", phi, regime, n_draws=N, seed=seed)
    sc = replace(sc, issuer=replace(sc.issuer, h=h, xi=XI))  # toggle h; fix xi=0.20 (USDC)
    draws = run_scenario(sc)
    p = np.array([d.secondary_price for d in draws])
    rate = np.array([d.redemption_rate["retail"] for d in draws])
    return float(np.mean(rate * (1.0 - p)) * 1e4), float(rate.mean()), float(p.mean())

cp = H * XI * 1e4   # standalone counterparty, identical in both worlds
rows = {}
for label, h in [("COUPLED   (h=0.01 in price+decision)", H),
                 ("DECOUPLED (h=0; counterparty added separately)", 0.0)]:
    db, rb, pb = depeg_bps("baseline", h, seed=42)
    ds, rs, ps_ = depeg_bps("stress", h, seed=84)
    Pi = cp + (1 - P_S) * db + P_S * ds
    rows[label] = (db, ds, Pi, rb, rs, pb, ps_)
    print(f"{label}")
    print(f"   counterparty={cp:5.1f}  depeg_b={db:6.2f}  depeg_s={ds:7.2f}  ->  Pi={Pi:6.2f} bps"
          f"   [rate_b={rb:.3f} rate_s={rs:.3f} p_b={pb:.4f} p_s={ps_:.4f}]")

cdb, cds, cPi = rows[list(rows)[0]][:3]
ddb, dds, dPi = rows[list(rows)[1]][:3]
wedge = (1 - P_S) * (cdb - ddb) + P_S * (cds - dds)
print("-" * 70)
print(f"Pi coupled   = {cPi:6.2f} bps")
print(f"Pi decoupled = {dPi:6.2f} bps")
print(f"COUPLING WEDGE = {cPi - dPi:6.2f} bps  ({100*(cPi-dPi)/cPi:.1f}% of coupled premium)")
print(f"  mechanical markdown reference  xi*h = {XI*H*1e4:.1f} bps on price")
print(f"  baseline depeg delta = {cdb-ddb:.2f} bps; stress depeg delta = {cds-dds:.2f} bps")
