# CLAUDE.md

## Purpose

This fork exists for one reason:

- track `upstream` as closely as possible
- apply a local directory contract that relocates project files into a cleaner layout

This fork is not intended to redefine ARIS workflows, research methodology, or feature scope. Local changes should stay narrowly focused on file and directory organization.

## Fork Policy

When modifying this fork:

- prefer syncing from `upstream` first
- keep local diffs minimal, mechanical, and path-focused
- avoid semantic workflow changes unless they are required by the directory relocation
- do not rename parameters or behaviors unless path relocation makes it necessary

The intended maintenance model is:

1. update from `upstream`
2. replay local path-contract changes
3. review only the files touched by directory relocation

## Local Directory Contract

The local project layout should converge to:

```text
project/
├── literature/
├── research/
│   ├── RESEARCH_BRIEF.md
│   ├── IDEA_REPORT.md
│   ├── AUTO_REVIEW.md
│   ├── REVIEW_STATE.json
│   ├── IDEA_CANDIDATES.md
│   ├── EXPERIMENT_LOG.md
│   ├── findings.md
│   └── refine/
├── data/
├── exp/
└── writing/
    ├── paper/
    │   ├── main.tex
    │   ├── main.pdf
    │   ├── sections/
    │   └── figures/
    ├── slides/
    ├── poster/
    ├── rebuttal/
    └── grant-proposal/
```

## Scope Of Local Rewrites

Expected relocation examples:

- `papers/` or `literature/` -> `literature/`
- `RESEARCH_BRIEF.md` -> `research/RESEARCH_BRIEF.md`
- `IDEA_REPORT.md` -> `research/IDEA_REPORT.md`
- `AUTO_REVIEW.md` -> `research/AUTO_REVIEW.md`
- `refine-logs/` -> `research/refine/`
- `paper/` -> `writing/paper/`
- `figures/` -> `writing/paper/figures/`
- `slides/` -> `writing/slides/`
- `poster/` -> `writing/poster/`
- `rebuttal/` -> `writing/rebuttal/`

## Non-Goals

This fork should not:

- become a general feature fork
- drift far from `upstream`
- introduce unrelated workflow preferences into skill logic
- accumulate manual one-off edits that cannot be replayed after an upstream sync
