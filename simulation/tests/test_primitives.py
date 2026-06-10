"""Unit tests for the implemented primitives.

Covers:
- signals.class_redemption_probability and posterior helpers.
- secondary.effective_depth and secondary.secondary_price.
- payoffs.redemption_payoff, hold_payoff, aggregate_demand and quadrature.
- issuer identities (smoke test was already in test_smoke.py).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from stablecoin_ms import payoffs, scenario, secondary, signals


def _baseline_scenario(**overrides) -> scenario.Scenario:
    ks = scenario.CLASS_KEYS
    cfg = dict(
        name="baseline",
        n_agents=1000,
        n_draws=100,
        seed=42,
        classes=scenario.ClassParameters(
            pi={k: 0.25 for k in ks},
            B={k: 1.0 for k in ks},
            sigma={"retail": 0.20, "wholesale": 0.15, "cross_border": 0.25, "market_maker": 0.10},
            omega={k: 0.01 for k in ks},
            cq={k: 0.05 for k in ks},
        ),
        issuer=scenario.IssuerParameters(R=0.6, A=0.3, h=0.01, xi=0.30),
        secondary=scenario.SecondaryParameters(M=2.0, psi=0.30, nu=1.5, mu_q=0.05, zeta=0.50, p_underbar=0.50),
        rails=scenario.RailParameters(q={k: 0.10 for k in ks}),
    )
    cfg.update(overrides)
    return scenario.Scenario(**cfg)


# --- signals -----------------------------------------------------------


def test_class_redemption_probability_basic():
    # At s_star == theta, Phi(0) = 0.5.
    assert signals.class_redemption_probability(0.0, 0.0, 1.0) == pytest.approx(0.5)
    # s_star much greater than theta -> Phi(+infty) = 1.
    assert signals.class_redemption_probability(10.0, 0.0, 1.0) > 0.999
    # s_star much smaller -> Phi(-infty) = 0.
    assert signals.class_redemption_probability(-10.0, 0.0, 1.0) < 0.001


def test_posterior_mean_improper_prior_returns_signal():
    assert signals.posterior_mean_theta(1.5, 0.20) == pytest.approx(1.5)


def test_posterior_mean_with_prior_shrinks_toward_prior():
    s = 1.0
    pm = signals.posterior_mean_theta(s, sigma_k=1.0, prior_mean=0.0, prior_tau=1.0)
    # 50/50 weight when tau_prior == tau_k = 1
    assert pm == pytest.approx(0.5)


def test_posterior_variance_improper_prior():
    assert signals.posterior_variance_theta(0.2) == pytest.approx(0.04)


# --- secondary --------------------------------------------------------


def test_effective_depth_monotone_in_U():
    Mtilde_low = secondary.effective_depth(U=0.0, M=1.0, zeta=0.5)
    Mtilde_high = secondary.effective_depth(U=2.0, M=1.0, zeta=0.5)
    assert Mtilde_low == pytest.approx(1.0)
    assert Mtilde_high < Mtilde_low


def test_secondary_price_par_at_zero_pressure():
    p = secondary.secondary_price(
        U=0.0, M=1.0, psi=0.3, nu=1.5, mu_q=0.0, q=0.0,
        xi=0.0, h=0.0, p_underbar=0.5, zeta=0.5,
    )
    assert p == pytest.approx(1.0)


def test_secondary_price_floors_at_p_underbar():
    p = secondary.secondary_price(
        U=100.0, M=0.1, psi=10.0, nu=2.0, mu_q=0.5, q=1.0,
        xi=0.3, h=1.0, p_underbar=0.5, zeta=10.0,
    )
    assert p == pytest.approx(0.5)


def test_secondary_price_caps_at_one():
    # Strongly positive noise should not push the price above 1.
    p = secondary.secondary_price(
        U=0.0, M=1.0, psi=0.0, nu=1.5, mu_q=0.0, q=0.0,
        xi=0.0, h=0.0, p_underbar=0.5, zeta=0.0, noise=0.05,
    )
    assert p == pytest.approx(1.0)


# --- payoffs and aggregate demand ------------------------------------


def test_redemption_payoff_all_primary():
    # R >> D -> share == 1 -> V_R = 1 - phi
    assert payoffs.redemption_payoff(D=1.0, R=10.0, p_sec=0.5, phi=0.02) == pytest.approx(0.98)


def test_redemption_payoff_all_secondary():
    # R = 0 -> share == 0 -> V_R = p_sec - phi
    assert payoffs.redemption_payoff(D=1.0, R=0.0, p_sec=0.5, phi=0.02) == pytest.approx(0.48)


def test_hold_payoff_linear():
    assert payoffs.hold_payoff(theta=1.0, q=0.2, cq=0.5, omega=0.05) == pytest.approx(0.95)


def test_aggregate_demand_at_threshold_theta_is_half_stake():
    # If s*_k == theta for every k, every class redeems with prob 0.5,
    # so D = 0.5 * sum_k W_k = 0.5 * W.
    sc = _baseline_scenario()
    thresholds = {k: 0.0 for k in scenario.CLASS_KEYS}
    D = payoffs.aggregate_demand(thresholds, theta=0.0, scenario=sc)
    assert D == pytest.approx(0.5 * sc.total_stake())


def test_aggregate_demand_monotone_in_theta():
    sc = _baseline_scenario()
    thresholds = {k: 0.0 for k in scenario.CLASS_KEYS}
    D_low_theta = payoffs.aggregate_demand(thresholds, theta=-1.0, scenario=sc)
    D_high_theta = payoffs.aggregate_demand(thresholds, theta=+1.0, scenario=sc)
    assert D_low_theta > D_high_theta


# --- expected_indifference_gap quadrature ----------------------------


def test_indifference_gap_returns_finite_number():
    sc = _baseline_scenario()
    thresholds = {k: 0.0 for k in scenario.CLASS_KEYS}
    gap = payoffs.expected_indifference_gap(
        s_star_k=0.0, other_thresholds=thresholds, scenario=sc, k="retail",
    )
    assert math.isfinite(gap)


def test_indifference_gap_sign_changes_with_threshold():
    # Sweeping s*_k from very low to very high should cross zero somewhere.
    sc = _baseline_scenario()
    base_thresholds = {k: 0.0 for k in scenario.CLASS_KEYS}
    low = payoffs.expected_indifference_gap(-2.0, base_thresholds, sc, "retail")
    high = payoffs.expected_indifference_gap(+2.0, base_thresholds, sc, "retail")
    assert low * high < 0, (
        "expected_indifference_gap should cross zero between s*_k = -2 and +2; "
        f"got low={low:.4f}, high={high:.4f}"
    )
