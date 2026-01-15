#!/usr/bin/env python3
"""Shared utilities for documentation validation."""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence


# ROOT is the repository root (/app in container)
# Path: /app/src/python/effectful_tools/doc_utils.py -> /app
ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_DIR = ROOT / "documents"
DEMO_DIR = ROOT / "demo"


def iter_markdown_files(include_demo: bool = True) -> Iterator[Path]:
    """Yield all markdown files under documents/ and optional demo documents."""
    for path in sorted(DOCS_DIR.rglob("*.md")):
        yield path
    if include_demo and DEMO_DIR.exists():
        for path in sorted(DEMO_DIR.rglob("documents/**/*.md")):
            yield path


def anchorize(text: str) -> str:
    """Convert a heading text into a markdown anchor approximation."""
    anchor = text.strip().lower()
    anchor = re.sub(r"[^\w\s-]", "", anchor)
    anchor = re.sub(r"\s+", "-", anchor)
    return anchor


def find_headings(lines: Sequence[str]) -> dict[str, list[str]]:
    """Return map of anchors to the raw heading text for a file."""
    anchors: dict[str, list[str]] = {}
    for line in lines:
        if not line.startswith("#"):
            continue
        heading = line.lstrip("#").strip()
        if not heading:
            continue
        anchor = anchorize(heading)
        anchors.setdefault(anchor, []).append(heading)
    return anchors


def fenced_blocks(lines: Sequence[str]) -> Iterator[tuple[int, str, list[str]]]:
    """Yield (start_index, language, body_lines) for each fenced code block."""
    in_block = False
    lang = ""
    body: list[str] = []
    start = 0
    for idx, line in enumerate(lines):
        if line.startswith("```") and not in_block:
            in_block = True
            lang = line.strip()[3:].strip()
            start = idx
            body = []
            continue
        if line.startswith("```") and in_block:
            yield (start, lang, body)
            in_block = False
            lang = ""
            body = []
            continue
        if in_block:
            body.append(line.rstrip("\n"))


def is_repo_github_link(link: str) -> bool:
    """Return True if link points to this repo on GitHub."""
    return "github.com" in link and "effectful" in link


def default_arg_parser(description: str) -> argparse.ArgumentParser:
    """Create an argparse parser with a --paths option."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional list of markdown files to check; defaults to documents/ and demo docs.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation modes for scripts that support it.",
    )
    return parser


@dataclass(frozen=True)
class CanonicalDiagram:
    """Canonical Mermaid diagram metadata extracted from docs."""

    kind: str
    identifier: str
    summary: str
    path: Path
    anchor: str
    is_demo: bool
    base_id: str | None


def hash_block(lines: Iterable[str]) -> str:
    """Stable hash of a block for uniqueness checks."""
    sha = hashlib.sha256()
    for line in lines:
        sha.update(line.encode("utf-8"))
    return sha.hexdigest()
