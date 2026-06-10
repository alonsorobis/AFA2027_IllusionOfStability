# Workflow log format

One Markdown file per working session, stored in `log/`. Filename:
`YYYY-MM-DD_NN_short-topic.md` (NN = sequence number for that day, in case
there is more than one session).

Each session file contains one or more entries. Each entry uses the
template below.

```
## Entry <N> — <YYYY-MM-DD HH:MM> — <short title>

**Tool**: Claude Code | claude.ai | ChatGPT | other
**Model**: e.g. Claude Opus 4.7
**Context**: Anchor in the action plan (e.g. "Phase 1 week 2 - USDT
diagnosis").

**Prompt** (verbatim or close paraphrase):

> ...

**Output summary** (1-3 lines): what the AI produced.

**Human decision**: accept / accept with edits / reject. If edits, what
changed.

**Files touched** (relative to project root): list.

**Result / takeaway** (1-2 lines).
```

## Why this format

It satisfies the AFA special-session requirement that papers be written with
documented generative-AI workflows. It is also the right log if the paper is
re-routed to JEDC or to a central-bank working paper series, where
reproducibility expectations apply equally.

Three principles:

1. **Verbatim prompts when possible**. If the prompt is long, summarise but
   preserve the structure and the variable names. Reviewers should be able
   to reproduce the interaction without seeing your screen.
2. **Always record the human decision**. The log is not "what the AI did";
   it is "how the human used the AI". Accept-with-edits is the most useful
   entry to capture because it shows where judgement was exercised.
3. **No silent rejections**. If you asked the AI for something and threw
   it away, log it. The pattern of where AI failed is itself part of the
   methodological contribution.

## What does not go in the log

- Routine LaTeX formatting tweaks done by hand.
- Code linting and trivial file moves.
- Personal notes and thoughts that do not involve an AI tool.

These go in a separate `RESEARCH_NOTES.md` if needed.

## Aggregation at submission time

At the end of August 2026, all entries are concatenated into one
`workflow_log_concat.md` that becomes a supplementary file in the AFA
submission. A short cover note summarises the AI tools used, the
percentage of code/prose authored with assistance versus by hand, and the
governance steps (when the human overruled the AI, when the AI flagged
something the human had missed).
