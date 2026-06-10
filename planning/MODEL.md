# Formal model — Morris-Shin global game on a payment infrastructure
*Draft 2026-06-01, Claude Code Opus 4.7 under author direction. For author review before simulation code is written.*

This memo states the model that backs the AFA 2027 submission. The notation is tight and the prose is short on purpose: this is the spec, not the paper.

## 0. Reading guide

The model has four layers. The first three are state variables and shocks; the fourth is the strategic stage. The Morris-Shin **fixed point lives in layer 4** and is the methodological core of the paper.

| Layer | Object | Role |
|-------|--------|------|
| 1 | Payment rails and corridors | Determines per-class congestion $q_k$ and incumbent-rail cost $c^{\text{inc}}_c$ in corridor $c$. |
| 2 | Issuer balance sheet | Determines liquid reserves $R$, illiquid asset value $A$, default hazard $h$. |
| 3 | Secondary market | Determines depth $M$ and the price-impact function $p^{sec}(\cdot)$. |
| 4 | Coordination stage | Solves the redemption fixed point $\{s^*_k\}$ given $(\theta, q_k, R, M, h)$. |

A Monte Carlo draw fixes a scenario (a triple of parameters $(R, M, h, q_k)$), draws $\theta$ from its prior, draws private signals $s_i$, then resolves the fixed point in layer 4 and reads off realised outcomes.

## 1. Agents, classes and stakes

The economy has $K$ classes, $k \in \mathcal K = \{\text{retail}, \text{wholesale}, \text{cross-border}, \text{market-maker}\}$. Within each class, agents are atomistic and ex-ante identical. Class $k$ has population share $\pi_k$ and per-capita stablecoin balance $B_k$, with aggregate stake $W_k = \pi_k B_k$ and total stake $W = \sum_k W_k$.

The market-maker class is kept for two reasons: it provides the arbitrage channel that connects fragmented venues, and it absorbs unmet primary redemptions. It is **not** a payment user; it does not pay corridor costs and does not enter the cost-benefit comparison of §6.

The end-user payment classes (retail, wholesale, cross-border) are each tied to one of the corridors:

| Class | Corridor | Incumbent rail |
|-------|----------|----------------|
| retail | US→MX | Wise (or equivalent fintech) |
| wholesale | EU→BR | SWIFT correspondent banking |
| cross-border | US→PHL | bank-account + fintech remittance benchmark (Wise / Remitly / WorldRemit average) |

The mapping is **one-to-one** to keep the comparison clean. Robustness exercises can permute corridor assignment.

## 2. Information

The latent issuer fundamental is $\theta \in \mathbb R$. Higher $\theta$ means the issuer can honour redemptions at par with higher probability. Agents share an improper uniform prior on $\theta$ (the standard simplification in the Morris-Shin literature that makes the fixed point clean). Each agent $i$ in class $k$ observes the private signal
$$s_i = \theta + \sigma_k \, \varepsilon_i, \qquad \varepsilon_i \sim \mathcal N(0,1), \quad \tau_k \equiv \sigma_k^{-2}.$$

Class-specific signal precision $\tau_k$ is the key informational lever. The natural ordering is $\tau_{\text{market-maker}} > \tau_{\text{wholesale}} > \tau_{\text{retail}} > \tau_{\text{cross-border}}$. Cross-border end users are by construction the least-informed end-user class, which is what makes them the most redemption-sensitive — the central comparative-statics result that the paper will explain endogenously rather than impose.

## 3. Strategies, payoffs and the dual-channel exit

Each agent chooses between **redeem** and **hold** in a single shot. The strategy is a threshold rule: redeem iff $s_i < s^*_k$.

Define the realised aggregate redemption mass given thresholds $\{s^*_k\}$ and fundamental $\theta$:
$$D(\theta; \{s^*_k\}) = \sum_{k} W_k \, \Phi\!\left(\frac{s^*_k - \theta}{\sigma_k}\right),$$
where $\Phi$ is the standard normal CDF. This uses that $\Pr(s_i < s^*_k \mid \theta) = \Phi((s^*_k-\theta)/\sigma_k)$.

**Dual-channel exit sequencing.** Every redeeming agent attempts primary redemption first. The issuer pays at par up to liquid reserves:
$$P(D) = \min\{D, R\}, \qquad U(D) = \max\{D-R, 0\}.$$
Unmet demand $U(D)$ spills to the secondary market and clears at price
$$p^{sec}(D) = \min\left\{ 1, \, \max\!\left[\underline p, \, 1 - \psi \left(\frac{U(D)}{\widetilde M(D)}\right)^\nu - \mu_q q - \xi h \right] \right\},$$
with depth erosion $\widetilde M(D) = M / (1 + \zeta U(D)/M)$.

The convexity parameter $\nu > 1$ captures the well-documented nonlinearity in secondary-price impact of stablecoin sell pressure (consistent with Watsky et al. 2024 and Lyons-Viswanath-Natraj 2023). The parameter $\xi$ scales the further markdown if the issuer defaults; $\mu_q$ is the secondary-market penalty when the rail is congested (reflects on-chain gas spikes when redemption demand is high).

**Per-agent payoff** of redeeming, given $(\theta, D)$:
$$V_R(D) = \underbrace{\min\!\left\{1, \tfrac{R}{D}\right\}}_{\text{primary share}} \cdot 1 \; + \; \underbrace{\left(1 - \min\!\left\{1, \tfrac{R}{D}\right\}\right)}_{\text{secondary share}} \cdot p^{sec}(D) - \phi,$$
where $\phi$ is the redemption transaction cost (gas + fee). Note $V_R$ does not depend on $\theta$ directly; the dependence runs through $D$.

**Per-agent payoff** of holding, given $\theta$ and the rail-state:
$$V_H(\theta) = \theta - c_q q + \omega.$$
Here $c_q q$ is the disutility of using a congested rail in this period and $\omega$ is the convenience yield of holding the stablecoin (programmability, 24/7 access, integration with on-chain markets). Both $c_q$ and $\omega$ are class-specific in practice; written without subscript for compactness.

This payoff structure delivers the standard global-games complementarity: when more agents redeem, $D$ rises, $p^{sec}$ falls, $V_R$ falls — but $V_H$ does not move, so the incentive to redeem rises only when $V_H$ itself is low (low $\theta$, congested rail). The complementarity comes from the secondary-market block, not from a direct payoff externality.

## 4. The fixed point

At the threshold $s^*_k$, the class-$k$ marginal agent is indifferent:
$$\boxed{\; E\!\left[V_R(D(\theta; \{s^*_j\})) - V_H(\theta) \mid s_i = s^*_k\right] = 0, \quad \forall k. \;}$$

This is a $K$-dimensional non-linear system. Under the improper-prior limit, the posterior over $\theta$ given $s_i = s^*_k$ is $\mathcal N(s^*_k, \sigma_k^2)$, which closes the expectation analytically up to the integral over $\theta$.

The integrand is well-behaved: $V_R(D)$ is monotone decreasing in $D$, and $D$ is monotone decreasing in $\theta$ (for any fixed $\{s^*_k\}$). Standard global-games arguments deliver existence; uniqueness of the threshold profile follows under bounded strategic complementarity, which is the condition $\sigma_k$ not too small relative to the price-impact slope. The simulation will report the convergence diagnostics directly.

The Monte Carlo loop is

1. Draw scenario parameters $(R, M, h, q_k, \{\sigma_k\}, \omega, c_q, \phi, \psi, \nu, \zeta, \mu_q, \xi, \underline p, \pi_k, B_k)$.
2. Draw $\theta$ from its prior.
3. Solve the $K$-dimensional fixed point above for $\{s^*_k(\theta, \cdot)\}$ by Newton-Krylov with a class-specific scalar warm-start derived from the reserve ratio, rail congestion and convenience yield.
4. Read off realised $D, p^{sec}, U, P$ and per-class redemption rates $R_k = \Phi((s^*_k - \theta)/\sigma_k)$.

Aggregate moments over $N$ draws give: average depeg probability $\Pr(p^{sec} < \bar p)$, queue ratio $q$ unchanged (it is a parameter here, not a state), per-class redemption distribution, etc.

## 4a. Regime-dependent dispersion of the fundamental

The θ-prior carries a precision $\tau$ that is calibrated separately for the two scenarios. In the **baseline regime**, $\tau$ is high — the issuer fundamental is concentrated tightly around $\theta_{baseline}$, so secondary-market prices are essentially deterministic across Monte Carlo draws and the model produces a near-par baseline as a structural property rather than as a numerical artefact. In the **stress regime**, $\tau$ is low — the fundamental is spread widely around $\theta_{stress}$, allowing the same calibrated $\{\sigma_k\}, \psi, \nu, \mu_q, \zeta\}$ block to produce a fat-tailed cross-section of $p^{sec}$ realisations. The regime-dependent dispersion is the structural device that lets a single set of microstructure parameters describe both calm and run-prone states without forcing the model to be uniformly noisy.

Implementation-wise, the calibration vector is twelve-dimensional: four class signal precisions, four secondary-block parameters $\{\psi, \nu, \mu_q, \zeta\}$, two regime means $\theta_{baseline}$ and $\theta_{stress}$, and two regime precisions $\tau_{baseline}$ and $\tau_{stress}$. The microstructure block is shared across regimes; only the prior of $\theta$ shifts.

## 5. Calibration strategy: anchor, policy event, falsification

**Anchor (March 2023 USDC depeg).** Sets the prior on $\theta$ (mean and tail) and the relative class signal precisions $\sigma_k$. The calibration targets the six moments computed in session 05 from the CryptoCompare USDC hourly series (`data/processed/usdc_march2023_targets.json`): baseline mean close, baseline std, baseline large-depeg frequency under $\bar p = 0.975$, stress minimum close, stress mean absolute depeg in basis points, and stress large-depeg frequency. $\{\sigma_k\}$ is identified from the heterogeneity in observed redemption timing across user classes, taken from on-chain redemption logs published by Circle and from secondary venue volumes.

**Policy event (Brazil ban on stablecoins for cross-border).** Identifies the cross-border end-user response by treating the ban as a discrete change in either $\omega_{\text{cross-border}}$ (programmability/access value drops to zero in the affected corridor) or, more sharply, as a forced reallocation of the stake $W_{\text{cross-border}}$ from the corridor's USD stablecoins to the incumbent SWIFT rail. The exercise asks whether the pre-ban equilibrium thresholds $s^*_k$ already priced this risk and how much welfare is lost or gained.

**Falsification (TerraUSD collapse, May 2022).** The model is designed for fiat-backed stablecoins with explicit reserves. TerraUSD had no reserves in the same sense: its peg was algorithmic, sustained by a partner token (LUNA) that itself derived value from the stablecoin's demand. Applying the same fixed point to UST should produce qualitatively different equilibrium behaviour — specifically, $\theta$ should become endogenously self-fulfilling rather than exogenous. If the model **does** match UST without modification, that is a red flag; if it fails to match unless reserves are formally set to zero and the recursive feedback is added, that is the desired result. Either way, the exercise is a falsification test, not a calibration target.

## 6. Cost-benefit metric: closing the loop with the incumbent rail

For corridor $c$ with stablecoin (class $k$ tied to $c$) and incumbent rail $i$, define the **per-unit certainty-equivalent cost** of using the stablecoin:

$$\mathrm{CEC}^{stbl}_c = \mathbb E_\theta\!\left[ \mathrm{fee}_c^{stbl} + (1 - p^{sec}(D))\, \mathbb 1\{s_i < s^*_k\} + c_q q + h \cdot \mathrm{LGD} \right] + \gamma_k \, \mathrm{Var}_\theta(p^{sec}(D)),$$

and for the incumbent rail:

$$\mathrm{CEC}^{inc}_c = \mathrm{fee}_c^{inc} + c^{\text{settle},inc}_c + \rho_c^{inc}.$$

The fee components $\mathrm{fee}^{stbl}_c, \mathrm{fee}^{inc}_c$ are observed (gas + DEX/CEX fees for stablecoins; per-corridor fee data from the World Bank Remittance Prices Worldwide quarterly database for the incumbent rail). The settlement-cost $c^{\text{settle},inc}_c$ proxies the cost of slow incumbent settlement (working capital tied up). The risk premium $\rho_c^{inc}$ proxies counterparty risk in the incumbent rail (rare for SWIFT major-currency corridors; non-trivial for EU→BR through certain corresponding banks).

The **breakeven condition** is $\mathrm{CEC}^{stbl}_c = \mathrm{CEC}^{inc}_c$. The paper reports the realised level of $\theta$, of $W_{\text{cross-border}}$ and of $M$ at which the breakeven holds, and shows how the breakeven moves under the Brazil ban event. This is the empirical cost-benefit answer the author requested in the brief.

## 7. What is in this memo and what is not

- **In:** the strategic and informational structure, the fixed-point statement, the calibration logic and the cost-benefit metric. These four together are sufficient to start writing the simulation.
- **Not in yet:** functional forms for the convenience yield $\omega(\cdot)$, the full identification argument for $\{\sigma_k\}$, the formal proof of uniqueness of the threshold profile (it will be stated in the paper as a proposition with assumptions, not derived in full here), and the specific Newton-Krylov tolerance and warm-start scheme — these go in `simulation/` once the author signs off on this memo.

## 8. Author ruling on the open question (2026-06-01)

**Wholesale class stays in the cost-benefit comparison as a robustness null.** §6 reports three corridors:

| Corridor | Class | Incumbent rail | Expected net metric |
|----------|-------|----------------|----------------------|
| US→MX | retail | Wise (or equivalent fintech) | Stablecoin can dominate when incumbent fee plus settlement-cost combination is high. |
| US→PHL | cross-border | bank-account + fintech remittance benchmark (Wise / Remitly / WorldRemit average) | Stablecoin can dominate when corridor friction is high (mean RPW 2023-2024 ≈ 4.64 %, 16 firms in RPW). |
| EU→BR | wholesale | TARGET2-leg + correspondent → BR RTGS | Negative-by-construction null. The paper will show the negative sign as a sanity check on the metric and as a falsification of the claim that stablecoins are universally welfare-improving for payments. |

The null result for the wholesale corridor is itself a paper-worthy point: it tightens the headline by exhibiting the corridor where the stablecoin does not pay off and grounds the segmentation claim quantitatively. The §6 metric is computed identically across the three corridors; only the sign of the realised $\mathrm{CEC}^{stbl}_c - \mathrm{CEC}^{inc}_c$ is allowed to flip.
