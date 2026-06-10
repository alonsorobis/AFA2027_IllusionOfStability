# The Illusion of Stability in Stablecoins
## Submission package for AFA 2027 Special Session on Generative AI Workflows

**Project start date:** 2026-06-01 (the earliest date permitted by the call).
**Submission deadline:** 2026-08-31.
**Status:** Repository pushed to GitHub at https://github.com/alonsorobis/AFA2027_IllusionOfStability (verified 2026-06-10)
**Author:** Andres Alonso-Robisco (IE University / Banco de España).
**Target venues:** AFA 2027 Special Session (primary); Journal of Economic Dynamics and Control (alternative outlet for the same paper if not selected).

## Why a separate project
The AFA 2027 Special Session call requires that the investigation **begin on or after 1 June 2026** and that no humans other than the named authors contribute work. A prior working paper exists under `../Human_x_AI_Finance_submission/`, drafted with OpenAI Codex for a different conference. That work counts as **background context** for the author, not as starting material for the AFA submission. The simulation code, the paper, the bibliography and the data pipelines under this folder are built from scratch from 2026-06-01 onward and document every AI interaction.

## Folder layout
- `AI_INTERACTION_LOG.md` — master index of every Claude Code / AI session, with verbatim prompts and links to per-session transcripts.
- `conversations/` — full, verbatim transcripts of each interaction. Filenames are `YYYY-MM-DD_session_NN.md`.
- `HUMAN_TIME_LOG.md` — bitácora temporal manual del autor (clock-in / clock-out per session).
- `AUTHORSHIP_REPORT.md` — running tally of lines of code / paper text / documentation by author class (human vs AI).
- `RESEARCH_LOG.md` — substantive research-decision diary (in the same style as `../JoES/RESEARCH_LOG.md`).
- `planning/` — scope documents, research-question drafts, decision memos.
- `paper/` — LaTeX source built from scratch.
- `simulation/` — Python code, notebooks, scenario runners (from scratch).
- `data/` — raw downloads and processed datasets (refreshed from open sources after 2026-06-01).
- `literature/` — bibliography and reading notes specific to this paper (the `../JoES/library/pdfs/` PDFs may be referenced as a read-only library; new sources land here).

## Workflow rule for the author
1. Every new Claude Code session writes a transcript file under `conversations/`. The session index is appended to `AI_INTERACTION_LOG.md`.
2. Before starting a session, the author logs the time in `HUMAN_TIME_LOG.md`.
3. After substantive code or text changes, the author updates `AUTHORSHIP_REPORT.md` (or asks the AI assistant to recompute it).
4. Substantive research decisions (research question, calibration target, modelling choices, killed branches) go in `RESEARCH_LOG.md`.
