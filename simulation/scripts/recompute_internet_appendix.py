"""Recompute internet-appendix robustness grids at the corrected (counterparty-in-V_H) phi*.

Outputs data/processed/internet_appendix_corrected.json:
  - two_class: class-P / class-M premia and stress trough, USDC and USDT
  - mu_tau_grid: 3x3 (mu_s, tau_s) sweep of Pi and ell_Ds at USDC phi*
  - tau_b_grid: Pi at tau_b in {100, 400, 1600}, USDC phi*
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stablecoin_ms.montecarlo import run_scenario
from stablecoin_ms.scenario import (
    ClassParameters,
    IssuerParameters,
    RailParameters,
    Scenario,
    SecondaryParameters,
    ThetaPrior,
)

PHI_USDC = {"sigma": 0.19368812639123134, "psi": 0.27459061603325163, "nu": 1.740548754749086,
            "mu_q": 0.052691159616821664, "zeta": 0.507352543351488,
            "theta_stress": 0.21247327324753199, "tau_stress": 9.881810438888362}
PHI_USDT = {"sigma": 0.2366794100547257, "psi": 0.10806092952834376, "nu": 4.0,
            "mu_q": 0.02191403141624647, "zeta": 0.4527849028439752,
            "theta_stress": 0.23075705814896785, "tau_stress": 7.980707184433772}

THETA_BASELINE = 1.0
TAU_BASELINE = 400.0
P_STRESS = 0.0108
N_DRAWS = 300
SEED = 44


def _scenario(asset, phi, alpha, sigma_ratio_M, regime, tau_b=TAU_BASELINE,
              theta_s=None, tau_s=None, n_draws=N_DRAWS, seed=SEED):
    sigma_P = float(phi["sigma"])
    sigma_M = sigma_ratio_M * sigma_P
    classes = ClassParameters(
        pi={"retail": 1.0 - alpha, "wholesale": 0.0, "cross_border": 0.0, "market_maker": alpha},
        B={"retail": 1.0, "wholesale": 1.0, "cross_border": 1.0, "market_maker": 1.0},
        sigma={"retail": sigma_P, "wholesale": sigma_P, "cross_border": sigma_P, "market_maker": sigma_M},
        omega={"retail": 0.01, "wholesale": 0.01, "cross_border": 0.01, "market_maker": 0.0},
        cq={"retail": 0.05, "wholesale": 0.05, "cross_border": 0.05, "market_maker": 0.05},
    )
    secondary = SecondaryParameters(M=2.0, psi=float(phi["psi"]), nu=float(phi["nu"]),
                                    mu_q=float(phi["mu_q"]), zeta=float(phi["zeta"]), p_underbar=0.50)
    issuer = (IssuerParameters(R=0.6, A=0.3, h=0.01, xi=0.20) if asset == "USDC"
              else IssuerParameters(R=0.5, A=0.4, h=0.02, xi=0.30))
    if regime == "baseline":
        theta_prior = ThetaPrior(mean=THETA_BASELINE, tau=tau_b)
    else:
        theta_prior = ThetaPrior(mean=theta_s if theta_s is not None else float(phi["theta_stress"]),
                                 tau=tau_s if tau_s is not None else float(phi["tau_stress"]))
    return Scenario(name=f"{asset}_{regime}", n_agents=1000, n_draws=n_draws, seed=seed,
                    classes=classes, issuer=issuer, secondary=secondary,
                    rails=RailParameters(q={"retail": 0.10, "wholesale": 0.10,
                                            "cross_border": 0.10, "market_maker": 0.10}),
                    theta_prior=theta_prior)


def two_class_cell(asset, phi, alpha, sigma_ratio_M):
    base = run_scenario(_scenario(asset, phi, alpha, sigma_ratio_M, "baseline", seed=SEED))
    stress = run_scenario(_scenario(asset, phi, alpha, sigma_ratio_M, "stress", seed=SEED + 1))
    p_b = np.array([d.secondary_price for d in base])
    p_s = np.array([d.secondary_price for d in stress])
    h, xi = (0.01, 0.20) if asset == "USDC" else (0.02, 0.30)
    ell_C = h * xi * 1e4

    def decomp(key):
        rb = np.array([d.redemption_rate[key] for d in base])
        rs = np.array([d.redemption_rate[key] for d in stress])
        ell_Db = float(np.mean(rb * (1.0 - p_b)) * 1e4)
        ell_Ds = float(np.mean(rs * (1.0 - p_s)) * 1e4)
        return ell_C + (1 - P_STRESS) * ell_Db + P_STRESS * ell_Ds

    return {"alpha": alpha, "sigma_ratio_M": sigma_ratio_M,
            "P_total": decomp("retail"), "M_total": decomp("market_maker"),
            "trough": float(p_s.min())}


def pi_at(phi, asset, tau_b=TAU_BASELINE, theta_s=None, tau_s=None):
    base = run_scenario(_scenario(asset, phi, 0.0, 1.0, "baseline", tau_b=tau_b, seed=SEED))
    stress = run_scenario(_scenario(asset, phi, 0.0, 1.0, "stress", theta_s=theta_s, tau_s=tau_s, seed=SEED + 1))
    p_b = np.array([d.secondary_price for d in base])
    p_s = np.array([d.secondary_price for d in stress])
    rb = np.array([d.redemption_rate["retail"] for d in base])
    rs = np.array([d.redemption_rate["retail"] for d in stress])
    h, xi = (0.01, 0.20)
    ell_C = h * xi * 1e4
    ell_Db = float(np.mean(rb * (1.0 - p_b)) * 1e4)
    ell_Ds = float(np.mean(rs * (1.0 - p_s)) * 1e4)
    Pi = ell_C + (1 - P_STRESS) * ell_Db + P_STRESS * ell_Ds
    return {"Pi": Pi, "ell_Db": ell_Db, "ell_Ds": ell_Ds}


def main():
    out = {"two_class": {"USDC": [], "USDT": []}, "mu_tau_grid": [], "tau_b_grid": []}

    for alpha in [0.10, 0.20, 0.30]:
        out["two_class"]["USDC"].append(two_class_cell("USDC", PHI_USDC, alpha, 1.0))
        print("USDC tc", alpha, out["two_class"]["USDC"][-1])
    out["two_class"]["USDC"].append({**two_class_cell("USDC", PHI_USDC, 0.20, 2.0), "label": "sigma_M_2x"})
    for alpha in [0.025, 0.075, 0.125]:
        out["two_class"]["USDT"].append(two_class_cell("USDT", PHI_USDT, alpha, 1.0))
        print("USDT tc", alpha, out["two_class"]["USDT"][-1])
    out["two_class"]["USDT"].append({**two_class_cell("USDT", PHI_USDT, 0.075, 2.0), "label": "sigma_M_2x"})

    mu_grid = [-1.0, PHI_USDC["theta_stress"], 1.5]
    tau_grid = [1.0, PHI_USDC["tau_stress"], 50.0]
    for mu in mu_grid:
        for tau in tau_grid:
            r = pi_at(PHI_USDC, "USDC", theta_s=mu, tau_s=tau)
            out["mu_tau_grid"].append({"mu_s": mu, "tau_s": tau, "Pi": r["Pi"], "ell_Ds": r["ell_Ds"]})
            print("mu_tau", round(mu, 3), round(tau, 2), round(r["Pi"], 2), round(r["ell_Ds"], 1))

    for tb in [100.0, 400.0, 1600.0]:
        r = pi_at(PHI_USDC, "USDC", tau_b=tb)
        out["tau_b_grid"].append({"tau_b": tb, "ell_Db": r["ell_Db"], "ell_Ds": r["ell_Ds"], "Pi": r["Pi"]})
        print("tau_b", tb, round(r["Pi"], 2))

    out_path = ROOT.parent / "data" / "processed" / "internet_appendix_corrected.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote", out_path)


if __name__ == "__main__":
    main()
