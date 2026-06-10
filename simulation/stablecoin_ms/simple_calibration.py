"""One-class representative-holder calibration for the IJCB submission.

The K-class infrastructure in `calibration.py` and `joint_calibration.py` is
preserved for reference but is not the main object of the paper any more. The
methodological contribution is reduced to its essential role: extract the
risk-adjusted economics of a stablecoin payment given that a representative
holder faces a coordination problem at the redemption stage with two
stablecoin-specific risks (counterparty hazard $h$ and a depeg outcome
driven by the global game).

The free parameter vector has seven entries:

    free_params = (
        sigma,        # representative holder signal noise about reserve quality
        psi,          # secondary-market price-impact scale
        nu,           # secondary-market convexity
        mu_q,         # secondary-market congestion penalty (small here)
        zeta,         # secondary-market depth erosion
        theta_stress, # stress-regime fundamental mean
        tau_stress,   # stress-regime prior precision
    )

Two parameters are fixed externally on economic grounds: $\\theta_{baseline}=1.0$
by par-convertibility definition, and $\\tau_{baseline} = 400$ at a calibrated
reference value that keeps the baseline regime quasi-deterministic (the
exact value of $\\tau_{baseline}$ does not affect any moment in a regime
where the prior precision is already saturating).

Six price moments per asset (USDC March 2023 episode) discipline the seven
free parameters, with the system effectively exactly identified once we
acknowledge that $\\tau_{baseline}$ is irrelevant in the saturated baseline
regime. The model output drives the risk module used by the empirical
cost-benefit comparison against PIX, FedNow, SEPA Instant, UPI, BIS Nexus,
SWIFT correspondent and fintech remittance services.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Tuple

import numpy as np

from .montecarlo import aggregate_moments, run_scenario
from .scenario import (
    CLASS_KEYS,
    ClassParameters,
    IssuerParameters,
    RailParameters,
    Scenario,
    SecondaryParameters,
    ThetaPrior,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Externally fixed parameters
THETA_BASELINE = 1.0
TAU_BASELINE = 400.0    # saturated baseline regime; does not affect price moments


# Seven free parameters
SIMPLE_PARAM_NAMES = (
    "sigma",
    "psi",
    "nu",
    "mu_q",
    "zeta",
    "theta_stress",
    "tau_stress",
)


@dataclass(frozen=True)
class SimpleBounds:
    sigma: Tuple[float, float] = (0.05, 1.0)
    psi: Tuple[float, float] = (0.01, 5.0)
    nu: Tuple[float, float] = (1.0, 4.0)
    mu_q: Tuple[float, float] = (0.0, 0.5)
    zeta: Tuple[float, float] = (0.0, 5.0)
    theta_stress: Tuple[float, float] = (-1.0, 1.5)
    tau_stress: Tuple[float, float] = (1.0, 50.0)


def simple_bounds_vector() -> Tuple[Tuple[float, float], ...]:
    b = SimpleBounds()
    return (b.sigma, b.psi, b.nu, b.mu_q, b.zeta, b.theta_stress, b.tau_stress)


@dataclass(frozen=True)
class USDCTargets:
    baseline_mean_close: float
    baseline_std_close: float
    baseline_large_depeg_freq: float
    stress_min_close: float
    stress_mean_abs_depeg_bps: float
    stress_large_depeg_freq: float
    p_threshold: float = 0.975

    @classmethod
    def from_json(cls) -> "USDCTargets":
        path = PROJECT_ROOT / "data" / "processed" / "usdc_march2023_targets.json"
        d = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            baseline_mean_close=float(d["baseline_mean_close"]),
            baseline_std_close=float(d["baseline_std_close"]),
            baseline_large_depeg_freq=float(d["baseline_large_depeg_freq"]),
            stress_min_close=float(d["stress_min_close"]),
            stress_mean_abs_depeg_bps=float(d["stress_mean_abs_depeg_bps"]),
            stress_large_depeg_freq=float(d["stress_large_depeg_freq"]),
            p_threshold=float(d.get("p_threshold", 0.975)),
        )


def build_scenario(name: str, phi: np.ndarray, regime: str,
                    n_draws: int, seed: int) -> Scenario:
    """Build a single-class representative-holder scenario.

    The class structure of the underlying `Scenario` object is kept intact
    (it carries four class keys for historical reasons), but the population
    share is concentrated on a single representative class and the other
    three classes are inert. This produces a one-class fixed point.
    """
    sigma_val = float(phi[0])
    classes = ClassParameters(
        pi={"retail": 1.0, "wholesale": 0.0, "cross_border": 0.0, "market_maker": 0.0},
        B={"retail": 1.0, "wholesale": 1.0, "cross_border": 1.0, "market_maker": 1.0},
        sigma={"retail": sigma_val, "wholesale": sigma_val,
               "cross_border": sigma_val, "market_maker": sigma_val},
        omega={"retail": 0.01, "wholesale": 0.01,
               "cross_border": 0.01, "market_maker": 0.01},
        cq={"retail": 0.05, "wholesale": 0.05,
            "cross_border": 0.05, "market_maker": 0.05},
    )
    secondary = SecondaryParameters(
        M=2.0,
        psi=float(phi[1]),
        nu=float(phi[2]),
        mu_q=float(phi[3]),
        zeta=float(phi[4]),
        p_underbar=0.50,
    )
    if regime == "baseline":
        theta_prior = ThetaPrior(mean=THETA_BASELINE, tau=TAU_BASELINE)
    elif regime == "stress":
        theta_prior = ThetaPrior(mean=float(phi[5]), tau=float(phi[6]))
    else:
        raise ValueError(f"regime must be 'baseline' or 'stress', got {regime!r}")
    return Scenario(
        name=name,
        n_agents=1000,
        n_draws=n_draws,
        seed=seed,
        classes=classes,
        issuer=IssuerParameters(R=0.6, A=0.3, h=0.01, xi=0.20),
        secondary=secondary,
        rails=RailParameters(q={"retail": 0.10, "wholesale": 0.10,
                                  "cross_border": 0.10, "market_maker": 0.10}),
        theta_prior=theta_prior,
    )


def simple_moments(phi: np.ndarray, n_draws: int, seed: int) -> Dict[str, float]:
    """Return the six USDC-comparable price moments under the one-class model."""
    base_sc = build_scenario("simple_base", phi, "baseline", n_draws=n_draws, seed=seed)
    stress_sc = build_scenario("simple_str", phi, "stress", n_draws=n_draws, seed=seed + 1)
    bm = aggregate_moments(run_scenario(base_sc))
    sm = aggregate_moments(run_scenario(stress_sc))
    return {
        "baseline_mean_close": bm["mean_p_sec"],
        "baseline_std_close": bm["std_p_sec"],
        "baseline_large_depeg_freq": bm["large_depeg_freq"],
        "stress_min_close": sm["min_p_sec"],
        "stress_mean_abs_depeg_bps": sm["mean_abs_depeg_bps"],
        "stress_large_depeg_freq": sm["large_depeg_freq"],
    }


DEFAULT_WEIGHTS = {
    "baseline_mean_close": 100.0,
    "baseline_std_close": 1000.0,
    "baseline_large_depeg_freq": 50.0,
    "stress_min_close": 50.0,
    "stress_mean_abs_depeg_bps": 1.0,
    "stress_large_depeg_freq": 50.0,
}


def simple_loss(
    phi: np.ndarray,
    targets: USDCTargets,
    n_draws: int = 200,
    weights: Dict[str, float] | None = None,
    seed: int = 42,
) -> float:
    weights = weights or DEFAULT_WEIGHTS
    mom = simple_moments(phi, n_draws=n_draws, seed=seed)
    return float(sum(w * (mom[name] - getattr(targets, name)) ** 2
                     for name, w in weights.items()))


def risk_components_at(
    phi: np.ndarray,
    issuer_hazard: float = 0.01,
    issuer_lgd: float = 0.20,
    n_draws: int = 500,
    seed: int = 42,
) -> Dict[str, float]:
    """Decompose the stablecoin-specific risk components at the calibrated phi.

    Returns three numbers in basis points:
        counterparty_loss = issuer_hazard * issuer_lgd * 1e4
        depeg_loss_baseline = E[(1 - p_sec) * 1{redeem}] in baseline, in bps
        depeg_loss_stress = same in stress regime, in bps

    The two depeg numbers are the expected per-unit haircut on a converting
    holder, conditional on the regime. They are the model's empirical bite
    in the cost-benefit comparison against rails without these two risks.
    """
    base_sc = build_scenario("risk_base", phi, "baseline", n_draws=n_draws, seed=seed)
    stress_sc = build_scenario("risk_str", phi, "stress", n_draws=n_draws, seed=seed + 1)
    base_draws = run_scenario(base_sc)
    stress_draws = run_scenario(stress_sc)
    p_base = np.array([d.secondary_price for d in base_draws])
    p_stress = np.array([d.secondary_price for d in stress_draws])
    rate_base = np.array([d.redemption_rate["retail"] for d in base_draws])
    rate_stress = np.array([d.redemption_rate["retail"] for d in stress_draws])
    return {
        "counterparty_loss_bps": float(issuer_hazard * issuer_lgd * 1e4),
        "depeg_loss_baseline_bps": float(np.mean(rate_base * (1.0 - p_base)) * 1e4),
        "depeg_loss_stress_bps": float(np.mean(rate_stress * (1.0 - p_stress)) * 1e4),
        "issuer_hazard": float(issuer_hazard),
        "issuer_lgd": float(issuer_lgd),
    }
