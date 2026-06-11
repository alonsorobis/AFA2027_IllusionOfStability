# Closed-game version — design document

**Opened:** 2026-06-11. **Status:** scaffold (exact copy of fable5, paths retargeted, compiles 58 pp).
**Parent:** `paper/fable5/` stays the canonical submission version; this is a parallel methodological rewrite.

## Why this version exists

The referee test (b) of 2026-06-11 (`simulation/scripts/test_reduced_form_depeg.py`,
`data/processed/reduced_form_depeg_test.json`) showed that the headline expected loss is
recoverable from observables and econometrics without the six-moment high-frequency
calibration:

| Component | fable5 model | reduced (observable + econometrics) |
|-----------|--------------|-------------------------------------|
| counterparty ell_C | 20 / 60 | h·xi market proxies = 20 / 60 |
| baseline depeg ell_D,b | 26.4 / 10.9 | off-ramp basis = 21 / 12 (observable) |
| stress depeg ell_D,s (wtd) | 2.6 / 0.3 | p_s × episode depth = 0.0108×240 / 0.0108×28 = 2.6 / 0.3 |
| **total** | **48.9 / 71.2** | **≈ 43.6 / 72.3** |

The empirical below-par depeg at the USD-pair mid is only 1.3 (USDC) / 2.1 (USDT) bps over
38,688 hours, so the baseline component is carried by the observed basis, not by the model;
the stress component equals p_s times the observed episode depth. The model therefore earns
its place through **mechanism and counterfactuals**, not through the number. This version
makes that the explicit thesis and adopts a Klee-style closed-form so the causal/counterfactual
properties are analytical, contrasted against econometrics, with no moment-matching.

## What is kept from fable5

- The risk-adjusted-cost framing and the full payment circuit (on/off-ramp, basis, on-chain fee).
- ell_C = h·xi from market proxies (attestations, BB–B default frequencies). Unchanged.
- The corridor comparison (UC1–3, Nexus overlay) and the policy section (non-homogeneity,
  build-versus-license).
- All visuals: SVB/Terra on-chain figures, the cross-section trough map, the decomposition
  figure, the coordination-structure schematic.
- The econometric mechanism check (daily depeg on net redemption outflow, the USDC kink) and
  the cross-section of troughs — these become the **empirical counterpart** the closed-form
  is tested against, promoted from a side check to a co-equal pillar.

## What is removed

- The seven-parameter calibration by matching six high-frequency moments
  (`simple_calibration`, the Newton–Krylov fixed point search, the loss function).
- The Jacobian / SVD / effective-rank identification apparatus (Appendix A3 in its current form).
- The calibration bootstrap (no calibration to bootstrap; uncertainty now comes from the
  observable inputs — basis dispersion, episode depth, (h,xi) range).

## What is derived new (closed-form, à la Klee FEDS 2026-037)

A global game with **linear price impact + uniform signal noise**, which Klee shows yields a
closed-form threshold. The open analytical question for this version is whether the closed
form survives our **dual-channel exit** (primary redemption up to reserves R, residual into a
secondary market with price impact). Targets:

1. **Threshold s\*** in closed form (or a one-line implicit equation), under
   `p_sec(D) = 1 − ψ·max(D−R,0)` (linear, ν=1, no depth erosion ζ=0, no congestion) and
   `ε_i ~ U[−a,a]`.
2. **Endogenous per-coin stress probability p_s** as a function of (R, ψ, σ, fundamentals) —
   the Klee-style run probability, estimated separately for USDC and USDT instead of the shared
   96/8856 = 0.0108. (The empirical per-coin frequencies from test (b): USDC ≈ 0.001–0.008,
   USDT ≈ 0.0002, both far below 0.0108.)
3. **Expected depeg loss** `ell_D = E_θ[ D(θ)(1 − p_sec(D(θ))) ]` in closed or semi-closed form
   by integrating over the fundamental distribution.
4. **Analytical comparative statics**: ∂ell_D/∂R, ∂ell_D/∂ψ (depth), ∂p_s/∂R, ∂s\*/∂ω. These
   are the causal/counterfactual properties — proved, not simulated.

## How it is contrasted with econometrics (the test-(b) logic, built in)

- **Threshold**: the model's kink at U = D − R = 0 vs the empirical kink in the depeg-on-outflow
  regression (USDC flat until ~1.1% outflow, then convex; already estimated).
- **Run probability**: endogenous p_s(coin) vs the empirical stress frequency per coin.
- **Level**: closed-form ell_D vs the reduced-form ell_D (basis + p_s×episode depth). If they
  agree, the model is disciplined, not inflationary; the agreement is reported, not hidden.

## Paper structure (closed_game)

§1 intro (same framing, closed-form method) · §2 lit (position vs Klee closed-form and vs the
moment-matching tradition we deliberately avoid) · §3 risk factors · **§4 closed-form global
game** (linear impact + uniform noise: threshold, endogenous p_s, analytical comparative
statics) · **§5 parametrisation by observables + econometric contrast** (replaces the calibration
section: R from reserves, ψ from order-book depth, σ from signal dispersion; mechanism check;
per-coin p_s; level cross-check) · §6 corridor comparison · §7 policy · §8 conclusion.
Appendices: closed-form proofs; cost data. No identification appendix.

## Work plan (phases)

1. **Analytics first (gate).** Derive the dual-channel closed-form threshold and ell_D on paper
   (sympy where useful). If the dual channel breaks the closed form, decide: (a) drop primary
   redemption into the secondary as one channel with a kink, or (b) keep a one-line implicit
   threshold. This gate decides feasibility before any prose is touched.
2. Rewrite §4 with the closed-form model; rewrite §5 as parametrisation-by-observables +
   econometric contrast; delete the calibration/identification machinery.
3. Recompute the headline from the observable parametrisation; confirm it tracks 48.9 / 71.2.
4. Reposition §2 and the intro; keep all figures; build the closed_game internet appendix if needed.
5. Hyphen audit + compile; log.

## Numbers to preserve as anchors (from test (b) and fable5)

USDC ell_C 20, basis ~21, episode depth 240 bps, empirical p_s 0.001–0.008, headline ~44–49.
USDT ell_C 60, basis ~12, episode depth 28 bps, empirical p_s ~0.0002, headline ~71–72.
