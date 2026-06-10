"""Monte Carlo loop and aggregate moments.

Each draw samples theta from the prior, solves the K-dimensional Morris-Shin
fixed point at that theta, and records the realised DrawResult. Aggregating
over N draws produces the moments used to calibrate against USDC March 2023
and to populate the cost-benefit metric.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

import numpy as np

from .fixed_point import solve
from .scenario import CLASS_KEYS, DrawResult, Scenario


def sample_theta(scenario: Scenario, rng: np.random.Generator) -> float:
    """Draw theta from the scenario's prior.

    In the improper-prior limit (tau = 0), this falls back to a normal
    centred at theta_prior.mean with a hand-picked dispersion. For
    calibration we use the informative-prior branch with finite tau.
    """
    prior = scenario.theta_prior
    if prior.tau > 0:
        sigma_theta = 1.0 / np.sqrt(prior.tau)
        return float(prior.mean + sigma_theta * rng.standard_normal())
    return float(prior.mean + 0.10 * rng.standard_normal())


def run_scenario(
    scenario: Scenario,
    out_dir: Path | None = None,
    verbose: bool = False,
) -> List[DrawResult]:
    """Run all Monte Carlo draws for one Scenario and return the DrawResult list."""
    rng = np.random.default_rng(scenario.seed)
    draws: List[DrawResult] = []
    for t in range(scenario.n_draws):
        theta = sample_theta(scenario, rng)
        res = solve(scenario, theta=theta)
        draws.append(res)
        if verbose and (t + 1) % 100 == 0:
            print(f"  draw {t+1}/{scenario.n_draws} | theta={theta:.4f} | p_sec={res.secondary_price:.4f}")

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "scenario_name": scenario.name,
            "n_draws": scenario.n_draws,
            "n_agents": scenario.n_agents,
            "seed": scenario.seed,
            "theta_prior": {"mean": scenario.theta_prior.mean, "tau": scenario.theta_prior.tau},
            "moments": aggregate_moments(draws),
        }
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
    return draws


def aggregate_moments(draws: List[DrawResult]) -> Dict[str, float]:
    """Compute the moments used in calibration and reporting.

    Returns the six USDC-comparable moments (mean p_sec, std p_sec,
    large-depeg frequency, mean abs depeg in bps, min p_sec) plus aggregate
    statistics (mean queue, mean unmet, mean redemption rate per class).
    """
    if not draws:
        raise ValueError("draws is empty")
    p_sec = np.array([d.secondary_price for d in draws])
    converged = np.array([d.converged for d in draws])
    p_threshold = 0.975
    moments: Dict[str, float] = {
        "mean_p_sec": float(p_sec.mean()),
        "std_p_sec": float(p_sec.std()),
        "min_p_sec": float(p_sec.min()),
        "max_p_sec": float(p_sec.max()),
        "p95_depeg_bps": float(np.quantile(1.0 - p_sec, 0.95) * 1e4),
        "large_depeg_freq": float((p_sec < p_threshold).mean()),
        "mean_abs_depeg_bps": float(np.abs(1.0 - p_sec).mean() * 1e4),
        "fraction_converged": float(converged.mean()),
        "mean_aggregate_demand": float(np.array([d.aggregate_demand for d in draws]).mean()),
        "mean_unmet_demand": float(np.array([d.unmet_demand for d in draws]).mean()),
    }
    for k in CLASS_KEYS:
        rates = np.array([d.redemption_rate[k] for d in draws])
        moments[f"mean_redemption_rate_{k}"] = float(rates.mean())
        moments[f"std_redemption_rate_{k}"] = float(rates.std())
    return moments
