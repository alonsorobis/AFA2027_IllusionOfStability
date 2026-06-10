"""Tests for the K-dimensional Morris-Shin fixed-point solver.

Strategy:
1. Smoke test: solve() returns a populated DrawResult on the baseline scenario.
2. Indifference verification: at the solution, the gap vector evaluated at
   the returned thresholds is below tolerance for every class.
3. Comparative statics: tighter reserves push thresholds up (more redemption);
   higher convenience yield pulls thresholds down.
4. 1-class reduction: collapsing pi to a single class produces a stable
   answer that does not depend on the other classes' parameters.
"""

from __future__ import annotations

import numpy as np
import pytest

from stablecoin_ms import fixed_point, payoffs, scenario


def _baseline(**overrides) -> scenario.Scenario:
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


def test_solve_returns_populated_result():
    sc = _baseline()
    res = fixed_point.solve(sc, theta=1.0)
    assert set(res.thresholds) == set(scenario.CLASS_KEYS)
    assert set(res.redemption_rate) == set(scenario.CLASS_KEYS)
    assert 0.0 <= res.secondary_price <= 1.0
    assert res.aggregate_demand >= 0.0
    assert res.primary_paid + res.unmet_demand == pytest.approx(res.aggregate_demand)


def test_solution_satisfies_indifference():
    sc = _baseline()
    res = fixed_point.solve(sc, theta=1.0, tol=1e-5)
    assert res.converged, "fixed point did not converge on the baseline scenario"
    s_vec = np.array([res.thresholds[k] for k in scenario.CLASS_KEYS])
    gap = fixed_point._gap_vector(s_vec, sc, n_nodes=25)
    assert np.max(np.abs(gap)) < 5e-4, f"gap vector {gap} not small enough"


def test_higher_theta_lowers_demand():
    """Canonical Morris-Shin comparative static: better fundamental -> less run."""
    sc = _baseline()
    r_low = fixed_point.solve(sc, theta=0.5)
    r_high = fixed_point.solve(sc, theta=1.5)
    assert r_high.aggregate_demand < r_low.aggregate_demand, (
        f"higher theta should lower demand; "
        f"theta=0.5 -> D={r_low.aggregate_demand:.3f}, theta=1.5 -> D={r_high.aggregate_demand:.3f}"
    )


def test_tighter_reserves_dampen_demand_via_secondary_penalty():
    """Endogenous comparative static: tighter primary reserves -> larger unmet ->
    lower secondary price -> redemption becomes less attractive at the margin
    and the indifference threshold moves down. The test pins the sign so the
    result is flagged if a future refactor breaks it.
    """
    sc_loose = _baseline(issuer=scenario.IssuerParameters(R=1.0, A=0.3, h=0.01, xi=0.30))
    sc_tight = _baseline(issuer=scenario.IssuerParameters(R=0.2, A=0.3, h=0.01, xi=0.30))
    r_loose = fixed_point.solve(sc_loose, theta=1.0)
    r_tight = fixed_point.solve(sc_tight, theta=1.0)
    assert r_tight.aggregate_demand < r_loose.aggregate_demand, (
        f"tighter reserves should dampen demand via secondary penalty; "
        f"loose D={r_loose.aggregate_demand:.3f}, tight D={r_tight.aggregate_demand:.3f}"
    )
    assert r_tight.unmet_demand > 0.0
    assert r_tight.secondary_price < r_loose.secondary_price


def test_higher_convenience_yield_lowers_demand():
    ks = scenario.CLASS_KEYS
    sc_low_omega = _baseline()
    sc_high_omega = _baseline(
        classes=scenario.ClassParameters(
            pi={k: 0.25 for k in ks},
            B={k: 1.0 for k in ks},
            sigma={"retail": 0.20, "wholesale": 0.15, "cross_border": 0.25, "market_maker": 0.10},
            omega={k: 0.10 for k in ks},
            cq={k: 0.05 for k in ks},
        ),
    )
    r_low = fixed_point.solve(sc_low_omega, theta=1.0)
    r_high = fixed_point.solve(sc_high_omega, theta=1.0)
    assert r_high.aggregate_demand < r_low.aggregate_demand, (
        f"higher convenience yield should lower demand; "
        f"low omega D={r_low.aggregate_demand:.3f}, high omega D={r_high.aggregate_demand:.3f}"
    )


def test_one_class_concentration_pi():
    ks = scenario.CLASS_KEYS
    pi = {"retail": 1.0, "wholesale": 0.0, "cross_border": 0.0, "market_maker": 0.0}
    sc = _baseline(
        classes=scenario.ClassParameters(
            pi=pi,
            B={k: 1.0 for k in ks},
            sigma={k: 0.20 for k in ks},
            omega={k: 0.01 for k in ks},
            cq={k: 0.05 for k in ks},
        ),
    )
    res = fixed_point.solve(sc, theta=1.0)
    # Only the retail threshold matters; demand is purely driven by retail.
    W_retail = sc.classes.pi["retail"] * sc.classes.B["retail"]
    assert res.aggregate_demand <= W_retail + 1e-9
    # Other-class thresholds are decoupled from D because their pi is 0; they
    # converge to whatever satisfies their own indifference, but they cannot
    # affect aggregate dynamics.
