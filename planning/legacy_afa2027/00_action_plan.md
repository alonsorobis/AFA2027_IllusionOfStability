# Action plan — June, July, August 2026

3 months, ~10-15 h/week assumed, with day job at Banco de España in the
Division of Payment Innovation as the binding time constraint. Submission
deadline: **2026-08-31** (AFA 2027 special session).

## Phase 1 — June 2026 (4 weeks): diagnosis and freezing the baseline

Goal: have a clean baseline to compare against, a diagnosis of the USDT miss,
a Yes/No on whether the Brazil 2025 stablecoin restriction is usable as a
second calibration anchor, and the AI workflow log started.

Weekly milestones:
- **Week 1 (Jun 1-7)**. Re-run the existing pipeline end to end; freeze the
  baseline numbers in a tagged commit. Start the log on day 1. Open the
  template files for the Morris-Shin module so the structure exists even
  before the code does.
- **Week 2 (Jun 8-14)**. Diagnose the USDT March-2023 miss. State one
  competing hypothesis (captive offshore user base with a different outside
  option) and one cheap test for it.
- **Week 3 (Jun 15-21)**. Look at the Brazil 2025 stablecoin restriction
  event: pull public price and on-chain flow data for the relevant week and
  decide whether it is a usable second calibration anchor. If not, drop it
  and move on without guilt.
- **Week 4 (Jun 22-30)**. End-of-month checkpoint. Stop-loss decision: have
  we made any meaningful progress on the Morris-Shin 2-type module? If not,
  abandon the AFA submission and re-route to a JEDC submission in autumn
  2026.

## Phase 2 — July 2026 (4 weeks): the scientific upgrade

Goal: solve the global-games fixed point under 2 agent types, characterise
the approximation error of the current logistic rule, and add a tornado-style
sensitivity analysis. These are the three highest-impact items from the HxAI
Finance referee report.

Weekly milestones:
- **Week 5 (Jul 1-7)**. Code the 2-type Morris-Shin fixed-point solver as a
  separate module. Best-response iteration on thresholds, no Monte Carlo
  yet. Verify it converges on canonical parameterisations.
- **Week 6 (Jul 8-14)**. Wire the fixed-point solver into the existing
  pipeline. Solve once per (state, scenario), not inside the Monte Carlo
  loop. Compare the solved threshold against what the current logistic
  predicts at the same point.
- **Week 7 (Jul 15-21)**. Run the full set of scenarios with the upgraded
  block. Re-compute the key results from the HxAI version. Check that the
  cross-border segmentation result survives.
- **Week 8 (Jul 22-31)**. Tornado sensitivity over six to eight structural
  parameters (price impact scale and convexity, depth-erosion coefficient,
  signal noise, run count, agent count) plus the IQR of each LLM-elicited
  behavioural prior. Demonstrate Monte Carlo convergence by varying run
  count and agent count.

## Phase 3 — August 2026 (4 weeks): empirical anchor and paper rewrite

Goal: at least one external anchor for the LLM-elicited priors, a tight
rewrite of the paper foregrounding "illusion of stability" and the
liquidity/counterparty/joint decomposition, and submission by 2026-08-31.

Weekly milestones:
- **Week 9 (Aug 1-7)**. Pull one public source for a behavioural-parameter
  cross-check: a Circle redemption disclosure series, an Etherscan/Tron
  flow-elasticity proxy, or BIS/CPMI survey data on stablecoin usage. Report
  the LLM prior next to the external anchor in the paper.
- **Week 10 (Aug 8-14)**. Paper rewrite, half one. Resolve every "Section
  ??" cross-reference. New abstract and introduction that lead with
  "illusion of stability" and the three-channel decomposition. Tighten the
  Diamond-Dybvig and Morris-Shin links in section 2.
- **Week 11 (Aug 15-21)**. Paper rewrite, half two. New section on the
  Morris-Shin fixed point and the logistic approximation error. New section
  on the tornado sensitivity. New appendix on the LLM elicitation procedure
  with prompts, schema, aggregation rule, audit-log format.
- **Week 12 (Aug 22-31)**. Final pass, references, figures, and submission
  package. Cover letter that openly references the prior HxAI submission and
  explains how the present version differs (see eligibility note). Submit by
  2026-08-31.

## Out of scope for this sprint

- Endogenous rail choice under stress (rail substitution). This is a
  six-month project on its own.
- Multi-event calibration on Terra/Luna, FTX, BUSD wind-down beyond the
  one Brazil 2025 case. One additional event well done beats three poorly.
- A full structural estimation of behavioural parameters from on-chain
  transaction data. This is a natural follow-up paper, not a sprint item.
- A welfare or DSGE extension. We stay in microstructure.

## Stop-loss conditions

Abandon the AFA submission if any of these triggers fire:

1. End of June 2026: the 2-type Morris-Shin solver does not converge on
   canonical parameterisations, or the logistic approximation error is so
   large that the entire scenario decomposition would need re-derivation.
2. End of July 2026: the tornado sensitivity reveals that the cross-border
   segmentation result is fragile to standard parameter perturbations. In
   that case the paper has a different and harder story to tell, not one
   that fits a three-week rewrite.
3. The AFA organisers respond to a clarifying email saying that a paper
   previously submitted to another conference cannot be considered.

If we abandon, the work done is not lost. It maps directly into a JEDC
submission for late 2026 with no time pressure.
