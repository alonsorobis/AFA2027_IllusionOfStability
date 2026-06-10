# AFA 2027 Special Session — Submission package manifest
*The Illusion of Stability in Stablecoins*

This file lists every item the AFA 2027 Special Session call requires, with its location in the project tree. Reviewers can use it as a checklist to verify compliance with the special-session rules.

## Headline deliverables

| Required item | Location | Notes |
|---------------|----------|-------|
| Final paper PDF | [paper/main.pdf](paper/main.pdf) | 33 pages, 11,789 words, draft 6 |
| Paper LaTeX source | [paper/main.tex](paper/main.tex) + [paper/sections/](paper/sections/) | Reproducible compile with `pdflatex main; bibtex main; pdflatex main; pdflatex main` |
| Bibliography | [paper/refs.bib](paper/refs.bib) | 20 BibTeX entries; symlinked from [literature/refs.bib](literature/refs.bib) |

## AFA-mandated evidence files

| Required item | Location | Notes |
|---------------|----------|-------|
| Verbatim transcript of every AI session | [conversations/](conversations/) | 11 transcripts, all dated 2026-06-01 or 2026-06-02; initial author prompt of each session reproduced verbatim |
| Master AI interaction index | [AI_INTERACTION_LOG.md](AI_INTERACTION_LOG.md) | One row per session with system, model, purpose and transcript link |
| Human time log | [HUMAN_TIME_LOG.md](HUMAN_TIME_LOG.md) | Per-session start/end (author to complete remaining `TBD` entries) |
| Authorship report (lines by author class) | [AUTHORSHIP_REPORT.md](AUTHORSHIP_REPORT.md) | Snapshots at each session close |
| AI workflow description inside the paper | [paper/sections/A1_ai_workflow.tex](paper/sections/A1_ai_workflow.tex) | Appendix A1 of the submitted paper |

## Reproducibility artefacts

| Required item | Location | Notes |
|---------------|----------|-------|
| Simulation package | [simulation/stablecoin_ms/](simulation/stablecoin_ms/) | 10 modules implementing the model |
| Unit tests | [simulation/tests/](simulation/tests/) | 26 tests, all passing |
| Calibration scripts | [simulation/scripts/run_calibration.py](simulation/scripts/run_calibration.py) and the inline runner documented in session 07 | Reproduces the main calibration and the multi-start in session 11 |
| Calibration outputs | [data/processed/usdc_calibration_20260601T145343Z/](data/processed/usdc_calibration_20260601T145343Z/) | manifest, phi history, moments comparison |
| Out-of-sample outputs | [data/processed/oos_calibration_20260601T172037Z/](data/processed/oos_calibration_20260601T172037Z/) | USDT and DAI re-estimation results |
| Cost-benefit metrics | [data/processed/cb_metrics_20260601T145343Z.json](data/processed/cb_metrics_20260601T145343Z.json) | Per-corridor CEC at calibrated $\phi^\star$ |
| Identification check | [data/processed/identification_check_TBD/](data/processed/) | Jacobian SVD around $\phi^\star$ (session 11) |
| Multi-start verification | [data/processed/multistart_TBD/](data/processed/) | Three random restarts around $\phi^\star$ (session 11) |
| Data download scripts | [data/scripts/](data/scripts/) | Coinbase Advanced Trade, CryptoCompare, DefiLlama, FRED, World Bank, BCB |
| Data download log | [data/download_log.md](data/download_log.md) | Per-download timestamp, source URL, SHA-256 hash |
| Raw data | [data/raw/](data/raw/) | All downloads performed inside the project window |
| BCB primary materials | [data/raw/manual/](data/raw/manual/) | Two BCB PDFs documenting the November 2025 package |

## Planning and decision trail

| Item | Location | Purpose |
|------|----------|---------|
| Scope and decision log | [planning/SCOPE_AND_QUESTIONS.md](planning/SCOPE_AND_QUESTIONS.md) | Author rulings on every strategic decision |
| Model spec memo | [planning/MODEL.md](planning/MODEL.md) | Model statement before code was written |
| Literature gap memo | [planning/LITERATURE_GAP.md](planning/LITERATURE_GAP.md) | Positioning against the four closest papers |
| Research log | [RESEARCH_LOG.md](RESEARCH_LOG.md) | Chronological diary of substantive decisions |

## Compliance with AFA rules (self-check)

| Rule | Compliance | Evidence |
|------|------------|----------|
| Investigation must begin on or after 2026-06-01 | ✓ | First session: `2026-06-01_session_01.md`, opening at the start of the AFA window |
| Only the named author may contribute work | ✓ | No other human collaborator; AI assistant disclosed in Appendix A1 |
| All AI conversations documented and submitted | ✓ | 11 verbatim transcripts in `conversations/` |
| Time log of human activities included | ✓ | `HUMAN_TIME_LOG.md` (author to complete `TBD` start times) |
| Report of authorship (lines by class) included | ✓ | `AUTHORSHIP_REPORT.md` |
| Submission deadline 2026-08-31 | ⏳ | Draft 6 ready; submission window still open |

## What remains for final submission

1. Author proofread of `paper/main.pdf`.
2. Author fills the remaining `TBD` start times in `HUMAN_TIME_LOG.md` (the close of session 10 at 20:00 on 2026-06-01 is already recorded).
3. Multi-start verification result documented (session 11, in progress).
4. Numerical identification check documented (session 11, in progress).
5. Submission upload through the AFA portal once the call's submission window opens.
