# Scope, research question and decision points
*Draft 2026-06-01, Claude Code Opus 4.7 + author brief. To be confirmed by the author before any simulation or paper code is written.*

## 1. Working research question

> When stablecoins enter a payment use case, the apparent unit stability of the token coexists with a state-contingent fragility that becomes endogenously larger as adoption rises. **In a calibrated microstructure model where redemption is a Morris-Shin coordination game with two exit channels (primary redemption and secondary sale) and rail-level congestion, when does the cost-benefit balance of the stablecoin dominate the relevant incumbent payment rail, and when does it not?**

Three sub-questions, each tied to one channel:

1. **Liquidity risk channel.** How does redemption queue length and settlement congestion change the marginal cost of using a stablecoin for a given payment corridor, conditional on the endogenous run probability?
2. **Counterparty / depeg risk channel.** How does the endogenous coordination threshold in the global game shift the expected loss from non-par exit, as a function of issuer reserve quality and signal precision?
3. **Policy event channel.** How does a discrete policy shock — Brazil's announced ban on stablecoins for cross-border payments is the leading candidate — re-anchor the equilibrium and shift the cost-benefit balance for affected corridors?

These three are intentionally separable: each isolates one of the risk dimensions the author flagged (colas de redemption, contrapartida, depeg) and each can be reported as a stand-alone result in the paper.

## 2. What stays inside the model and what stays outside

| In scope | Out of scope |
|----------|--------------|
| Heterogeneous agents (small number of classes, parsimony). | Macro/general equilibrium with monetary-policy transmission. |
| Dual-channel exit (issuer primary + secondary market). | Banking-sector reallocation, deposit substitution. |
| Endogenous Morris-Shin fixed point for redemption thresholds. | Endogenous validator economics or token supply policy. |
| Multi-rail congestion (kept minimal, parsimonious). | Smart-contract risk, oracle attacks, MEV at the protocol layer. |
| Calibration to identifiable coordination events. | Cross-country adoption forecasting. |
| Cost-benefit comparison vs at most three incumbent rails. | Welfare evaluation for the central bank. |

The author specifically asked to avoid general equilibrium and to stay inside microstructure. The line above is drawn accordingly.

## 3. Methodology

The coordination stage is a standard Morris-Shin global game with class heterogeneity, dual-channel exit (issuer primary + secondary market) and rail-level congestion. Each agent $i$ in class $k$ observes $s_i = \theta + \sigma_k \varepsilon_i$, follows a threshold rule $s^*_k$, and redeems iff $s_i < s^*_k$. The system is solved per Monte Carlo draw of $\theta$ as a $K$-dimensional fixed point: the indifference condition at $s^*_k$, the secondary-price equation, and the consistency between aggregate redemption mass and the threshold profile.

The class structure delivers heterogeneous thresholds and heterogeneous strategic complementarity. This is the source of the *illusion of stability* claim: a single observed unit price can be consistent with very different state-contingent thresholds across user classes, so the same instrument can look stable in ordinary states while concealing a steeply state-contingent fragility in the segments most relevant for payments.

Within the published run-theoretic literature on stablecoins, the closest models are surveyed in [`LITERATURE_GAP.md`](LITERATURE_GAP.md). The model here differs by jointly carrying class-heterogeneous Morris-Shin thresholds, an explicit payment-rail congestion block coupled to the indifference condition, and a corridor-level certainty-equivalent comparison against a named incumbent rail.

## 4. Cost-benefit metric: how the paper closes the loop

For each payment corridor $c$ and each agent class $k$, the model produces:

- **Benefit side**: per-unit transaction cost saved vs the incumbent rail ($\Delta \text{fee}_c$), settlement-speed gain ($\Delta t_c$) and reach gain (binary, for corridors where the incumbent is absent or restricted).
- **Cost side**: expected per-unit haircut $E[1 - p^{sec} \mid \theta]$ under the endogenous Morris-Shin solve, expected delay from queue congestion $E[q]$, expected loss from issuer default $E[\text{hazard}\cdot \text{LGD}]$.
- **Net metric**: per-unit certainty-equivalent cost of using the stablecoin minus per-unit cost of the incumbent rail, integrated over the joint distribution of $\theta$ and the rail-state. A positive net metric means the stablecoin dominates; a negative net metric means the incumbent rail dominates; the value where the metric crosses zero is the **breakeven coordination state** that the paper highlights.

Reference incumbent rails to compare against:

- **Domestic retail**: PIX (Brazil), FedNow (US), SEPA SCT Inst (EU).
- **Domestic wholesale**: TARGET2 / Fedwire equivalents — comparison is mostly nominal here because stablecoins are not credible substitutes; useful as a robustness null.
- **Cross-border**: SWIFT correspondent banking, Wise (or equivalent fintech rails), and selectively the corridor-specific local instant scheme when an interoperability link exists.

The author asked for an empirical idea of cost-benefit, not a structural welfare statement. The certainty-equivalent representation is the minimum theoretical commitment that delivers a clean comparison.

## 5. Candidate calibration events

The endogenous fixed point becomes interesting only when calibrated to a coordination shock whose timing and identification are clean. Shortlist:

| Event | Date | Pros | Cons |
|-------|------|------|------|
| **March 2023 USDC depeg** | 10–13 Mar 2023 | Clean confidence shock for a fiat-backed stablecoin; high-frequency hourly data available; identifies the $\theta$-distribution and class-specific signal noise via the realised cross-section of redemption activity. | Single asset, single venue. Useful as **anchor**, paired with a policy-channel event for cross-corridor identification. |
| **Brazil ban on stablecoins for cross-border payments** | Announced 2025; in force during 2026 window | Clean policy discontinuity; cross-border corridor; identifies the policy-channel sub-question. | Effects partly anticipatory; data on actual flow displacement still thin in mid-2026. |
| **EU MiCA stablecoin de-listings (Tether, others)** | 2024–2025 EU MiCA enforcement | Discrete regulatory event, multi-corridor effect, lots of disclosure. | Less of a Morris-Shin coordination story, more of a compliance one. |
| **TerraUSD collapse** | May 2022 | Canonical coordination failure; rich event data. | Algorithmic stablecoin; different model class. Useful as **robustness/falsification** target only. |
| **Hong Kong stablecoin licence regime first issuance** | 2025 | Positive shock to confidence in HKD-pegged stablecoins; corridor-specific. | Effect size likely small at horizon visible by 2026-08. |
| **Argentina dollarisation / Milei stablecoin debate** | 2024–2026 | High informational asymmetry; clear coordination flavour. | Hard to map to a discrete identification moment. |

**Author decision needed.** Proposed default: March 2023 USDC as the anchor for $\theta$-distribution and reserve depth, Brazil ban as the cross-border policy-channel event, TerraUSD as the robustness target.

## 6. Data

- Refresh prices, supply and on-chain stablecoin metrics from open sources (Coinbase Advanced Trade and CryptoCompare candles, DefiLlama supplies, FRED macro controls, World Bank remittance share of GDP and Remittance Prices Worldwide) for the period 2022-01-01 through 2026-05-31.
- Complement with: Banco Central do Brasil cross-border statistics (SGS endpoints + named PDF reports for the Brazil cross-border stablecoin ban), and corridor-specific incumbent-rail price snapshots where the RPW panel does not cover the corridor.
- Treat each data download as a logged operation in `data/download_log.md` with timestamp, source URL, output file and SHA256.

## 7. Outlets and positioning

The model is finance microstructure on a payment infrastructure, with a clean methodological contribution. Plausible outlets:

1. **AFA 2027 Special Session** — the immediate target. Requires AI-workflow evidence (handled by this folder).
2. **Journal of Economic Dynamics and Control** — natural home for the calibrated global-game ABM if AFA does not select.
3. **Journal of Financial Stability / Journal of Banking & Finance** — viable if the policy-event angle (Brazil ban, MiCA) is foregrounded.
4. **Review of Asset Pricing Studies** — if the secondary-market microstructure block is the dominant contribution.

Positioning sentence the paper has to support by Section 1: *"This paper isolates the conditions under which a stablecoin payment use case is welfare-improving in the certainty-equivalent sense, by solving the coordination problem at the heart of stablecoin redemption endogenously and by mapping the solution to the cost structure of the relevant incumbent rail."*

## 8. Decision points the author must rule on before code is written

> **Status 2026-06-01:** the author confirmed the four structural rulings below in session 01. The remaining items (corridor specificity, notebook reuse) are resolved by following the recommended defaults given the four locked decisions.

**Author rulings (2026-06-01):**

- **A. Cost-benefit comparison:** *bilateral per corridor.* Stablecoin vs one named incumbent rail for each corridor in the empirical exercise.
- **B. Calibration events:** *March 2023 USDC depeg as anchor + Brazil's stablecoin cross-border ban as policy-channel event + TerraUSD collapse as falsification/robustness target.*
- **C. Corridor specificity (implicit in A):** *three named corridors* — US→Mexico (retail class, Wise / fintech benchmark), US→Philippines (cross-border class, fintech remittance benchmark), EU→Brazil (wholesale class, TARGET2 leg + correspondent → BR RTGS). The corridor mapping was revised in session 06 after the RPW panel for 2023–2024 turned out to have no US→Argentina coverage; the US→Philippines corridor was picked instead because it has 496 RPW observations across 16 firms, sits at a clean mean total cost of 4.64 %, and is a well-documented stablecoin-remittance use case.
- **D. Time horizon:** *one-shot game per Monte Carlo draw.* Reserves, depth and rail-state are scenario parameters; no across-period state evolution.
- **E. Encuadre:** *AFA-first, JEDC as alternative outlet.* Intro stays in finance microstructure; a JEDC-flavoured intro is kept as a parallel branch but not the main file.
- **F. Existing notebook (`../stablecoin_global_games_exercise.ipynb`):** *do not port.* Build `simulation/` from scratch from 2026-06-01 inside logged sessions, per the AFA timing rule.

The original A–F list below is left for the audit trail.

### Original A–F prompts presented to the author

A. **Scope of the cost-benefit comparison.** Three options, ranked by the author later:
   1. Bilateral: stablecoin vs one incumbent per corridor (cleanest, easiest to write up).
   2. Multilateral: stablecoin vs incumbent + one additional candidate (fintech, RTGS extension, instant-payment interlink).
   3. Coalitional: stablecoin coexistence with incumbent, with an endogenous share split. *Out of scope per the no-GE rule, listed only for completeness.*

B. **Calibration events.** Confirm or revise the shortlist in §5. Default: USDC March 2023 + Brazil ban + TerraUSD as robustness.

C. **Corridor specificity.** Two options:
   1. **Synthetic corridor**, parameterised, generic. Permits cleaner identification of mechanisms.
   2. **Three named corridors**: US→Mexico, US→Argentina, EU→Brazil. Gives the paper an empirical hook and makes Brazil-ban calibration natural. Recommended.

D. **Time horizon of the simulation.** Two options:
   1. **One-shot game per Monte Carlo draw**, with the fixed point solved per draw. Computationally cheap, cleaner to expose theoretically.
   2. **Multi-period with state evolution** (reserves and depth evolve, agents update beliefs). Richer, but moves toward dynamic GE which the author wants to avoid. Recommended: one-shot per draw.

E. **Position of the paper.** Two options:
   1. **Finance microstructure** lens, AFA-first framing.
   2. **Computational economics** lens, JEDC-first framing.
   Both can be written from the same model; only the introduction and policy framing differ. Recommended: write the finance microstructure lens first (AFA-first), keep a JEDC-flavoured intro as a parallel branch.

F. **Use of the existing notebook.** `Stablecoins/stablecoin_global_games_exercise.ipynb` predates 2026-06-01. Two options:
   1. Treat it as background only and rebuild simulation code from scratch under `simulation/`.
   2. Port pieces of it with a clear in-file note that the port happened on 2026-06-01 inside an AI-supervised session.
   Recommended: option 1 (strictly clean from 2026-06-01 onward).

## 9. Immediate next step on author confirmation

Once A–F are answered, the next session will:

1. Write a one-page formal model statement under `planning/MODEL.md` with the Morris-Shin fixed-point equations.
2. Stand up `simulation/` with the project skeleton (no science yet, only structure).
3. Refresh the public data through 2026-05-31 and log each download.
4. Translate the bibliography under `literature/` and set up a `.bib` file specific to this paper.
