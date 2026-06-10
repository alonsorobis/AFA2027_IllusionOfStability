# Archived: AFA-era draft (pre-pivot, 2026-06-01)

This folder contains the pre-pivot draft of the paper produced during sessions 01-11 (2026-06-01 and morning of 2026-06-02). The pivot to the IJCB-target framing happened in session 12 (2026-06-02), at which point this draft was retired in favour of the structure now in `../../main.tex` and `../../sections/`.

## Contents

- `main_afa.tex` and `main_afa.pdf` — the original main file and final compiled PDF of the AFA-era draft (33 pp, 12,101 words at session 11 close, joint USDC+DAI calibration).
- `sections/` — the nine section files of the original eight-section + appendix structure:
  - `01_introduction.tex`, `02_literature.tex`, `03_model.tex`, `04_data_calibration.tex`, `05_results.tex`, `06_cost_benefit.tex`, `07_discussion.tex`, `08_conclusion.tex`, `A3_proofs.tex`
- LaTeX auxiliary artefacts (`main.aux`, `main.bbl`, etc) — kept so the PDF is reproducible without recompilation.

## Why this is archived

The AFA-era draft framed the paper as a financial-stability piece on stablecoin run dynamics with the Morris-Shin global game as the headline methodological contribution. Session 12 author guidance reframed the paper as a payments-economics piece for IJCB, with the global game as a supporting tool for pricing the structural risk premium that enters a corridor-level cost comparison. Most of the analysis content carried over, but the presentation, section structure, and emphasis changed enough that a clean restart of the LaTeX tree was the cleanest route.

## Reproducibility

To recompile this draft, copy it to a working directory (the relative paths assume `sections/` lives alongside `main_afa.tex`) and run `pdflatex main_afa.tex; bibtex main_afa; pdflatex main_afa.tex; pdflatex main_afa.tex` against the project root `refs.bib`. The propositions in `A3_proofs.tex` are subsumed in the active draft's Appendix B (`../../sections/B_formal_model.tex`).
