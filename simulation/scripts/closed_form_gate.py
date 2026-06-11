"""Closed-game analytical gate: does the dual-channel global game admit a closed
form under uniform signal noise + linear price impact (Klee-style)?

Setup
-----
Fundamental theta ~ U[A, B]. Each holder i sees s_i = theta + sigma*eps_i with
eps_i ~ U[-1, 1], so given theta the redeeming mass under threshold s* is
    D(theta) = 1/2 + (s* - theta)/(2 sigma)   on theta in (s*-sigma, s*+sigma),
D = 1 below, D = 0 above. Primary redemption pays par up to reserves R; residual
U = max(D - R, 0) hits a secondary market with LINEAR impact
    p_sec(D) = 1 - psi * U.
The priced object is the expected below-par depeg loss
    ell_D = E_theta[ D(theta) * (1 - p_sec(D(theta))) ] = E_theta[ D * psi * max(D-R,0) ].

Stress region: D > R  <=>  theta < theta_s := s* - sigma*(2R - 1).
This script verifies (i) ell_D is closed form, (ii) d ell_D / dR is closed form,
(iii) the endogenous per-coin stress probability p_s is closed form.
"""
import sympy as sp

theta, s, sigma, psi, R, A, B = sp.symbols("theta s sigma psi R A B", positive=True)

# redeeming mass on the interior ramp
D = sp.Rational(1, 2) + (s - theta) / (2 * sigma)

# stress boundary: D = R
theta_s = sp.solve(sp.Eq(D, R), theta)[0]
print("theta_s (D=R boundary):", sp.simplify(theta_s))           # = s - sigma(2R-1)

# uniform prior density
f = 1 / (B - A)

# --- region 1: full-run plateau, theta in (A, s-sigma): D = 1, depeg = psi*(1-R)
depeg_plateau = psi * (1 - R)
I_plateau = sp.integrate(depeg_plateau * f, (theta, A, s - sigma))

# --- region 2: ramp in stress, theta in (s-sigma, theta_s): depeg = psi*D*(D-R)
depeg_ramp = psi * D * (D - R)
I_ramp = sp.integrate(depeg_ramp * f, (theta, s - sigma, theta_s))

ell_D = sp.simplify(I_plateau + I_ramp)
print("\nell_D (closed form):")
sp.pprint(ell_D)

# comparative static wrt reserves R (Leibniz: R in integrand AND in theta_s limit)
dell_dR = sp.simplify(sp.diff(ell_D, R))
print("\nd ell_D / dR (closed form):")
sp.pprint(dell_dR)

# sign check at a representative interior calibration
subs = {psi: sp.Rational(3, 10), sigma: sp.Rational(2, 10), R: sp.Rational(6, 10),
        s: 0, A: -1, B: 1}
print("\nnumeric ell_D at (psi=.3,sigma=.2,R=.6,s=0,A=-1,B=1):",
      sp.nsimplify(ell_D.subs(subs)), "=", float(ell_D.subs(subs)))
print("numeric d ell_D/dR there:", float(dell_dR.subs(subs)),
      "  (expect < 0: deeper reserves lower the expected depeg loss)")

# --- endogenous per-coin stress probability p_s = P(theta < theta_s)
p_s = sp.simplify((theta_s - A) / (B - A))
print("\np_s endogenous (closed form):")
sp.pprint(p_s)
dps_dR = sp.simplify(sp.diff(p_s, R))
print("d p_s / dR:", dps_dR, " (expect < 0)")

# --- threshold indifference equation F(s*)=0 (states it is one equation in one
# unknown; the primary prorating R/D term makes it transcendental via a log, but
# it is a single 1-D root, not a 7-parameter fixed point).
print("\nThreshold: marginal holder s_i = s* indifferent, theta|s* ~ U[s*-sigma, s*+sigma].")
print("F(s*) = E[V_R - V_H | s*] = 0, a single 1-D equation (log term from R/D prorating).")
print("Comparative statics by implicit function theorem: ds*/dR = -F_R / F_{s*}.")
