#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


TEXT_EXTS = {
    ".md",
    ".py",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".tex",
    ".sh",
}


SKIP_PARTS = {".git", "__pycache__"}


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTS and path.name not in {
            "README",
            "README.md",
            "README_CN.md",
        }:
            continue
        try:
            path.read_text()
        except Exception:
            continue
        files.append(path)
    return files


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


RESEARCH_GLOBAL_REPLACEMENTS = [
    (r"(?<!research/)RESEARCH_BRIEF\.md\b", "research/RESEARCH_BRIEF.md"),
    (r"(?<!research/)IDEA_REPORT\.md\b", "research/IDEA_REPORT.md"),
    (r"(?<!research/)AUTO_REVIEW\.md\b", "research/AUTO_REVIEW.md"),
    (r"(?<!research/)REVIEW_STATE\.json\b", "research/REVIEW_STATE.json"),
    (r"(?<!research/)IDEA_CANDIDATES\.md\b", "research/IDEA_CANDIDATES.md"),
    (r"(?<!research/)EXPERIMENT_LOG\.md\b", "research/EXPERIMENT_LOG.md"),
    (r"(?<!research/)findings\.md\b", "research/findings.md"),
    (r"docs/research_contract\.md\b", "research/contract.md"),
    (r"(?<!research/)research/refine/", "research/refine/"),
]


LITERATURE_GLOBAL_REPLACEMENTS = [
    (r"\bpapers/\b", "literature/"),
]


PAPER_PIPELINE_FILES = {
    "README.md",
    "README_CN.md",
    "skills/paper-writing/SKILL.md",
    "skills/paper-plan/SKILL.md",
    "skills/paper-figure/SKILL.md",
    "skills/paper-write/SKILL.md",
    "skills/paper-compile/SKILL.md",
    "skills/auto-paper-improvement-loop/SKILL.md",
    "skills/paper-illustration/SKILL.md",
    "skills/mermaid-diagram/SKILL.md",
    "skills/skills-codex/paper-writing/SKILL.md",
    "skills/skills-codex/paper-plan/SKILL.md",
    "skills/skills-codex/paper-figure/SKILL.md",
    "skills/skills-codex/paper-write/SKILL.md",
    "skills/skills-codex/paper-compile/SKILL.md",
    "skills/skills-codex/auto-paper-improvement-loop/SKILL.md",
    "skills/skills-codex/paper-illustration/SKILL.md",
    "skills/skills-codex/mermaid-diagram/SKILL.md",
    "skills/skills-codex-gemini-review/paper-writing/SKILL.md",
    "skills/skills-codex-gemini-review/paper-figure/SKILL.md",
    "skills/skills-codex-gemini-review/paper-write/SKILL.md",
    "skills/skills-codex-gemini-review/auto-paper-improvement-loop/SKILL.md",
    "skills/skills-codex-claude-review/paper-figure/SKILL.md",
    "skills/skills-codex-claude-review/paper-write/SKILL.md",
    "docs/LOCAL_DIRECTORY_CONTRACT.md",
}


SLIDES_FILES = {
    "README.md",
    "README_CN.md",
    "skills/paper-slides/SKILL.md",
    "skills/skills-codex/paper-slides/SKILL.md",
    "skills/skills-codex-gemini-review/paper-slides/SKILL.md",
    "docs/LOCAL_DIRECTORY_CONTRACT.md",
}


POSTER_FILES = {
    "README.md",
    "README_CN.md",
    "skills/paper-poster/SKILL.md",
    "skills/skills-codex/paper-poster/SKILL.md",
    "skills/skills-codex-gemini-review/paper-poster/SKILL.md",
    "docs/LOCAL_DIRECTORY_CONTRACT.md",
}


REBUTTAL_FILES = {
    "README.md",
    "README_CN.md",
    "skills/rebuttal/SKILL.md",
    "skills/skills-codex/rebuttal/SKILL.md",
    "docs/LOCAL_DIRECTORY_CONTRACT.md",
}


GRANT_FILES = {
    "skills/grant-proposal/SKILL.md",
    "skills/skills-codex/grant-proposal/SKILL.md",
    "skills/skills-codex-gemini-review/grant-proposal/SKILL.md",
    "docs/LOCAL_DIRECTORY_CONTRACT.md",
}


def apply_regexes(text: str, replacements: list[tuple[str, str]]) -> str:
    out = text
    for pattern, replacement in replacements:
        out = re.sub(pattern, replacement, out)
    return out


def apply_global_contract(text: str) -> str:
    out = apply_regexes(text, RESEARCH_GLOBAL_REPLACEMENTS)
    out = apply_regexes(out, LITERATURE_GLOBAL_REPLACEMENTS)
    out = re.sub(r"literature/\*\*/\.pdf,\s*literature/\*\*/\.pdf", "literature/**/*.pdf", out)
    out = re.sub(r"literature/\*\*/paper\.md,\s*literature/\*\*/\.pdf", "literature/**/paper.md, literature/**/*.pdf", out)
    return out


def apply_paper_pipeline(text: str) -> str:
    out = text
    exact_pairs = [
        ("`paper/`", "`writing/paper/`"),
        ('"paper/"', '"writing/paper/"'),
        (" paper/", " writing/paper/"),
        ("`paper/main.pdf`", "`writing/paper/main.pdf`"),
        ("`paper/main.tex`", "`writing/paper/main.tex`"),
        ("`paper/main.log`", "`writing/paper/main.log`"),
        ("paper/main.pdf", "writing/paper/main.pdf"),
        ("paper/main.tex", "writing/paper/main.tex"),
        ("paper/main.log", "writing/paper/main.log"),
        ("paper/sections/*.tex", "writing/paper/sections/*.tex"),
        ("paper/PAPER_IMPROVEMENT_LOG.md", "writing/paper/PAPER_IMPROVEMENT_LOG.md"),
        ("paper-backup-{timestamp}/", "writing/paper-backup-{timestamp}/"),
        ("figures/latex_includes.tex", "writing/paper/figures/latex_includes.tex"),
        ("figures/ai_generated/", "writing/paper/figures/ai_generated/"),
        ("mkdir -p figures", "mkdir -p writing/paper/figures"),
        ("FIG_DIR = `figures/`", "FIG_DIR = `writing/paper/figures/`"),
        ("Output directory for generated figures", "Output directory for generated paper figures"),
        ("`figures/` directory", "`writing/paper/figures/` directory"),
        ("to figures/ before proceeding", "to writing/paper/figures/ before proceeding"),
        ("to figures/ before I proceed", "to writing/paper/figures/ before I proceed"),
        ("placed in `figures/`", "placed in `writing/paper/figures/`"),
        ("files in `figures/`", "files in `writing/paper/figures/`"),
        ("JSON files in `figures/`", "JSON files in `writing/paper/figures/`"),
        ("CSV files, or screen logs in `figures/` or project root", "CSV files, or screen logs in `writing/paper/figures/` or project root"),
        ("writing/paper/", "writing/paper/"),
    ]
    for old, new in exact_pairs:
        out = out.replace(old, new)
    return out


def apply_slides_contract(text: str) -> str:
    out = text
    pairs = [
        ("`slides/`", "`writing/slides/`"),
        ('"slides/"', '"writing/slides/"'),
        (" slides/", " writing/slides/"),
        ("slides/SLIDES_STATE.json", "writing/slides/SLIDES_STATE.json"),
        ("slides/SLIDE_OUTLINE.md", "writing/slides/SLIDE_OUTLINE.md"),
        ("slides/main.tex", "writing/slides/main.tex"),
        ("slides/main.pdf", "writing/slides/main.pdf"),
        ("slides/speaker_notes.md", "writing/slides/speaker_notes.md"),
        ("slides/generate_pptx.py", "writing/slides/generate_pptx.py"),
        ("slides/presentation.pptx", "writing/slides/presentation.pptx"),
        ("slides/TALK_SCRIPT.md", "writing/slides/TALK_SCRIPT.md"),
        ("slides/SLIDES_REVIEW.md", "writing/slides/SLIDES_REVIEW.md"),
        ("slides/figures/", "writing/slides/figures/"),
        ("slides-backup-{timestamp}/", "writing/slides-backup-{timestamp}/"),
        ("`paper/`", "`writing/paper/`"),
        ('"paper/"', '"writing/paper/"'),
        ("paper/sections/*.tex", "writing/paper/sections/*.tex"),
        ("paper/figures/", "writing/paper/figures/"),
        ("$PAPER_DIR = `paper/`", "$PAPER_DIR = `writing/paper/`"),
        ("writing/slides/", "writing/slides/"),
    ]
    for old, new in pairs:
        out = out.replace(old, new)
    return out


def apply_poster_contract(text: str) -> str:
    out = text
    pairs = [
        ("`poster/`", "`writing/poster/`"),
        ('"poster/"', '"writing/poster/"'),
        (" poster/", " writing/poster/"),
        ("poster/POSTER_STATE.json", "writing/poster/POSTER_STATE.json"),
        ("poster/POSTER_CONTENT_PLAN.md", "writing/poster/POSTER_CONTENT_PLAN.md"),
        ("poster/main.tex", "writing/poster/main.tex"),
        ("poster/main.pdf", "writing/poster/main.pdf"),
        ("poster/poster_review.png", "writing/poster/poster_review.png"),
        ("poster/POSTER_VISUAL_REVIEW.md", "writing/poster/POSTER_VISUAL_REVIEW.md"),
        ("poster/POSTER_REVIEW.md", "writing/poster/POSTER_REVIEW.md"),
        ("poster/generate_pptx.py", "writing/poster/generate_pptx.py"),
        ("poster/poster.pptx", "writing/poster/poster.pptx"),
        ("poster/poster.svg", "writing/poster/poster.svg"),
        ("poster/poster_preview.png", "writing/poster/poster_preview.png"),
        ("poster/poster_components.pptx", "writing/poster/poster_components.pptx"),
        ("poster/POSTER_SPEECH.md", "writing/poster/POSTER_SPEECH.md"),
        ("poster/figures/", "writing/poster/figures/"),
        ("poster-backup-{timestamp}/", "writing/poster-backup-{timestamp}/"),
        ("`paper/`", "`writing/paper/`"),
        ('"paper/"', '"writing/paper/"'),
        ("paper/sections/*.tex", "writing/paper/sections/*.tex"),
        ("paper/figures/", "writing/paper/figures/"),
        ("$PAPER_DIR = `paper/`", "$PAPER_DIR = `writing/paper/`"),
        ("writing/poster/", "writing/poster/"),
    ]
    for old, new in pairs:
        out = out.replace(old, new)
    return out


def apply_rebuttal_contract(text: str) -> str:
    out = text
    pairs = [
        ("`rebuttal/`", "`writing/rebuttal/`"),
        ('"rebuttal/"', '"writing/rebuttal/"'),
        (" rebuttal/", " writing/rebuttal/"),
        ("rebuttal/REBUTTAL_STATE.md", "writing/rebuttal/REBUTTAL_STATE.md"),
        ("rebuttal/REVIEWS_RAW.md", "writing/rebuttal/REVIEWS_RAW.md"),
        ("rebuttal/ISSUE_BOARD.md", "writing/rebuttal/ISSUE_BOARD.md"),
        ("rebuttal/STRATEGY_PLAN.md", "writing/rebuttal/STRATEGY_PLAN.md"),
        ("rebuttal/REBUTTAL_EXPERIMENT_PLAN.md", "writing/rebuttal/REBUTTAL_EXPERIMENT_PLAN.md"),
        ("rebuttal/REBUTTAL_EXPERIMENTS.md", "writing/rebuttal/REBUTTAL_EXPERIMENTS.md"),
        ("rebuttal/REBUTTAL_DRAFT_v1.md", "writing/rebuttal/REBUTTAL_DRAFT_v1.md"),
        ("rebuttal/PASTE_READY.txt", "writing/rebuttal/PASTE_READY.txt"),
        ("rebuttal/MCP_STRESS_TEST.md", "writing/rebuttal/MCP_STRESS_TEST.md"),
        ("rebuttal/REBUTTAL_DRAFT_rich.md", "writing/rebuttal/REBUTTAL_DRAFT_rich.md"),
        ("rebuttal/FOLLOWUP_LOG.md", "writing/rebuttal/FOLLOWUP_LOG.md"),
        ("writing/rebuttal/", "writing/rebuttal/"),
    ]
    for old, new in pairs:
        out = out.replace(old, new)
    return out


def apply_grant_contract(text: str) -> str:
    out = text
    pairs = [
        ("`grant-proposal/`", "`writing/grant-proposal/`"),
        ("grant-proposal/figures/", "writing/grant-proposal/figures/"),
        ("writing/grant-proposal/", "writing/grant-proposal/"),
    ]
    for old, new in pairs:
        out = out.replace(old, new)
    return out


def main() -> None:
    changed = 0
    for path in iter_text_files():
        original = path.read_text()
        updated = apply_global_contract(original)

        r = rel(path)
        if r in PAPER_PIPELINE_FILES:
            updated = apply_paper_pipeline(updated)
        if r in SLIDES_FILES:
            updated = apply_slides_contract(updated)
        if r in POSTER_FILES:
            updated = apply_poster_contract(updated)
        if r in REBUTTAL_FILES:
            updated = apply_rebuttal_contract(updated)
        if r in GRANT_FILES:
            updated = apply_grant_contract(updated)

        # cleanup from overlapping replacements
        updated = updated.replace("research/", "research/")
        updated = updated.replace("writing/", "writing/")

        if updated != original:
            path.write_text(updated)
            changed += 1
            print(f"updated {r}")

    print(f"changed_files={changed}")


if __name__ == "__main__":
    main()
