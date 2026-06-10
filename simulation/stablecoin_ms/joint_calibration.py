"""Joint calibration of USDC and DAI with shared structural parameters.

This module supersedes the single-asset calibration in `calibration.py`. The
key changes are:

1. The two stablecoins are calibrated jointly. The microstructure block,
   the two active class signal noises and the two regime precisions are
   shared across assets. The stress-regime $\\theta$-mean is asset-specific.
2. The baseline regime mean is fixed at $\\theta_{baseline}=1.0$ (par) for
   both stablecoins by definition rather than calibrated, removing two
   parameters.
3. The two non-active class signal noises are fixed externally on economic
   grounds: $\\sigma_{\\text{market-maker}} = 0.05$ and
   $\\sigma_{\\text{wholesale}} = 0.10$. The corresponding classes are
   structurally less involved in the price moments at the calibrated
   stress regime, so we discipline them from the literature rather than
   from the loss function.

The result is a ten-parameter calibration matched to twelve price moments
(six per stablecoin). The model is over-identified at ratio 1.2.

Supply moments computed from DefiLlama daily circulating supply are used as
an additional, independent validation check in Section~\\ref{sec:results}
rather than in the loss function. The mapping from the model's redemption
mass to the data's daily supply change requires an active-fraction
assumption that we prefer to avoid baking into the calibration.
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


# ---------------------------------------------------------------------------
# Externally-fixed parameters
# ---------------------------------------------------------------------------

SIGMA_MARKET_MAKER = 0.05    # arbitrageurs observe issuer reserve quality with low noise
SIGMA_WHOLESALE = 0.10       # institutional users with strong private information
THETA_BASELINE = 1.0         # par-convertibility regime mean by definition


# Ten free parameters in the joint calibration vector
JOINT_PARAM_NAMES = (
    "sigma_retail",
    "sigma_cross_border",
    "psi",
    "nu",
    "mu_q",
    "zeta",
    "tau_baseline",
    "tau_stress",
    "theta_stress_USDC",
    "theta_stress_DAI",
)


@dataclass(frozen=True)
class JointBounds:
    sigma: Tuple[float, float] = (0.05, 1.0)
    psi: Tuple[float, float] = (0.01, 5.0)
    nu: Tuple[float, float] = (1.0, 4.0)
    mu_q: Tuple[float, float] = (0.0, 0.5)
    zeta: Tuple[float, float] = (0.0, 5.0)
    tau_baseline: Tuple[float, float] = (100.0, 1000.0)
    tau_stress: Tuple[float, float] = (1.0, 50.0)
    theta_stress: Tuple[float, float] = (-1.0, 1.5)


def joint_bounds_vector() -> Tuple[Tuple[float, float], ...]:
    b = JointBounds()
    return (
        b.sigma, b.sigma,                # sigma_retail, sigma_cross_border
        b.psi, b.nu, b.mu_q, b.zeta,
        b.tau_baseline, b.tau_stress,
        b.theta_stress, b.theta_stress,  # USDC stress mean, DAI stress mean
    )


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssetTargets:
    asset: str
    # Six price moments per asset, used in the loss
    baseline_mean_close: float
    baseline_std_close: float
    baseline_large_depeg_freq: float
    stress_min_close: float
    stress_mean_abs_depeg_bps: float
    stress_large_depeg_freq: float
    # Supply moments are loaded for validation only
    baseline_supply_std_bps: float
    stress_supply_min_pct_bps: float

    @classmethod
    def from_files(cls, asset: str) -> "AssetTargets":
        price_path = PROJECT_ROOT / "data" / "processed" / f"{asset.lower()}_march2023_targets.json"
        supply_path = PROJECT_ROOT / "data" / "processed" / f"{asset.lower()}_supply_moments.json"
        price = json.loads(price_path.read_text(encoding="utf-8"))
        supply = json.loads(supply_path.read_text(encoding="utf-8"))
        return cls(
            asset=asset,
            baseline_mean_close=float(price["baseline_mean_close"]),
            baseline_std_close=float(price["baseline_std_close"]),
            baseline_large_depeg_freq=float(price["baseline_large_depeg_freq"]),
            stress_min_close=float(price["stress_min_close"]),
            stress_mean_abs_depeg_bps=float(price["stress_mean_abs_depeg_bps"]),
            stress_large_depeg_freq=float(price["stress_large_depeg_freq"]),
            baseline_supply_std_bps=float(supply["baseline_supply_std_bps"]),
            stress_supply_min_pct_bps=float(supply["stress_supply_min_pct_bps"]),
        )


# ---------------------------------------------------------------------------
# Scenario construction
# ---------------------------------------------------------------------------


def build_template(name: str, n_draws: int, seed: int) -> Scenario:
    ks = CLASS_KEYS
    return Scenario(
        name=name,
        n_agents=1000,
        n_draws=n_draws,
        seed=seed,
        classes=ClassParameters(
            pi={k: 0.25 for k in ks},
            B={k: 1.0 for k in ks},
            sigma={"retail": 0.20, "wholesale": SIGMA_WHOLESALE,
                   "cross_border": 0.25, "market_maker": SIGMA_MARKET_MAKER},
            omega={k: 0.01 for k in ks},
            cq={k: 0.05 for k in ks},
        ),
        issuer=IssuerParameters(R=0.6, A=0.3, h=0.01, xi=0.30),
        secondary=SecondaryParameters(M=2.0, psi=0.30, nu=1.5, mu_q=0.05,
                                      zeta=0.50, p_underbar=0.50),
        rails=RailParameters(q={k: 0.10 for k in ks}),
        theta_prior=ThetaPrior(mean=THETA_BASELINE, tau=400.0),
    )


def apply_joint_params(
    scenario: Scenario,
    phi: np.ndarray,
    theta_stress_mean: float,
    regime: str,
) -> Scenario:
    """Build a parameterised scenario for either the baseline or the stress
    regime of one asset.

    The ten free parameters in `phi` follow JOINT_PARAM_NAMES. The two non-
    active class signal noises and the baseline regime mean are fixed
    externally to SIGMA_MARKET_MAKER, SIGMA_WHOLESALE and THETA_BASELINE
    respectively.
    """
    sigma = {
        "retail": float(phi[0]),
        "wholesale": SIGMA_WHOLESALE,
        "cross_border": float(phi[1]),
        "market_maker": SIGMA_MARKET_MAKER,
    }
    classes = replace(scenario.classes, sigma=sigma)
    secondary = replace(
        scenario.secondary,
        psi=float(phi[2]),
        nu=float(phi[3]),
        mu_q=float(phi[4]),
        zeta=float(phi[5]),
    )
    if regime == "baseline":
        theta_prior = ThetaPrior(mean=THETA_BASELINE, tau=float(phi[6]))
    elif regime == "stress":
        theta_prior = ThetaPrior(mean=float(theta_stress_mean), tau=float(phi[7]))
    else:
        raise ValueError(f"regime must be 'baseline' or 'stress', got {regime!r}")
    return replace(scenario, classes=classes, secondary=secondary, theta_prior=theta_prior)


# ---------------------------------------------------------------------------
# Loss and moments
# ---------------------------------------------------------------------------


DEFAULT_WEIGHTS = {
    "baseline_mean_close": 100.0,
    "baseline_std_close": 1000.0,
    "baseline_large_depeg_freq": 50.0,
    "stress_min_close": 50.0,
    "stress_mean_abs_depeg_bps": 1.0,
    "stress_large_depeg_freq": 50.0,
}


def asset_moments_at_phi(
    phi: np.ndarray,
    asset: str,
    theta_stress_mean: float,
    n_draws: int,
    seed: int,
) -> Dict[str, float]:
    """Return the six price moments for one asset at parameter vector phi.

    The supply-side dispersion of the model (cross-draw standard deviation of
    the aggregate redemption mass D in basis points of total stake) is also
    returned for offline validation against the DefiLlama data.
    """
    base_sc = build_template(f"joint_{asset}_b", n_draws=n_draws, seed=seed)
    stress_sc = build_template(f"joint_{asset}_s", n_draws=n_draws, seed=seed + 1)
    base_sc = apply_joint_params(base_sc, phi, theta_stress_mean, "baseline")
    stress_sc = apply_joint_params(stress_sc, phi, theta_stress_mean, "stress")
    base_draws = run_scenario(base_sc)
    stress_draws = run_scenario(stress_sc)
    bm = aggregate_moments(base_draws)
    sm = aggregate_moments(stress_draws)

    base_D = np.array([d.aggregate_demand for d in base_draws])
    stress_D = np.array([d.aggregate_demand for d in stress_draws])

    return {
        "baseline_mean_close": bm["mean_p_sec"],
        "baseline_std_close": bm["std_p_sec"],
        "baseline_large_depeg_freq": bm["large_depeg_freq"],
        "stress_min_close": sm["min_p_sec"],
        "stress_mean_abs_depeg_bps": sm["mean_abs_depeg_bps"],
        "stress_large_depeg_freq": sm["large_depeg_freq"],
        "model_baseline_D_std": float(base_D.std()),
        "model_stress_D_max": float(stress_D.max()),
    }


def joint_loss(
    phi: np.ndarray,
    targets: Dict[str, AssetTargets],
    n_draws: int = 200,
    weights: Dict[str, float] | None = None,
    seed: int = 42,
) -> float:
    """Weighted L2 loss across both stablecoins and the six price moments
    per stablecoin.

    `targets` is a dict keyed by asset name (e.g. {"USDC": usdc_t, "DAI": dai_t})
    of AssetTargets objects. The stress-mean for each asset is taken from
    the corresponding entry of `phi` (index 8 for USDC, 9 for DAI).
    """
    weights = weights or DEFAULT_WEIGHTS
    asset_stress_mean = {"USDC": float(phi[8]), "DAI": float(phi[9])}
    total = 0.0
    for asset, tgt in targets.items():
        mom = asset_moments_at_phi(
            phi, asset=asset, theta_stress_mean=asset_stress_mean[asset],
            n_draws=n_draws, seed=seed + (hash(asset) & 0xFFF),
        )
        for name, w in weights.items():
            err = mom[name] - getattr(tgt, name)
            total += w * (err ** 2)
    return float(total)
