#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "README.md",
    ROOT / "README_CN.md",
    *sorted(
        path
        for path in (ROOT / "skills").rglob("*.md")
        if not any(part.startswith("skills-codex") for part in path.parts)
    ),
]

CHECKS = [
    (re.compile(r"\brefine-logs/"), "old refine-logs/ path"),
    (re.compile(r"\bpapers/"), "old papers/ path"),
    (re.compile(r"writing/writing/"), "duplicated writing/ path"),
    (re.compile(r"writing/paper/review/"), "malformed writing/paper/review path"),
    (re.compile(r"\bexp/data[/\\]"), "data should be at project root, not under exp/"),
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    failures: list[str] = []
    for path in TARGETS:
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
