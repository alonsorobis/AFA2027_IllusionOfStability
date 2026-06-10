# `simulation/` — agent-based model for *The Illusion of Stability in Stablecoins*

Python implementation of the model stated in `../planning/MODEL.md`. Built from scratch on 2026-06-01 inside an AI-supervised session, per the AFA 2027 timing rule.

## Layout

```
simulation/
├── stablecoin_ms/          # importable package
│   ├── __init__.py         # version, top-level exports
│   ├── agents.py           # per-class state, signal draws
│   ├── issuer.py           # issuer balance sheet, primary redemptions
│   ├── secondary.py        # secondary-price block, depth erosion
│   ├── signals.py          # private signal generation, posteriors
│   ├── fixed_point.py      # Morris-Shin K-dim threshold solver
│   ├── payoffs.py          # V_R and V_H, per-class wedges
│   ├── scenario.py         # scenario parameter container
│   ├── montecarlo.py       # MC loop, draw-level orchestration
│   ├── calibration.py      # moment-matching, USDC March 2023 targets
│   └── cost_benefit.py     # certainty-equivalent vs incumbent rail
├── tests/                  # pytest suite (unit + integration)
├── notebooks/              # exploratory Jupyter notebooks (logged in their own AI sessions)
├── requirements.txt        # pinned deps
└── README.md               # this file
```

## Status

- 2026-06-01: skeleton only. All function bodies are stubs that raise `NotImplementedError` and carry docstrings referencing the equations in `../planning/MODEL.md`. No simulation results yet.

## How to run (once implemented)

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
pytest tests/
python -m stablecoin_ms.montecarlo --scenario baseline --n_draws 1000 --seed 42 --out results/
```

## Reproducibility

- All randomness is seeded; `montecarlo.run_scenario(seed=...)` is the single entry point.
- Each Monte Carlo run writes a manifest in `results/<scenario>_<timestamp>/manifest.json` with the resolved parameter dict, the AFA project SHA1 of the codebase, and the calibration version.
- No data is read from inside `stablecoin_ms`. Datasets live under `../data/processed/` and are passed in as paths.
