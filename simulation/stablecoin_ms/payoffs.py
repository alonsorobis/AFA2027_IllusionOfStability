"""Per-agent payoffs and the indifference condition.

V_R(D) = primary_share * 1 + (1 - primary_share) * p_sec(D) - phi
V_H(theta) = theta - c_q * q + omega

The expected indifference gap E[V_R - V_H | s_i = s*_k] is computed by
Gauss-Hermite quadrature over the posterior of theta given the threshold
signal. The Morris-Shin fixed point in `fixed_point.solve` drives this gap
to zero in every class k simultaneously.

See `planning/MODEL.md` Section 3.
"""

from __future__ import annotations

from typing import Dict, Mapping

import numpy as np
from scipy.special import roots_hermitenorm
from scipy.stats import norm

from .issuer import primary_share
from .scenario import CLASS_KEYS
from .secondary import secondary_price


def redemption_payoff(
    D: float,
    R: float,
    p_sec: float,
    phi: float,
) -> float:
    """V_R(D) = min(1, R/D) + (1 - min(1, R/D)) * p_sec - phi."""
    if phi < 0:
        raise ValueError("phi must be non-negative")
    share = primary_share(D, R)
    return float(share * 1.0 + (1.0 - share) * p_sec - phi)


def hold_payoff(
    theta: float,
    q: float,
    cq: float,
    omega: float,
) -> float:
    """V_H(theta) = theta - cq * q + omega."""
    return float(theta - cq * q + omega)


def aggregate_demand(
    thresholds: Mapping[str, float],
    theta: float,
    scenario,
) -> float:
    """D(theta; {s*_k}) = sum_k W_k * Phi((s*_k - theta) / sigma_k)."""
    D = 0.0
    for k in CLASS_KEYS:
        W_k = scenario.classes.pi[k] * scenario.classes.B[k]
        z = (thresholds[k] - theta) / scenario.classes.sigma[k]
        D += W_k * float(norm.cdf(z))
    return float(D)


_QUAD_CACHE: Dict[int, tuple] = {}


def _hermite_nodes(n_nodes: int) -> tuple:
    """Cache Gauss-Hermite nodes for the standard normal density.

    We use `roots_hermitenorm`, whose nodes integrate against the weight
    exp(-x^2 / 2) / sqrt(2*pi). The returned (x, w) satisfy
        E[f(theta)] = sum_i w_i * f(s* + sigma * x_i)
    when theta | s_i = s* ~ N(s*, sigma^2) in the improper-prior limit.
    """
    if n_nodes not in _QUAD_CACHE:
        x, w = roots_hermitenorm(n_nodes)
        w = w / np.sqrt(2.0 * np.pi)
        _QUAD_CACHE[n_nodes] = (x, w)
    return _QUAD_CACHE[n_nodes]


def expected_indifference_gap(
    s_star_k: float,
    other_thresholds: Mapping[str, float],
    scenario,
    k: str,
    n_nodes: int = 15,
) -> float:
    """E[V_R - V_H | s_i = s_star_k] for class k.

    Integrates over theta ~ N(s_star_k, sigma_k^2) using Gauss-Hermite
    quadrature. The body is vectorised over the quadrature nodes: each of
    the K class-stake terms in D is evaluated against the (n_nodes,) theta
    array in a single call to `scipy.stats.norm.cdf`, and the secondary
    price + payoff formulas are propagated as numpy arrays. This brings
    the cost of one indifference evaluation down from O(n_nodes * K) Python
    function calls to O(K) plus an array reduction.

    `other_thresholds` is the current K-vector of thresholds; its entry
    for class k is overridden by `s_star_k` internally so the caller can
    pass the full current iterate.
    """
    sigma_k = scenario.classes.sigma[k]
    cq = scenario.classes.cq[k]
    omega = scenario.classes.omega[k]
    q_k = scenario.rails.q[k]
    issuer = scenario.issuer
    sec = scenario.secondary

    thresholds = dict(other_thresholds)
    thresholds[k] = s_star_k

    x_nodes, w_nodes = _hermite_nodes(n_nodes)
    theta_arr = s_star_k + sigma_k * x_nodes

    # vectorised aggregate demand over theta_arr
    D = np.zeros_like(theta_arr)
    for j in CLASS_KEYS:
        W_j = scenario.classes.pi[j] * scenario.classes.B[j]
        z = (thresholds[j] - theta_arr) / scenario.classes.sigma[j]
        D += W_j * norm.cdf(z)

    R = issuer.R
    U = np.maximum(D - R, 0.0)
    # primary share: D could be exactly zero -> share = 1 by convention
    with np.errstate(divide="ignore", invalid="ignore"):
        share_raw = np.where(D > 0, np.minimum(1.0, R / np.maximum(D, 1e-12)), 1.0)
    share = np.clip(share_raw, 0.0, 1.0)

    # vectorised secondary price
    Mtilde = sec.M / (1.0 + sec.zeta * U / sec.M)
    with np.errstate(divide="ignore", invalid="ignore"):
        impact = np.where(U > 0, (U / Mtilde) ** sec.nu, 0.0)
    # Counterparty risk does not mark down the secondary price; it enters the
    # value of holding (V_H) below. A riskier issuer therefore lowers the value
    # of *keeping* the coin and pushes holders to convert (endogenous coupling),
    # and counterparty risk is priced once, via the standalone counterparty
    # term in the premium, not twice.
    raw_price = 1.0 - sec.psi * impact - sec.mu_q * q_k
    p_sec = np.minimum(1.0, np.maximum(sec.p_underbar, raw_price))

    # Counterparty risk enters the value of holding (V_H) as a constant charge,
    # not the secondary price: a riskier issuer lowers the value of keeping the
    # coin. The calibrated interaction between this channel and the depeg channel
    # is second-order (tested with a state-dependent hazard), so the two risks
    # price additively.
    V_R = share * 1.0 + (1.0 - share) * p_sec - scenario.redemption_fee
    V_H = theta_arr - cq * q_k + omega - issuer.xi * issuer.h

    return float(np.sum(w_nodes * (V_R - V_H)))
