# Local Directory Contract

> Local fork contract for organizing ARIS projects by domain instead of by upstream root-level defaults.

## Goal

The upstream layout is workflow-first and root-relative:

- `literature/` for local paper search
- `research/refine/` for refinement artifacts
- `writing/paper/`, `writing/slides/`, `writing/poster/`, `writing/rebuttal/` for writing outputs
- `research/IDEA_REPORT.md`, `research/AUTO_REVIEW.md`, `research/RESEARCH_BRIEF.md` in project root

This local fork intentionally changes that contract. The project should be organized by domain:

1. `literature/` — reference papers and imported external material
2. `research/` — iterative state, review logs, planning artifacts
3. `exp/` — runnable experiments and outputs
4. `writing/` — submission-facing outputs

This is a real fork-level path change, not a compatibility alias layer.

## Canonical Layout

```text
project/
├── CLAUDE.md
├── literature/
│   └── ...                        # local paper library, notes, imported papers
├── research/
│   ├── research/RESEARCH_BRIEF.md
│   ├── research/IDEA_REPORT.md
│   ├── research/AUTO_REVIEW.md
│   ├── research/REVIEW_STATE.json
│   ├── research/IDEA_CANDIDATES.md
│   ├── research/EXPERIMENT_LOG.md
│   ├── research/findings.md
│   ├── contract.md
│   └── refine/
│       ├── FINAL_PROPOSAL.md
│       ├── REVIEW_SUMMARY.md
│       ├── REFINEMENT_REPORT.md
│       ├── EXPERIMENT_PLAN.md
│       ├── EXPERIMENT_TRACKER.md
│       ├── EXPERIMENT_RESULTS.md
│       ├── PIPELINE_SUMMARY.md
│       ├── REFINE_STATE.json
│       ├── score-history.md
│       └── round-*.md
├── exp/
│   ├── scripts/
│   ├── logs/
│   ├── results/
│   ├── ckpts/
│   └── data/
└── writing/
    ├── writing/paper/
    │   ├── main.tex
    │   ├── main.pdf
    │   ├── sections/
    │   └── figures/
    ├── writing/slides/
    ├── writing/poster/
    ├── writing/rebuttal/
    └── grant-proposal/
```

## Path Mapping

| Upstream default | Local fork path |
|---|---|
| `papers/` | `literature/` |
| `literature/` | `literature/` |
| `research/RESEARCH_BRIEF.md` | `research/RESEARCH_BRIEF.md` |
| `research/IDEA_REPORT.md` | `research/IDEA_REPORT.md` |
| `research/AUTO_REVIEW.md` | `research/AUTO_REVIEW.md` |
| `research/REVIEW_STATE.json` | `research/REVIEW_STATE.json` |
| `research/IDEA_CANDIDATES.md` | `research/IDEA_CANDIDATES.md` |
| `research/EXPERIMENT_LOG.md` | `research/EXPERIMENT_LOG.md` |
| `research/findings.md` | `research/findings.md` |
| `research/contract.md` | `research/contract.md` |
| `research/refine/` | `research/refine/` |
| `writing/paper/` | `writing/paper/` |
| top-level `figures/` for the paper pipeline | `writing/paper/figures/` |
| `writing/slides/` | `writing/slides/` |
| `writing/poster/` | `writing/poster/` |
| `writing/rebuttal/` | `writing/rebuttal/` |
| `writing/grant-proposal/` | `writing/grant-proposal/` |

## Design Rules

- Keep external reference material in `literature/`.
- Keep workflow state and recovery files in `research/`.
- Keep planning and iterative refinement artifacts in `research/refine/`.
- Keep runnable experiments in `exp/`.
- Keep the current paper and all presentation assets under `writing/`.
- Keep paper figures under `writing/paper/figures/`.
- Within generated LaTeX or slide/poster files, relative asset references such as `figures/...` may still appear when they are relative to the output directory itself. The fork-level path change is about project structure, not internal LaTeX relative paths.

## Required Rewrite Scope

Adopting this contract requires more than a few skill edits. The path contract is spread across:

- `skills/`
- `README.md` and `README_CN.md`
- `docs/`
- `templates/`
- a small number of helper scripts

The fork therefore keeps two helper scripts:

- `tools/apply_local_contract.py`
- `tools/check_local_contract.py`

The intended maintenance workflow is:

1. merge or rebase from upstream
2. run `tools/apply_local_contract.py`
3. run `tools/check_local_contract.py`
4. manually review hotspot files

## Hotspot Files

These files are the most path-sensitive and should be checked after every upstream sync:

- `skills/research-refine/SKILL.md`
- `skills/research-refine-pipeline/SKILL.md`
- `skills/experiment-bridge/SKILL.md`
- `skills/research-lit/SKILL.md`
- `skills/paper-writing/SKILL.md`
- `skills/paper-write/SKILL.md`
- `skills/paper-compile/SKILL.md`
- `skills/paper-slides/SKILL.md`
- `skills/paper-poster/SKILL.md`
- `skills/rebuttal/SKILL.md`

## Non-Goal

This fork does not preserve upstream root-level path compatibility. It intentionally changes the project contract to match the local layout above.
