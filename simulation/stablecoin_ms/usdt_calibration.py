"""USDT-specific calibration with may-2022 Terra-fallout episode as stress anchor.

The structure mirrors `simple_calibration.py` but:
  - Targets are USDT may-2022, not USDC march-2023
  - Counterparty parameters (h, xi) are higher to reflect Tether's weaker
    attestation and historically more concentrated commercial-paper holdings
  - Large-depeg threshold is 0.99 (USDT's stress event never crossed 0.975)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np

from .montecarlo import aggregate_moments, run_scenario
from .scenario import (
    ClassParameters,
    IssuerParameters,
    RailParameters,
    Scenario,
    SecondaryParameters,
    ThetaPrior,
)
from .simple_calibration import (
    SIMPLE_PARAM_NAMES,
    simple_bounds_vector,
    THETA_BASELINE,
    TAU_BASELINE,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

USDT_HAZARD = 0.02     # 2 percent annual; double USDC's 1 percent
USDT_LGD = 0.30        # 30 percent loss given default; up from USDC's 20 percent
USDT_THRESHOLD = 0.99  # large-depeg threshold for USDT (its stress max was -250 bps)


@dataclass(frozen=True)
class USDTTargets:
    baseline_mean_close: float
    baseline_std_close: float
    baseline_large_depeg_freq: float
    stress_min_close: float
    stress_mean_abs_depeg_bps: float
    stress_large_depeg_freq: float
    p_threshold: float = USDT_THRESHOLD

    @classmethod
    def from_json(cls) -> "USDTTargets":
        path = PROJECT_ROOT / "data" / "processed" / "usdt_may2022_targets.json"
        d = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            baseline_mean_close=float(d["baseline_mean_close"]),
            baseline_std_close=float(d["baseline_std_close"]),
            baseline_large_depeg_freq=float(d["baseline_large_depeg_freq"]),
            stress_min_close=float(d["stress_min_close"]),
            stress_mean_abs_depeg_bps=float(d["stress_mean_abs_depeg_bps"]),
            stress_large_depeg_freq=float(d["stress_large_depeg_freq"]),
            p_threshold=float(d.get("p_threshold", USDT_THRESHOLD)),
        )


def build_scenario_usdt(name: str, phi: np.ndarray, regime: str,
                          n_draws: int, seed: int) -> Scenario:
    """Build a USDT-flavoured scenario: same microstructure, higher counterparty risk."""
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
        issuer=IssuerParameters(R=0.5, A=0.4, h=USDT_HAZARD, xi=USDT_LGD),  # USDT-style reserve composition
        secondary=secondary,
        rails=RailParameters(q={"retail": 0.10, "wholesale": 0.10,
                                  "cross_border": 0.10, "market_maker": 0.10}),
        theta_prior=theta_prior,
    )


def usdt_moments(phi: np.ndarray, n_draws: int, seed: int,
                  threshold: float = USDT_THRESHOLD) -> Dict[str, float]:
    """Return the six USDT-specific price moments under the one-class model."""
    base_sc = build_scenario_usdt("usdt_base", phi, "baseline", n_draws=n_draws, seed=seed)
    stress_sc = build_scenario_usdt("usdt_str", phi, "stress", n_draws=n_draws, seed=seed + 1)
    # We need to re-aggregate with the custom threshold for the "large_depeg" moments
    bd = run_scenario(base_sc)
    sd = run_scenario(stress_sc)

    base_p = np.array([d.secondary_price for d in bd])
    stress_p = np.array([d.secondary_price for d in sd])
    return {
        "baseline_mean_close": float(np.mean(base_p)),
        "baseline_std_close": float(np.std(base_p)),
        "baseline_large_depeg_freq": float(np.mean(base_p < threshold)),
        "stress_min_close": float(np.min(stress_p)),
        "stress_mean_abs_depeg_bps": float(np.mean(np.abs(stress_p - 1.0)) * 1e4),
        "stress_large_depeg_freq": float(np.mean(stress_p < threshold)),
    }


USDT_WEIGHTS = {
    "baseline_mean_close": 100.0,
    "baseline_std_close": 1000.0,
    "baseline_large_depeg_freq": 50.0,
    "stress_min_close": 50.0,
    "stress_mean_abs_depeg_bps": 1.0,
    "stress_large_depeg_freq": 50.0,
}


def usdt_loss(
    phi: np.ndarray,
    targets: USDTTargets,
    n_draws: int = 200,
    weights: Dict[str, float] | None = None,
    seed: int = 42,
) -> float:
    weights = weights or USDT_WEIGHTS
    mom = usdt_moments(phi, n_draws=n_draws, seed=seed, threshold=targets.p_threshold)
    return float(sum(w * (mom[name] - getattr(targets, name)) ** 2
                     for name, w in weights.items()))


def risk_components_usdt(
    phi: np.ndarray,
    n_draws: int = 500,
    seed: int = 42,
) -> Dict[str, float]:
    """USDT risk decomposition at phi."""
    base_sc = build_scenario_usdt("risk_base", phi, "baseline", n_draws=n_draws, seed=seed)
    stress_sc = build_scenario_usdt("risk_str", phi, "stress", n_draws=n_draws, seed=seed + 1)
    base_draws = run_scenario(base_sc)
    stress_draws = run_scenario(stress_sc)
    p_base = np.array([d.secondary_price for d in base_draws])
    p_stress = np.array([d.secondary_price for d in stress_draws])
    rate_base = np.array([d.redemption_rate["retail"] for d in base_draws])
    rate_stress = np.array([d.redemption_rate["retail"] for d in stress_draws])
    return {
        "counterparty_loss_bps": float(USDT_HAZARD * USDT_LGD * 1e4),
        "depeg_loss_baseline_bps": float(np.mean(rate_base * (1.0 - p_base)) * 1e4),
        "depeg_loss_stress_bps": float(np.mean(rate_stress * (1.0 - p_stress)) * 1e4),
        "issuer_hazard": float(USDT_HAZARD),
        "issuer_lgd": float(USDT_LGD),
    }
