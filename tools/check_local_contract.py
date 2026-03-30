#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "__pycache__"}
TEXT_EXTS = {".md", ".py", ".txt", ".json", ".yaml", ".yml", ".toml", ".tex", ".sh"}


CHECKS = [
    (re.compile(r"research/refine/"), "old refine-logs path"),
    (re.compile(r"(?<!research/)RESEARCH_BRIEF\.md\b"), "root research/RESEARCH_BRIEF.md"),
    (re.compile(r"(?<!research/)IDEA_REPORT\.md\b"), "root research/IDEA_REPORT.md"),
    (re.compile(r"(?<!research/)AUTO_REVIEW\.md\b"), "root research/AUTO_REVIEW.md"),
    (re.compile(r"(?<!research/)REVIEW_STATE\.json\b"), "root research/REVIEW_STATE.json"),
    (re.compile(r"(?<!research/)IDEA_CANDIDATES\.md\b"), "root research/IDEA_CANDIDATES.md"),
    (re.compile(r"(?<!research/)EXPERIMENT_LOG\.md\b"), "root research/EXPERIMENT_LOG.md"),
    (re.compile(r"(?<!research/)findings\.md\b"), "root research/findings.md"),
    (re.compile(r"\bpapers/"), "old papers/ path"),
]


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTS and path.name not in {"README.md", "README_CN.md"}:
            continue
        try:
            path.read_text()
        except Exception:
            continue
        files.append(path)
    return files


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    failures: list[str] = []
    for path in iter_text_files():
        text = path.read_text()
        for regex, label in CHECKS:
            for match in regex.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{rel(path)}:{line}: {label}")

    if failures:
        print("local contract check failed:")
        for item in failures:
            print(item)
        return 1

    print("local contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
