"""Two-class robustness for the AFA paper.

Reuses the K-class fixed-point solver in stablecoin_ms.fixed_point. Builds
scenarios where the population is split between a payment-holder class (mapped
onto the existing "retail" key) and a market-maker class (mapped onto the
existing "market_maker" key). The other two class keys are kept at zero mass.

Inputs: calibrated phi* for USDC and USDT from the existing manifests.
Output: data/processed/two_class_robustness.json with class-P and class-M
risk components in basis points for each (asset, alpha) cell.

The class-P premium is the headline for the use-case comparison; the class-M
premium is reported as a separate object that does not enter the payments
cost calculation.
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USDC_MANIFEST = PROJECT_ROOT / "data" / "processed" / "simple_calibration_20260602T092829Z" / "manifest.json"
USDT_MANIFEST = PROJECT_ROOT / "data" / "processed" / "usdt_calibration_20260602T102432Z" / "manifest.json"

THETA_BASELINE = 1.0
TAU_BASELINE = 400.0

# Stress regime weight: empirical fraction of stress hours per the USDC March
# 2023 calibration window (used as the canonical reference; USDT uses 0.0108
# as in the published table for comparability).
P_STRESS_USDC = 0.0108
P_STRESS_USDT = 0.0108


def _build_scenario(asset: str, phi: dict, alpha: float, sigma_ratio_M: float,
                     regime: str, n_draws: int, seed: int) -> Scenario:
    sigma_P = float(phi["sigma"])
    sigma_M = sigma_ratio_M * sigma_P

    classes = ClassParameters(
        pi={
            "retail": 1.0 - alpha,
            "wholesale": 0.0,
            "cross_border": 0.0,
            "market_maker": alpha,
        },
        B={"retail": 1.0, "wholesale": 1.0, "cross_border": 1.0, "market_maker": 1.0},
        sigma={
            "retail": sigma_P,
            "wholesale": sigma_P,
            "cross_border": sigma_P,
            "market_maker": sigma_M,
        },
        omega={
            "retail": 0.01,
            "wholesale": 0.01,
            "cross_border": 0.01,
            "market_maker": 0.0,
        },
        cq={
            "retail": 0.05,
            "wholesale": 0.05,
            "cross_border": 0.05,
            "market_maker": 0.05,
        },
    )
    secondary = SecondaryParameters(
        M=2.0,
        psi=float(phi["psi"]),
        nu=float(phi["nu"]),
        mu_q=float(phi["mu_q"]),
        zeta=float(phi["zeta"]),
        p_underbar=0.50,
    )
    if asset == "USDC":
        issuer = IssuerParameters(R=0.6, A=0.3, h=0.01, xi=0.20)
    elif asset == "USDT":
        issuer = IssuerParameters(R=0.5, A=0.4, h=0.02, xi=0.30)
    else:
        raise ValueError(f"asset must be USDC or USDT, got {asset!r}")

    if regime == "baseline":
        theta_prior = ThetaPrior(mean=THETA_BASELINE, tau=TAU_BASELINE)
    elif regime == "stress":
        theta_prior = ThetaPrior(mean=float(phi["theta_stress"]),
                                  tau=float(phi["tau_stress"]))
    else:
        raise ValueError(f"regime must be baseline or stress, got {regime!r}")

    return Scenario(
        name=f"{asset}_tc_alpha{alpha:.3f}_{regime}",
        n_agents=1000,
        n_draws=n_draws,
        seed=seed,
        classes=classes,
        issuer=issuer,
        secondary=secondary,
        rails=RailParameters(q={"retail": 0.10, "wholesale": 0.10,
                                "cross_border": 0.10, "market_maker": 0.10}),
        theta_prior=theta_prior,
    )


def risk_components(asset: str, phi: dict, alpha: float, sigma_ratio_M: float,
                     p_stress: float, n_draws: int = 300, seed: int = 42) -> dict:
    """Class-decomposed risk components in basis points."""
    base = _build_scenario(asset, phi, alpha, sigma_ratio_M, "baseline",
                            n_draws=n_draws, seed=seed)
    stress = _build_scenario(asset, phi, alpha, sigma_ratio_M, "stress",
                              n_draws=n_draws, seed=seed + 1)

    base_draws = run_scenario(base)
    stress_draws = run_scenario(stress)

    p_base = np.array([d.secondary_price for d in base_draws])
    p_stress_arr = np.array([d.secondary_price for d in stress_draws])
    rate_base_P = np.array([d.redemption_rate["retail"] for d in base_draws])
    rate_stress_P = np.array([d.redemption_rate["retail"] for d in stress_draws])
    rate_base_M = np.array([d.redemption_rate["market_maker"] for d in base_draws])
    rate_stress_M = np.array([d.redemption_rate["market_maker"] for d in stress_draws])

    h = base.issuer.h
    xi = base.issuer.xi
    ell_C = h * xi * 1e4

    def decomp(rate_b, p_b, rate_s, p_s):
        ell_Db = float(np.mean(rate_b * (1.0 - p_b)) * 1e4)
        ell_Ds = float(np.mean(rate_s * (1.0 - p_s)) * 1e4)
        ell_Db_w = (1.0 - p_stress) * ell_Db
        ell_Ds_w = p_stress * ell_Ds
        total = ell_C + ell_Db_w + ell_Ds_w
        return {
            "ell_C": ell_C,
            "ell_Db": ell_Db,
            "ell_Ds": ell_Ds,
            "ell_Db_weighted": ell_Db_w,
            "ell_Ds_weighted": ell_Ds_w,
            "total": total,
        }

    return {
        "asset": asset,
        "alpha": alpha,
        "sigma_ratio_M": sigma_ratio_M,
        "p_stress": p_stress,
        "stress_min_close": float(p_stress_arr.min()),
        "stress_mean_close": float(p_stress_arr.mean()),
        "baseline_mean_close": float(p_base.mean()),
        "P": decomp(rate_base_P, p_base, rate_stress_P, p_stress_arr),
        "M": decomp(rate_base_M, p_base, rate_stress_M, p_stress_arr),
    }


def main():
    usdc_phi = json.loads(USDC_MANIFEST.read_text())["phi_star"]
    usdt_phi = json.loads(USDT_MANIFEST.read_text())["phi_star"]

    out = {"USDC": [], "USDT": []}

    print("Running USDC two-class grid (sigma_M = sigma_P)...")
    for alpha in [0.10, 0.20, 0.30]:
        r = risk_components("USDC", usdc_phi, alpha, sigma_ratio_M=1.0,
                            p_stress=P_STRESS_USDC, n_draws=300, seed=42)
        out["USDC"].append(r)
        print(f"  alpha={alpha:.3f}, sigmaM=1.0x: P_total={r['P']['total']:.2f} "
              f"M_total={r['M']['total']:.2f} "
              f"trough={r['stress_min_close']:.4f}")

    print("Running USDC two-class grid (sigma_M = 2 sigma_P)...")
    for alpha in [0.20]:
        r = risk_components("USDC", usdc_phi, alpha, sigma_ratio_M=2.0,
                            p_stress=P_STRESS_USDC, n_draws=300, seed=42)
        r["label"] = "sigma_M_2x"
        out["USDC"].append(r)
        print(f"  alpha={alpha:.3f}, sigmaM=2.0x: P_total={r['P']['total']:.2f} "
              f"M_total={r['M']['total']:.2f} "
              f"trough={r['stress_min_close']:.4f}")

    print("Running USDT two-class grid (sigma_M = sigma_P)...")
    for alpha in [0.025, 0.075, 0.125]:
        r = risk_components("USDT", usdt_phi, alpha, sigma_ratio_M=1.0,
                            p_stress=P_STRESS_USDT, n_draws=300, seed=42)
        out["USDT"].append(r)
        print(f"  alpha={alpha:.3f}, sigmaM=1.0x: P_total={r['P']['total']:.2f} "
              f"M_total={r['M']['total']:.2f} "
              f"trough={r['stress_min_close']:.4f}")

    print("Running USDT two-class grid (sigma_M = 2 sigma_P)...")
    for alpha in [0.075]:
        r = risk_components("USDT", usdt_phi, alpha, sigma_ratio_M=2.0,
                            p_stress=P_STRESS_USDT, n_draws=300, seed=42)
        r["label"] = "sigma_M_2x"
        out["USDT"].append(r)
        print(f"  alpha={alpha:.3f}, sigmaM=2.0x: P_total={r['P']['total']:.2f} "
              f"M_total={r['M']['total']:.2f} "
              f"trough={r['stress_min_close']:.4f}")

    out_path = PROJECT_ROOT / "data" / "processed" / "two_class_robustness.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
