"""Calibration of the aggregate stablecoin block to USDC March 2023.

We match six moments computed from the CryptoCompare USDC hourly series in
`data/processed/usdc_march2023_targets.json`. Three are baseline moments
(2022 calendar year), three are stress-window moments (10–13 Mar 2023).

The calibration tunes a parameter vector
    phi = (sigma_retail, sigma_wholesale, sigma_cross_border, sigma_market_maker,
           psi, nu, mu_q, zeta, theta_baseline_mean, theta_stress_mean)
by minimising a weighted L2 loss between model-implied moments and data
targets. All other Scenario parameters are held fixed at their session-05
baseline values; tau (the theta-prior precision) is held at the session-05
baseline; reserves are held fixed across baseline and stress to keep the
identification on theta and the secondary-market block.

The loss is evaluated by spawning two parameterised Scenario objects from
a template, running montecarlo.run_scenario on each, computing aggregate
moments, and stacking the moment errors.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Dict, Tuple

import numpy as np
from scipy.optimize import minimize

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
DEFAULT_TARGETS_PATH = PROJECT_ROOT / "data" / "processed" / "usdc_march2023_targets.json"


@dataclass(frozen=True)
class USDCMarch2023Targets:
    """Empirical moments to match. Defaults below are placeholders; load
    from `data/processed/usdc_march2023_targets.json` for the real values."""

    baseline_mean_close: float = 1.0000
    baseline_std_close: float = 0.0008
    baseline_large_depeg_freq: float = 0.000
    stress_min_close: float = 0.9022
    stress_mean_abs_depeg_bps: float = 240.06
    stress_large_depeg_freq: float = 0.3958
    p_threshold: float = 0.975

    @classmethod
    def from_json(cls, path: Path | str = DEFAULT_TARGETS_PATH) -> "USDCMarch2023Targets":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            baseline_mean_close=float(data["baseline_mean_close"]),
            baseline_std_close=float(data["baseline_std_close"]),
            baseline_large_depeg_freq=float(data["baseline_large_depeg_freq"]),
            stress_min_close=float(data["stress_min_close"]),
            stress_mean_abs_depeg_bps=float(data["stress_mean_abs_depeg_bps"]),
            stress_large_depeg_freq=float(data["stress_large_depeg_freq"]),
            p_threshold=float(data.get("p_threshold", 0.975)),
        )


# Parameter vector layout
PARAM_NAMES = (
    "sigma_retail",
    "sigma_wholesale",
    "sigma_cross_border",
    "sigma_market_maker",
    "psi",
    "nu",
    "mu_q",
    "zeta",
    "theta_baseline_mean",
    "theta_stress_mean",
    "tau_baseline",
    "tau_stress",
)


@dataclass(frozen=True)
class CalibrationBounds:
    sigma: Tuple[float, float] = (0.05, 1.0)
    psi: Tuple[float, float] = (0.01, 5.0)
    nu: Tuple[float, float] = (1.0, 4.0)
    mu_q: Tuple[float, float] = (0.0, 0.5)
    zeta: Tuple[float, float] = (0.0, 5.0)
    theta_baseline: Tuple[float, float] = (0.5, 2.0)
    theta_stress: Tuple[float, float] = (-1.0, 1.5)
    # tau = 1 / sigma_theta^2; tau_baseline = 400 means sigma_theta = 0.05
    # (quasi-deterministic baseline); tau_stress small allows fat tails.
    tau_baseline: Tuple[float, float] = (100.0, 1000.0)
    tau_stress: Tuple[float, float] = (1.0, 50.0)


def default_bounds() -> Tuple[Tuple[float, float], ...]:
    b = CalibrationBounds()
    return (
        (b.sigma,) * 4
        + (b.psi, b.nu, b.mu_q, b.zeta, b.theta_baseline, b.theta_stress)
        + (b.tau_baseline, b.tau_stress)
    )


def template_scenario(name: str, n_draws: int, seed: int) -> Scenario:
    """Construct a baseline template that the calibrator parameterises around."""
    ks = CLASS_KEYS
    return Scenario(
        name=name,
        n_agents=1000,
        n_draws=n_draws,
        seed=seed,
        classes=ClassParameters(
            pi={k: 0.25 for k in ks},
            B={k: 1.0 for k in ks},
            sigma={"retail": 0.20, "wholesale": 0.15, "cross_border": 0.25, "market_maker": 0.10},
            omega={k: 0.01 for k in ks},
            cq={k: 0.05 for k in ks},
        ),
        issuer=IssuerParameters(R=0.6, A=0.3, h=0.01, xi=0.30),
        secondary=SecondaryParameters(M=2.0, psi=0.30, nu=1.5, mu_q=0.05, zeta=0.50, p_underbar=0.50),
        rails=RailParameters(q={k: 0.10 for k in ks}),
        theta_prior=ThetaPrior(mean=1.0, tau=4.0),
    )


def apply_params(
    scenario: Scenario,
    phi: np.ndarray,
    theta_mean: float,
    tau: float,
) -> Scenario:
    """Return a copy of `scenario` with the parameter vector applied.

    `phi` follows PARAM_NAMES order. `theta_mean` and `tau` override the
    prior so the same `phi` can be reused for baseline and stress with
    regime-dependent dispersion (high tau in baseline = quasi-deterministic;
    low tau in stress = fat-tailed).
    """
    sigma = {
        "retail": float(phi[0]),
        "wholesale": float(phi[1]),
        "cross_border": float(phi[2]),
        "market_maker": float(phi[3]),
    }
    classes = replace(scenario.classes, sigma=sigma)
    secondary = replace(
        scenario.secondary,
        psi=float(phi[4]),
        nu=float(phi[5]),
        mu_q=float(phi[6]),
        zeta=float(phi[7]),
    )
    theta_prior = replace(
        scenario.theta_prior, mean=float(theta_mean), tau=float(tau)
    )
    return replace(scenario, classes=classes, secondary=secondary, theta_prior=theta_prior)


def model_moments_pair(
    phi: np.ndarray,
    template_base: Scenario,
    template_stress: Scenario,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Run montecarlo for the baseline and stress scenarios under phi."""
    base = apply_params(template_base, phi, theta_mean=float(phi[8]), tau=float(phi[10]))
    stress = apply_params(template_stress, phi, theta_mean=float(phi[9]), tau=float(phi[11]))
    return aggregate_moments(run_scenario(base)), aggregate_moments(run_scenario(stress))


def usdc_loss(
    phi: np.ndarray,
    targets: USDCMarch2023Targets,
    template_base: Scenario,
    template_stress: Scenario,
    weights: Dict[str, float] | None = None,
) -> float:
    """Weighted L2 distance between model moments and USDC targets."""
    weights = weights or {
        "baseline_mean_close": 100.0,
        "baseline_std_close": 1000.0,
        "baseline_large_depeg_freq": 50.0,
        "stress_min_close": 50.0,
        "stress_mean_abs_depeg_bps": 1.0,
        "stress_large_depeg_freq": 50.0,
    }
    base_m, stress_m = model_moments_pair(phi, template_base, template_stress)
    err = {
        "baseline_mean_close": base_m["mean_p_sec"] - targets.baseline_mean_close,
        "baseline_std_close": base_m["std_p_sec"] - targets.baseline_std_close,
        "baseline_large_depeg_freq": base_m["large_depeg_freq"] - targets.baseline_large_depeg_freq,
        "stress_min_close": stress_m["min_p_sec"] - targets.stress_min_close,
        "stress_mean_abs_depeg_bps": stress_m["mean_abs_depeg_bps"] - targets.stress_mean_abs_depeg_bps,
        "stress_large_depeg_freq": stress_m["large_depeg_freq"] - targets.stress_large_depeg_freq,
    }
    return float(sum(weights[name] * (e ** 2) for name, e in err.items()))


def calibrate_usdc(
    targets: USDCMarch2023Targets | None = None,
    n_draws_eval: int = 200,
    seed: int = 42,
    maxiter: int = 30,
    bounds: Tuple[Tuple[float, float], ...] | None = None,
    callback: Callable[[np.ndarray], None] | None = None,
):
    """Run a Nelder-Mead-style minimisation against the USDC targets.

    Notes
    -----
    The fixed-point solve is expensive (~half a second per draw), so this
    routine is parameterised to keep the budget small by default. Increase
    n_draws_eval and maxiter for the final calibration.
    """
    targets = targets or USDCMarch2023Targets.from_json()
    template_base = template_scenario("usdc_calib_baseline", n_draws_eval, seed)
    template_stress = template_scenario("usdc_calib_stress", n_draws_eval, seed + 1)
    bounds = bounds or default_bounds()

    # x0: the template's own parameter values, with two thetas spanning the
    # baseline-vs-stress range and regime-dependent tau (high in baseline,
    # low in stress) to give the quasi-deterministic / fat-tailed split.
    x0 = np.array(
        [
            template_base.classes.sigma["retail"],
            template_base.classes.sigma["wholesale"],
            template_base.classes.sigma["cross_border"],
            template_base.classes.sigma["market_maker"],
            template_base.secondary.psi,
            template_base.secondary.nu,
            template_base.secondary.mu_q,
            template_base.secondary.zeta,
            template_base.theta_prior.mean,
            0.2,    # initial stress theta well below the baseline
            400.0,  # tau_baseline: sigma_theta = 0.05, quasi-deterministic
            10.0,   # tau_stress: sigma_theta = 0.32, fat-tailed
        ],
        dtype=float,
    )

    def fn(phi: np.ndarray) -> float:
        clipped = np.array([np.clip(v, lo, hi) for v, (lo, hi) in zip(phi, bounds)])
        return usdc_loss(clipped, targets, template_base, template_stress)

    result = minimize(
        fn,
        x0,
        method="Nelder-Mead",
        options={"maxiter": maxiter, "xatol": 1e-3, "fatol": 1e-3, "disp": False},
        callback=callback,
    )
    return {
        "result": result,
        "phi_star": dict(zip(PARAM_NAMES, [float(v) for v in result.x])),
        "loss": float(result.fun),
        "targets": targets,
    }
