"""Private-signal generation and posterior helpers.

Maps to `planning/MODEL.md` Section 2. Under the improper-uniform-prior limit
(tau_theta = 0), the posterior over theta given s_i = s* is N(s*, sigma_k^2).
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def draw_private_signals(
    theta: float,
    sigma: float,
    n: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draw n private signals s_i = theta + sigma * epsilon, epsilon ~ N(0,1)."""
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    return theta + sigma * rng.standard_normal(n)


def class_redemption_probability(
    s_star_k: float,
    theta: float,
    sigma_k: float,
) -> float:
    """Pr(redeem) for class k given threshold s_star_k and realised theta.

    Returns Phi((s_star_k - theta) / sigma_k). Equation (D) in MODEL.md §3.
    """
    if sigma_k <= 0:
        raise ValueError("sigma_k must be positive")
    return float(norm.cdf((s_star_k - theta) / sigma_k))


def posterior_mean_theta(
    s_star_k: float,
    sigma_k: float,
    prior_mean: float = 0.0,
    prior_tau: float = 0.0,
) -> float:
    """Bayesian posterior mean of theta given s_i = s_star_k.

    In the improper-prior limit (prior_tau = 0) this equals s_star_k exactly.
    Kept general for robustness checks with informative priors.
    """
    if sigma_k <= 0:
        raise ValueError("sigma_k must be positive")
    if prior_tau < 0:
        raise ValueError("prior_tau must be non-negative")
    tau_k = 1.0 / (sigma_k ** 2)
    if prior_tau == 0.0:
        return float(s_star_k)
    return float((prior_tau * prior_mean + tau_k * s_star_k) / (prior_tau + tau_k))


def posterior_variance_theta(
    sigma_k: float,
    prior_tau: float = 0.0,
) -> float:
    """Posterior variance of theta given s_i (improper-prior limit -> sigma_k^2)."""
    if sigma_k <= 0:
        raise ValueError("sigma_k must be positive")
    tau_k = 1.0 / (sigma_k ** 2)
    return float(1.0 / (prior_tau + tau_k))
