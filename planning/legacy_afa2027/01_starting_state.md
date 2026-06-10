# Starting state as of 2026-05-28

## The paper we are upgrading

Title: *Stablecoins and the Illusion of Stability: Evidence from an
Agent-based Model.*
Author: Andres Alonso-Robisco, Banco de Espana.
Prior submission: Human x AI Finance, March 2026. Ranked 91 of 159, scores:
Innovation 65, Methodology 67, Relevance 78, Rigor 52, Overall 66.
Not accepted.

The full HxAI submission package, the referee report, and the present working
codebase all live in the parent folder
`C:/Users/alons/Documents/Stablecoins/`.

## What is solid and we keep

- Three-block ABM: payment generation and queueing, issuer block with
  primary/secondary allocation and reduced-form secondary price, redemption
  block driven by a logistic that approximates global games.
- Four agent classes: national retail, national wholesale, cross-border,
  market makers, each with class-specific behavioural priors.
- Multi-rail layer: Ethereum, Tron, Solana, with class-specific rail usage
  weights and rail-specific expectation wedges.
- Calibration to March 2023 USDC on six moments and out-of-sample validation
  on USDT and DAI without refitting.
- Headline finding: cross-border users are both the most payment-useful and
  the most redemption-sensitive segment. We call this the "illusion of
  stability".
- Three-channel decomposition: liquidity stress maps mainly to payment
  congestion, counterparty stress maps mainly to depeg risk, joint stress
  amplifies both.
- Structured LLM elicitation of behavioural priors with schema-validated
  JSON, median + IQR aggregation, audit log, and a versioned hard-coded
  baseline. This is unusual and is the most distinctive methodological
  device.

## What we fix in this sprint

From the HxAI referee report, ranked by how much each fix moves rigor:

1. **Solve the global-games fixed point under 2 heterogeneous types** and
   characterise the approximation error of the logistic rule used in the
   prior version. This is the dominant fix.
2. **Tornado sensitivity analysis** over the structural parameters (price
   impact scale and convexity, depth-erosion coefficient, signal noise,
   Monte Carlo run count, agent count) and over the IQR of each
   LLM-elicited behavioural prior. Demonstrate Monte Carlo convergence.
3. **External empirical anchor** for at least one LLM-elicited behavioural
   parameter. Public chain data, Circle disclosures, or BIS/CPMI survey
   evidence.
4. **Diagnose the USDT March 2023 miss** and either report a clean
   asset-specific tuning step or admit the model does not transport to
   captive offshore user bases without an explicit extra mechanism.
5. Resolve the unresolved `Section ??` references, finalise the
   "preliminary" calibration label, and tighten the introduction so the
   "illusion of stability" framing and the three-channel decomposition lead
   the abstract.

Optional fix if time allows: a second calibration anchor on the May 2025
Brazilian restriction on stablecoin international payments. If the data
shows no usable signal on that week, we drop it without guilt.

## What we deliberately do not do

- No endogenous rail choice. Six-month problem on its own.
- No DSGE or welfare extension. Stay in microstructure.
- No full structural estimation of behavioural priors. Follow-up paper.
- No new model architecture. The current three-block design stands.

## Companion work that is relevant but separate

`../JoES/` contains the survey paper on payment-medium adoption from cash to
stablecoins, currently in draft. The two papers are complementary: the JoES
survey gives the framing on who uses what and why; the Illusion paper gives
the microstructure of why the segment best suited for stablecoins is also
the most fragile under stress. They should cite each other, not compete.
