#!/usr/bin/env python3
"""Scan local paper packages and optionally backfill missing Markdown."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]+")


@dataclass
class Package:
    root: Path
    metadata_path: Path | None = None
    markdown_path: Path | None = None
    pdf_path: Path | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan local paper packages")
    parser.add_argument("--root", default="papers", help="Paper library root")
    parser.add_argument("--query", default="", help="Topic used to rank local packages")
    parser.add_argument("--limit", type=int, default=20, help="Max packages to print")
    parser.add_argument(
        "--ensure-markdown",
        action="store_true",
        help="Run pdf-to-md for top relevant packages missing paper.md",
    )
    parser.add_argument(
        "--max-markdown-conversions",
        type=int,
        default=5,
        help="Maximum missing-Markdown packages to convert when --ensure-markdown is set",
    )
    parser.add_argument(
        "--md-lang",
        default="en",
        choices=["en", "ch"],
        help="Language hint forwarded to pdf-to-md",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=1200,
        help="Characters of abstract/markdown preview to include",
    )
    return parser.parse_args()


def tokenize(query: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(query) if len(token) >= 2]


def read_text(path: Path, limit: int | None = None) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if limit is not None:
        return text[:limit]
    return text


def manual_metadata_fallback(text: str) -> dict:
    data: dict[str, object] = {}
    for key in ("title", "venue", "abstract", "foldername"):
        match = re.search(rf"^{key}:\s*['\"]?(.*?)['\"]?\s*$", text, flags=re.MULTILINE)
        if match:
            data[key] = match.group(1)
    match = re.search(r"^year:\s*(\d{4})\s*$", text, flags=re.MULTILINE)
    if match:
        data["year"] = int(match.group(1))

    authors: list[str] = []
    authors_block = re.search(r"^authors:\s*$([\s\S]*?)(?:^\S|\Z)", text, flags=re.MULTILINE)
    if authors_block:
        for line in authors_block.group(1).splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                authors.append(stripped[2:].strip(" '\""))
    if authors:
        data["authors"] = authors

    identifiers: dict[str, str] = {}
    id_block = re.search(r"^identifiers:\s*$([\s\S]*?)(?:^\S|\Z)", text, flags=re.MULTILINE)
    if id_block:
        for key in ("doi", "arxiv"):
            match = re.search(
                rf"^\s+{key}:\s*['\"]?(.*?)['\"]?\s*$",
                id_block.group(1),
                flags=re.MULTILINE,
            )
            if match:
                identifiers[key] = match.group(1)
    if identifiers:
        data["identifiers"] = identifiers
    return data


def load_metadata(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {}
    text = read_text(path)
    if yaml is not None:
        loaded = yaml.safe_load(text) or {}
        if isinstance(loaded, dict):
            return loaded
    return manual_metadata_fallback(text)


def discover_packages(root: Path) -> list[Package]:
    packages: dict[Path, Package] = {}

    def get_package(package_root: Path) -> Package:
        resolved = package_root.resolve()
        if resolved not in packages:
            packages[resolved] = Package(root=resolved)
        return packages[resolved]

    for metadata_path in root.rglob("metadata.yaml"):
        package = get_package(metadata_path.parent)
        package.metadata_path = metadata_path.resolve()
        markdown_path = package.root / "paper" / "paper.md"
        pdf_path = package.root / "paper" / "paper.pdf"
        if markdown_path.is_file():
            package.markdown_path = markdown_path
        if pdf_path.is_file():
            package.pdf_path = pdf_path

    for markdown_path in root.rglob("paper.md"):
        package_root = markdown_path.parent.parent if markdown_path.parent.name == "paper" else markdown_path.parent
        package = get_package(package_root)
        package.markdown_path = markdown_path.resolve()
        if package.metadata_path is None:
            metadata_path = package.root / "metadata.yaml"
            if metadata_path.is_file():
                package.metadata_path = metadata_path
        if package.pdf_path is None:
            pdf_path = package.root / "paper" / "paper.pdf"
            if pdf_path.is_file():
                package.pdf_path = pdf_path

    for pdf_path in root.rglob("*.pdf"):
        if pdf_path.parent.name == "paper":
            package_root = pdf_path.parent.parent
        else:
            package_root = pdf_path.parent
        package = get_package(package_root)
        if package.pdf_path is None:
            package.pdf_path = pdf_path.resolve()
        if package.metadata_path is None:
            metadata_path = package.root / "metadata.yaml"
            if metadata_path.is_file():
                package.metadata_path = metadata_path
        if package.markdown_path is None:
            markdown_path = package.root / "paper" / "paper.md"
            if markdown_path.is_file():
                package.markdown_path = markdown_path

    return sorted(packages.values(), key=lambda item: str(item.root))


def resolve_pdf_to_md_script() -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[2] / "pdf-to-md" / "scripts" / "mineru-api.py",
        Path.home() / ".agents" / "skills" / "pdf-to-md" / "scripts" / "mineru-api.py",
        Path.home() / ".claude" / "skills" / "pdf-to-md" / "scripts" / "mineru-api.py",
        Path.home() / ".codex" / "skills" / "pdf-to-md" / "scripts" / "mineru-api.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def ensure_markdown(package: Package, md_lang: str) -> str:
    if package.pdf_path is None:
        return "skipped:no-pdf"
    if package.markdown_path is not None and package.markdown_path.is_file():
        return "skipped:markdown-exists"
    if not os.environ.get("MINERU_API_TOKEN"):
        return "skipped:missing-mineru-token"
    script_path = resolve_pdf_to_md_script()
    if script_path is None:
        return "skipped:missing-pdf-to-md-script"

    try:
        subprocess.run(
            ["python3", str(script_path), str(package.pdf_path), "-l", md_lang],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip().splitlines()
        tail = stderr[-1] if stderr else f"exit-{exc.returncode}"
        return f"failed:{tail}"

    markdown_path = package.pdf_path.with_suffix(".md")
    if markdown_path.is_file():
        package.markdown_path = markdown_path.resolve()
        return "generated"
    return "failed:markdown-missing"


def package_type(package: Package) -> str:
    if package.metadata_path is not None:
        return "paper_import_package"
    if package.pdf_path is not None and package.pdf_path.parent.name == "paper":
        return "package_without_metadata"
    return "legacy_pdf"


def available_assets(package: Package) -> list[str]:
    assets: list[str] = []
    if package.metadata_path is not None:
        assets.append("metadata")
    if package.markdown_path is not None and package.markdown_path.is_file():
        assets.append("markdown")
    if package.pdf_path is not None and package.pdf_path.is_file():
        assets.append("pdf")
    if (package.root / "paper" / "main.tex").is_file() or (package.root / "paper" / "refs.bib").is_file():
        assets.append("latex")
    if (package.root / "repo").is_dir() or (package.root / "repo_search.json").is_file():
        assets.append("repo")
    return assets


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def build_record(package: Package, query_tokens: list[str], preview_chars: int) -> dict:
    metadata = load_metadata(package.metadata_path)
    title = str(metadata.get("title") or "")
    authors = metadata.get("authors") or []
    if not isinstance(authors, list):
        authors = [str(authors)]
    authors = [str(author) for author in authors]
    identifiers = metadata.get("identifiers") or {}
    if not isinstance(identifiers, dict):
        identifiers = {}
    abstract = str(metadata.get("abstract") or "")
    foldername = str(metadata.get("foldername") or "")

    markdown_preview = ""
    if package.markdown_path is not None and package.markdown_path.is_file():
        markdown_preview = read_text(package.markdown_path, limit=preview_chars)

    fields = [
        ("path", str(package.root), 5),
        ("foldername", foldername, 6),
        ("title", title, 8),
        ("abstract", abstract, 4),
        ("authors", " ".join(authors), 2),
        ("markdown", markdown_preview, 3),
    ]
    score = 0
    matched_fields: set[str] = set()
    for token in query_tokens:
        normalized_token = normalize_title(token)
        for field_name, field_text, weight in fields:
            if not field_text:
                continue
            haystack = field_text.lower()
            if token in haystack or normalized_token in normalize_title(field_text):
                score += weight
                matched_fields.add(field_name)

    preview_source = ""
    text_preview = ""
    if markdown_preview:
        preview_source = "markdown"
        text_preview = markdown_preview
    elif abstract:
        preview_source = "abstract"
        text_preview = abstract[:preview_chars]

    return {
        "package_root": str(package.root),
        "package_type": package_type(package),
        "score": score,
        "matched_fields": sorted(matched_fields),
        "title": title or package.root.name,
        "authors": authors,
        "year": metadata.get("year"),
        "venue": metadata.get("venue"),
        "foldername": foldername or package.root.name,
        "identifiers": {
            "doi": identifiers.get("doi"),
            "arxiv": identifiers.get("arxiv"),
        },
        "abstract": abstract[:preview_chars] if abstract else "",
        "metadata_path": str(package.metadata_path) if package.metadata_path else None,
        "markdown_path": str(package.markdown_path) if package.markdown_path else None,
        "pdf_path": str(package.pdf_path) if package.pdf_path else None,
        "available_assets": available_assets(package),
        "preview_source": preview_source,
        "text_preview": text_preview,
    }


def main() -> None:
    args = parse_args()
    root = Path(args.root).expanduser()
    if not root.exists():
        print("[]")
        return

    query_tokens = tokenize(args.query)
    packages = discover_packages(root)
    records = [build_record(package, query_tokens, args.preview_chars) for package in packages]
    ranked = sorted(
        zip(packages, records),
        key=lambda item: (-item[1]["score"], item[1]["title"].lower(), item[1]["package_root"]),
    )

    if args.ensure_markdown:
        conversions = 0
        refreshed = False
        for package, record in ranked:
            if conversions >= args.max_markdown_conversions:
                break
            if record["markdown_path"] is not None or record["pdf_path"] is None:
                continue
            if query_tokens and record["score"] <= 0:
                continue
            status = ensure_markdown(package, args.md_lang)
            record["markdown_conversion"] = status
            conversions += 1
            refreshed = refreshed or status == "generated"
        if refreshed:
            records = [build_record(package, query_tokens, args.preview_chars) for package in packages]
            ranked = sorted(
                zip(packages, records),
                key=lambda item: (-item[1]["score"], item[1]["title"].lower(), item[1]["package_root"]),
            )

    output = []
    for _, record in ranked[: args.limit]:
        output.append(record)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
