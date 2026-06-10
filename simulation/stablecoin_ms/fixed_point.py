"""Morris-Shin K-dimensional threshold solver.

Solves the system
    E[V_R(D(theta; {s*_j})) - V_H(theta) | s_i = s*_k] = 0,  k = 1..K
for the threshold profile {s*_k}.

Strategy
--------
1. Warm-start with a class-specific scalar derived from the issuer reserve
   ratio and the user-side congestion term. This is intentionally cruder
   than a full logistic solve so that it does not bias the iterate near a
   spurious basin.
2. Solve with `scipy.optimize.root(method='krylov')` on the K-vector gap.
3. Fall back to damped fixed-point iteration if the Krylov solver returns
   a non-convergent flag.
4. Populate a `DrawResult` with realised D, p_sec, per-class redemption
   rates and convergence diagnostics.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
from scipy.optimize import root
from scipy.stats import norm

from .issuer import primary_payment, unmet_demand
from .payoffs import aggregate_demand, expected_indifference_gap
from .scenario import CLASS_KEYS, DrawResult
from .secondary import secondary_price


def logistic_warm_start(scenario, theta: float) -> Dict[str, float]:
    """Initial guess for the threshold profile.

    Heuristic: the threshold should sit near the realised theta when the
    issuer is solvent and slightly above it when stressed. Without solving
    a full logistic at this stage, we use

        s*_k(warm) = theta + sigma_k * Phi^{-1}(p_k)

    where p_k is a class-specific probability driven by the issuer reserve
    ratio, the rail queue and the convenience yield. This puts the warm
    start in the right basin without anchoring it to the answer.
    """
    R = scenario.issuer.R
    W = scenario.total_stake()
    reserve_ratio = R / W if W > 0 else 1.0
    out: Dict[str, float] = {}
    for k in CLASS_KEYS:
        sigma_k = scenario.classes.sigma[k]
        omega_k = scenario.classes.omega[k]
        cq_k = scenario.classes.cq[k]
        q_k = scenario.rails.q[k]
        # crude prior probability of redeeming at the warm start
        base = 0.3
        liq_push = 0.4 * (1.0 - reserve_ratio)        # tighter reserves -> redeem more
        cong_push = 0.2 * cq_k * q_k                   # higher congestion -> redeem more
        omega_pull = -0.3 * omega_k                    # more convenience -> redeem less
        p_k = float(np.clip(base + liq_push + cong_push + omega_pull, 0.01, 0.99))
        out[k] = theta + sigma_k * float(norm.ppf(p_k))
    return out


def _gap_vector(
    s_vec: np.ndarray,
    scenario,
    n_nodes: int,
) -> np.ndarray:
    """Stack the K class indifference gaps into a vector."""
    thresholds = dict(zip(CLASS_KEYS, [float(x) for x in s_vec]))
    out = np.empty(len(CLASS_KEYS), dtype=float)
    for i, k in enumerate(CLASS_KEYS):
        out[i] = expected_indifference_gap(
            s_star_k=thresholds[k],
            other_thresholds=thresholds,
            scenario=scenario,
            k=k,
            n_nodes=n_nodes,
        )
    return out


def _damped_fixed_point(
    scenario,
    theta: float,
    s0: np.ndarray,
    tol: float,
    maxiter: int,
    n_nodes: int,
    damping: float = 0.5,
) -> Tuple[np.ndarray, bool, int]:
    """Fallback: damped fixed-point iteration on the gap vector.

    Update rule: s_{t+1} = s_t - damping * gap(s_t). Damping factor is
    enough to suppress overshoot when the Newton-Krylov fallback fires.
    """
    s = s0.copy()
    for it in range(1, maxiter + 1):
        g = _gap_vector(s, scenario, n_nodes)
        norm_g = float(np.linalg.norm(g, np.inf))
        if norm_g < tol:
            return s, True, it
        s = s - damping * g
    return s, False, maxiter


def solve(
    scenario,
    theta: float,
    tol: float = 1e-6,
    maxiter: int = 200,
    n_nodes: int = 25,
) -> DrawResult:
    """Solve the K-dimensional fixed point at one (theta, scenario) draw."""
    warm = logistic_warm_start(scenario, theta)
    s0 = np.array([warm[k] for k in CLASS_KEYS], dtype=float)

    converged = False
    iterations = 0
    s_final = s0
    try:
        sol = root(
            _gap_vector,
            s0,
            args=(scenario, n_nodes),
            method="krylov",
            tol=tol,
            options={"maxiter": maxiter, "fatol": tol},
        )
        if sol.success:
            converged = True
            s_final = sol.x
            iterations = int(sol.nit) if hasattr(sol, "nit") else 0
        else:
            s_final, converged, iterations = _damped_fixed_point(
                scenario, theta, s0, tol, maxiter, n_nodes
            )
    except Exception:
        s_final, converged, iterations = _damped_fixed_point(
            scenario, theta, s0, tol, maxiter, n_nodes
        )

    thresholds = {k: float(v) for k, v in zip(CLASS_KEYS, s_final)}
    D = aggregate_demand(thresholds, theta, scenario)
    R = scenario.issuer.R
    U = unmet_demand(D, R)
    P = primary_payment(D, R)
    p_sec = secondary_price(
        U=U,
        M=scenario.secondary.M,
        psi=scenario.secondary.psi,
        nu=scenario.secondary.nu,
        mu_q=scenario.secondary.mu_q,
        q=float(np.mean(list(scenario.rails.q.values()))),
        xi=scenario.issuer.xi,
        h=scenario.issuer.h,
        p_underbar=scenario.secondary.p_underbar,
        zeta=scenario.secondary.zeta,
    )
    redemption_rate = {
        k: float(norm.cdf((thresholds[k] - theta) / scenario.classes.sigma[k]))
        for k in CLASS_KEYS
    }
    return DrawResult(
        theta=float(theta),
        thresholds=thresholds,
        redemption_rate=redemption_rate,
        aggregate_demand=float(D),
        primary_paid=float(P),
        unmet_demand=float(U),
        secondary_price=float(p_sec),
        converged=bool(converged),
        iterations=int(iterations),
    )
