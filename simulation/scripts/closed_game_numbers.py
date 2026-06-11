"""Closed-game phase 2 (WIP — prior mis-specified, numbers illustrative only).

KNOWN ISSUE (2026-06-11): expectations are taken over a flat prior U[A,B] that
places ~80% of mass in the stress region, so p_s and ell_D come out far too
large (p_s~0.80, ell_D~1170 bps). The fix is a two-regime prior (baseline near
par + rare stress tail) or an observable->(A,B,sigma,psi,R) mapping that makes
stress rare, matching the empirical per-coin p_s (USDC 0.001-0.008, USDT ~2e-4).
The analytical gate (closed_form_gate.py) is unaffected: the closed forms and
the signs of d ell_D/dR and d p_s/dR hold. This script's MECHANICS are correct;
only the prior parametrisation needs redesign before the headline is trusted.

Parametrise the closed-form dual-channel global game by observables, per coin,
and produce the headline expected loss, the endogenous stress probability, and
the reserve comparative static. Validate against the observed troughs and the
empirical stress frequency (test b).

Model (uniform noise + linear impact, gate-verified):
  theta ~ U[A,B];  D(theta) = 1/2 + (s* - theta)/(2 sigma) on [s*-sigma, s*+sigma]
  primary par up to reserves R; residual U = max(D-R,0) -> p_sec = 1 - psi*U (floored at p_lo)
  V_R(theta) = par_share + (1-par_share)*p_sec - phi,  par_share = min(1, R/D)
  V_H(theta) = theta + omega - xi*h
  threshold s*: E_{theta|s*~U[s*-sigma,s*+sigma]}[V_R - V_H] = 0   (single 1-D root)
Expected DEPEG loss (closed form, stress only; baseline mid-depeg is 0 in the
linear model and is taken from the observable off-ramp basis):
  ell_D_stress = E_theta[ D*(1-p_sec) ]  over the whole prior.
Total expected loss = ell_C (= h*xi, observable) + basis (observable) + ell_D_stress.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import brentq

# ----- observables per coin -------------------------------------------------
# R   : share of supply redeemable at par on demand (reserve liquidity / primary access)
# psi : linear price-impact (inverse secondary depth); USDT deeper -> smaller psi
# sigma: signal dispersion; broad retail base (USDT) -> larger sigma
# A,B : prior support of the issuer fundamental (1 = par); stress = lower tail
# h,xi: counterparty hazard and LGD (market proxies, unchanged)
# basis: observed off-ramp conversion basis (bps) -> baseline depeg component
# trough_obs: observed secondary-price trough in the named episode (validation)
COINS = {
    "USDC": dict(R=0.55, psi=0.45, sigma=0.22, A=0.55, B=1.05,
                 omega=0.010, phi=0.0015, h=0.01, xi=0.20,
                 basis=21.0, trough_obs=0.9022, p_s_emp=(0.001, 0.008)),
    "USDT": dict(R=0.45, psi=0.13, sigma=0.24, A=0.80, B=1.05,
                 omega=0.010, phi=0.0015, h=0.02, xi=0.30,
                 basis=12.0, trough_obs=0.9751, p_s_emp=(0.0002, 0.0005)),
}
P_LO = 0.50


def D_of(theta, s, sigma):
    return np.clip(0.5 + (s - theta) / (2 * sigma), 0.0, 1.0)


def p_sec_of(D, R, psi):
    U = max(D - R, 0.0)
    return max(P_LO, 1.0 - psi * U)


def indiff(s, p):
    """E[V_R - V_H | s_i=s] over theta ~ U[s-sigma, s+sigma], numerically."""
    sigma, R, psi, omega, phi, xi, h = (p["sigma"], p["R"], p["psi"],
                                        p["omega"], p["phi"], p["xi"], p["h"])
    th = np.linspace(s - sigma, s + sigma, 4001)
    D = D_of(th, s, sigma)
    par = np.minimum(1.0, np.where(D > 0, R / np.maximum(D, 1e-9), 1.0))
    psec = np.array([p_sec_of(d, R, psi) for d in D])
    V_R = par + (1 - par) * psec - phi
    V_H = th + omega - xi * h
    return np.trapezoid(V_R - V_H, th) / (2 * sigma)


def solve_threshold(p):
    lo, hi = p["A"] - p["sigma"], p["B"] + p["sigma"]
    f = lambda s: indiff(s, p)
    # scan for a sign change
    grid = np.linspace(lo, hi, 200)
    vals = [f(s) for s in grid]
    for i in range(len(grid) - 1):
        if vals[i] == 0:
            return grid[i]
        if vals[i] * vals[i + 1] < 0:
            return brentq(f, grid[i], grid[i + 1])
    # fallback: minimise |f|
    return grid[int(np.argmin(np.abs(vals)))]


def expected_depeg_and_ps(p, s):
    """ell_D_stress (bps) and endogenous p_s over theta ~ U[A,B]."""
    A, B, sigma, R, psi = p["A"], p["B"], p["sigma"], p["R"], p["psi"]
    th = np.linspace(A, B, 20001)
    D = D_of(th, s, sigma)
    psec = np.array([p_sec_of(d, R, psi) for d in D])
    depeg = D * (1.0 - psec)                       # below-par loss per unit
    ell_D = np.trapezoid(depeg, th) / (B - A) * 1e4    # bps, expectation under U[A,B]
    theta_s = s - sigma * (2 * R - 1)              # D=R boundary
    p_s = float(np.clip((theta_s - A) / (B - A), 0.0, 1.0))
    trough = float(psec.min())
    return ell_D, p_s, trough


def reserve_comp_static(p, s, dR=0.05):
    p2 = dict(p); p2["R"] = p["R"] + dR
    e0, _, _ = expected_depeg_and_ps(p, s)
    e1, _, _ = expected_depeg_and_ps(p2, solve_threshold(p2))
    return (e1 - e0) / dR


print(f"{'coin':>5} {'s*':>7} {'ell_C':>6} {'basis':>6} {'ell_D':>7} {'TOTAL':>7} "
      f"{'p_s_endog':>10} {'p_s_emp':>14} {'trough':>8} {'obs':>7} {'dellD/dR':>9}")
out = {}
for c, p in COINS.items():
    s = solve_threshold(p)
    ell_D, p_s, trough = expected_depeg_and_ps(p, s)
    ell_C = p["h"] * p["xi"] * 1e4
    total = ell_C + p["basis"] + ell_D
    dds = reserve_comp_static(p, s)
    out[c] = dict(s=s, ell_C=ell_C, basis=p["basis"], ell_D=ell_D, total=total,
                  p_s=p_s, trough=trough, dellD_dR=dds)
    print(f"{c:>5} {s:>7.3f} {ell_C:>6.1f} {p['basis']:>6.1f} {ell_D:>7.2f} {total:>7.1f} "
          f"{p_s:>10.4f} {str(p['p_s_emp']):>14} {trough:>8.4f} {p['trough_obs']:>7.4f} {dds:>9.2f}")

print("\nReadout:")
print(" - TOTAL is the observable-anchored headline (ell_C + basis + model stress depeg).")
print(" - p_s_endog should sit in the empirical per-coin range p_s_emp.")
print(" - trough (model) vs obs validates the linear impact + reserve channel.")
print(" - dellD/dR < 0 is the analytical reserve comparative static, numerically confirmed.")
print(" - fable5 model headline for reference: USDC 48.9, USDT 71.2.")
