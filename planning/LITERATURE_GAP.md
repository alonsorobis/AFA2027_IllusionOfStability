# Literature gap — where the AFA paper lives
*Draft 2026-06-01, Claude Code Opus 4.7 reading the four closest papers in the JoES library under author direction.*

This memo positions the AFA paper against the four most directly competing papers on stablecoin runs as global games. The objective is to make sure the planned contribution is genuinely incremental before any simulation code is written. References are to PDFs the author already has in `../JoES/library/pdfs/`; pages cited are from those PDFs.

## 1. The four nearest papers and what each does

### 1.1 Ahmed, Aldasoro and Duley (2024, BIS WP 1164, rev. Jan 2025) — *Public information and stablecoin runs*

- **Run model**: a Morris-Shin global game of regime change applied to stablecoin par convertibility (pp. 2–3 of the PDF). Holders observe noisy signals about the dollar value of reserves and decide redeem vs hold at a final date; par is defended whenever a sufficiently small mass redeems.
- **Methodological promotion over Morris-Shin (2003)**: the volatility of reserve assets is **unknown**, so the game becomes a second-generation global game à la Morris and Yildiz (2019) with multiple locally-unique equilibria. Rank beliefs about the issuer's ability to honour conversion become the key state.
- **Key finding**: greater transparency is not unambiguously stabilising. With weak priors about reserve quality, more transparency raises run risk; with strong priors, more transparency reduces it. Quality and transparency have distinct effects on issuer failure risk.
- **Empirical**: case studies with synthetic control, anchored on the USDC March 2023 event.
- **What is one and the same as in this paper**: the use of a global game with Morris-Shin signals to model the redemption decision; reliance on USDC March 2023 as calibration evidence; framing the issuer reserve as the fundamental.
- **What is different**: Ahmed-Aldasoro-Duley use one representative holder class and study the **transparency–quality trade-off**. They do not couple the game to a payment infrastructure, do not solve a heterogeneous-class fixed point, and do not produce a cost-benefit comparison against incumbent rails. Their second-generation extension is on the information structure; the present paper's extension is on the **heterogeneity of payoff and signal structure across user classes mapped to payment corridors**.

### 1.2 Ma, Zeng and Zhang (2025, NBER WP 33882) — *Stablecoin runs and the centralization of arbitrage*

- **Run model**: a two-layered market structure with a profit-maximising issuer, a small set of authorised arbitrageurs allowed to redeem at $1, and a continuum of investors who can only trade in a competitive secondary market (pp. 3–4 of the PDF).
- **Headline empirical fact**: arbitrage is concentrated — USDT averages only six redeemers per month with the top arbitrageur accounting for 66 % of redemption activity, versus 521 active redeemers for USDC (p. 3).
- **Key theoretical result**: a counterintuitive trade-off between price stability and run risk. More efficient arbitrage lowers price impact for sellers in the secondary market, which reduces the strategic substitutability that would otherwise discourage selling, and therefore **increases run risk**. Issuers optimally choose a finite degree of arbitrage concentration.
- **What is one and the same as in this paper**: the dual-channel exit (issuer-primary at par vs secondary at $p^{sec}$), the role of secondary-market depth, and the linkage between liquidity transformation on the issuer side and run risk on the holder side.
- **What is different**: Ma-Zeng-Zhang have **two** classes — arbitrageurs and investors — but **investors are homogeneous** and trade competitively. The strategic complementarity comes from the issuer's liquidity transformation, not from heterogeneous private signals across user classes. They do not model payment corridors, do not have a payment-congestion block, and do not produce a cost-benefit comparison.

### 1.3 Gorton, Klee, Ross, Ross and Vardoulakis (2026, JFQA, *Leverage and Stablecoin Pegs*)

- **Run model**: nests a Goldstein-Pauzner (2005) bank-run global game inside a leveraged collateralised trading model in the Gromb-Vayanos (2002) tradition. Three periods, four assets, three agents (issuer, investors, crypto speculators) (pp. 5–6 of the PDF).
- **Novel demand channel**: stablecoin owners are compensated for run risk by lending their coins to crypto speculators at high rates. The peg holds in expectation but the holder is paid a premium for the run-risk exposure.
- **Key empirical evidence**: speculative demand for crypto raises stablecoin lending rates. Instrument: MLB sponsorship deal with FTX. Application: Terra collapse and the near-run on Tether in May 2022.
- **What is one and the same as in this paper**: the use of a global game to pin down a unique run probability; the link between issuer balance-sheet liquidity and peg stability; the use of historical run episodes (May 2022 there, March 2023 here) to discipline the calibration.
- **What is different**: Gorton et al. focus on the **leverage-money nexus**. The demand for stablecoins in their model is driven by speculative lending. The present paper is silent on speculation and is instead about payment use. The two papers are complementary rather than substitutable, and the AFA paper should cite Gorton et al. as the closest finance-side framing while exhibiting the payment-side gap they leave open.

### 1.4 Bertsch (2025, working paper, Sveriges Riksbank) — *Stablecoins: Adoption and Fragility*

- **Run model**: a modified Goldstein-Pauzner (2005) global game. Three dates. Investors choose stablecoin vs bank deposit at $t=0$; the run game is played at $t=1$ (pp. 4–5 of the PDF).
- **Key results**:
  - Most factors that raise the attractiveness of stablecoins **reduce** their fragility, because the marginal investor at the redemption threshold becomes less flighty.
  - Wider adoption can be destabilising once it absorbs cohorts with low convenience benefit (more flighty marginal holders).
  - Negative network effects via transaction-fee congestion can be **stabilising**: anticipated congestion at the run date makes the marginal holder less flighty ex ante.
  - The presence of a large speculator is unambiguously destabilising.
- **What is one and the same as in this paper**: explicit modelling of stablecoin adoption versus an alternative payment instrument; use of a global game over a single fundamental; congestion as a relevant state.
- **What is different**: Bertsch has **one** representative class of stablecoin holders. The adoption vs deposit choice is at $t=0$ rather than the ex-post cost-benefit framing the present paper proposes. There is no calibration to event data and no corridor structure.

## 2. The contribution map

Stack the four papers along three axes:

| Axis | Ahmed-Aldasoro-Duley | Ma-Zeng-Zhang | Gorton-Klee-Ross-Ross-Vardoulakis | Bertsch | **This paper** |
|------|----------------------|----------------|--------------------------------------|---------|----------------|
| Coordination layer | 2G global game with unknown reserve volatility | Run game with two-layer market structure | Bank-run game nested in leveraged trading | Goldstein-Pauzner adapted | **Morris-Shin fixed point with class-heterogeneous thresholds** |
| Heterogeneity of holders | none | arbs vs investors (2 classes) | none | none | **4 classes mapped to payment corridors** |
| Payment-infrastructure block | no | no | no | congestion via fees, no rail topology | **rail-level queue ratio enters payoff** |
| Cost-benefit vs incumbent rail | no | no | no | adoption-stage choice vs bank deposit | **corridor-level certainty-equivalent vs named incumbent** |
| Identification | SVB/USDC, synthetic control | cross-sectional concentration of arbitrage | MLB-FTX as instrument; May 2022 application | none, purely theoretical | **USDC March 2023 + Brazil cross-border ban + TerraUSD falsification** |

The white space is in the bottom three rows of the right column. None of the four nearest papers covers the joint of (a) heterogeneous class-specific thresholds, (b) endogenous coupling to a payment-rail block and (c) a cost-benefit closure against a named incumbent rail with corridor-level data. That joint is the contribution of the AFA paper.

## 3. Honest framing of the methodological contribution

The contribution is **not**: "first paper to use a global game on stablecoins." Ahmed-Aldasoro-Duley, Gorton et al., Bertsch and Ma-Zeng-Zhang all already do that, in different ways. Any draft that opens with such a claim invites a fatal referee comment.

The contribution **is**: "First paper to solve a class-heterogeneous Morris-Shin fixed point on top of an explicit payment-rail block and to close the loop with a corridor-level certainty-equivalent comparison against named incumbent rails." The three pieces are jointly necessary: take any one of them out and one of the four papers above already does the rest.

Auxiliary contributions worth flagging (but not headline-worthy on their own):

- Calibrate $\{\sigma_k\}$ from the observed cross-section of redemption activity around 11–12 March 2023 rather than from a single aggregate moment.
- Use the Brazil cross-border ban as a quasi-natural-experiment identification of the cross-border-class payoff component $\omega_{\text{cross-border}}$.
- Treat TerraUSD as out-of-class falsification rather than as a calibration target, sharpening the model's boundary of applicability.

## 4. Required positioning passages for the AFA paper

Three citations cannot be missing in the lit-review section and must each carry a specific sentence:

1. **Ahmed, Aldasoro and Duley (2024)** — *"Closest in modelling philosophy. They extend the Morris-Shin coordination problem along the information dimension (unknown reserve volatility). This paper extends it along the holder-heterogeneity and payment-infrastructure dimensions, while reverting to a first-generation game in which the fundamental's distribution is common knowledge."*

2. **Ma, Zeng and Zhang (2025)** — *"Documents centralised arbitrage and analyses how it interacts with stablecoin run risk. We retain their dual-channel exit structure (primary redemption + secondary sale) but replace their two-layer arbs-versus-investors structure with $K$ heterogeneous user classes whose thresholds are solved jointly. Their counterintuitive arbitrage-vs-run-risk trade-off is preserved in our setup as a comparative-statics result on $\psi$ and $\zeta$."*

3. **Bertsch (2025)** — *"Closest in question. Like Bertsch, we ask whether holding/using a stablecoin is welfare-improving relative to an alternative. Unlike Bertsch, the comparison is corridor-specific and post-event, anchored on a calibrated $\theta$-distribution and on the realised cost structure of the relevant incumbent rail rather than on an ex-ante adoption decision against a generic bank deposit."*

4. **Gorton, Klee, Ross, Ross and Vardoulakis (2026)** — *"Provides the canonical finance-side framing of stablecoin fragility via the leverage-money nexus. Our paper does not model speculative demand and is therefore complementary: we hold the demand source fixed at payment use and isolate the segment-specific cost-benefit balance."*

## 5. Open risks and mitigations

- **Risk 1.** A referee may ask why we revert to a first-generation Morris-Shin game when Ahmed-Aldasoro-Duley already have the more sophisticated second-generation extension. **Mitigation:** state explicitly that the second-generation extension is orthogonal to the heterogeneous-class extension we propose and that adding both would obscure the cost-benefit interpretation. Cite Ahmed-Aldasoro-Duley as the natural sequel that combines both.
- **Risk 2.** A referee may argue that the cross-border–wholesale–retail split is ad hoc. **Mitigation:** in the lit review and in §3 of the model statement, justify each class with at least one descriptive paper from the JoES library (Auer-Lewrick-Paulick 2024 for cross-border; Ante 2025 for remittance adoption; Egan-Matvos-Seru-Wang-Yao 2026 for retail payment incidence; Watsky-Allen-Daud-Demuth-Little-Rodden-Seira 2024 for the role of arbitrageurs).
- **Risk 3.** A referee may worry that the cost-benefit metric in §6 is too sensitive to the choice of $\gamma_k$ (the risk-aversion-like weight on $\mathrm{Var}_\theta(p^{sec})$). **Mitigation:** report the metric for two values of $\gamma_k$, one zero and one calibrated to the standard payment-economics value, and show that the breakeven coordination state moves monotonically but does not flip the sign of the comparison in our preferred specifications.
- **Risk 4.** A referee may notice that the Brazil ban is partly anticipatory and that flow displacement data is thin in mid-2026. **Mitigation:** report the calibration in two windows, pre- and post-announcement, and present the post-implementation window as a robustness check; ensure the headline result does not depend on data later than 2026-04 if available.

## 6. Verdict on whether to proceed

No fatal overlap. The headline contribution is intact provided the paper frames it as the joint of (heterogeneous-class fixed point) × (payment-rail block) × (corridor-level cost-benefit). The relationship to each of the four nearest papers is clean, and each one has a one-sentence positioning we can lift verbatim into the lit-review section. **Recommendation: proceed to the simulation skeleton.**
