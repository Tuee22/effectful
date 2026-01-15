#!/usr/bin/env python3
"""Validate documentation links and anchors."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from effectful_tools.doc_utils import anchorize, default_arg_parser, is_repo_github_link


ROOT = Path(__file__).resolve().parent.parent


def extract_links(content: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    idx = 0
    while True:
        start = content.find("[", idx)
        if start == -1:
            break
        end_text = content.find("]", start)
        if end_text == -1 or end_text + 1 >= len(content) or content[end_text + 1] != "(":
            idx = start + 1
            continue
        end_link = content.find(")", end_text)
        if end_link == -1:
            break
        text = content[start + 1 : end_text]
        link = content[end_text + 2 : end_link]
        links.append((text, link))
        idx = end_link + 1
    return links


def load_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            if heading:
                anchors.add(anchorize(heading))
    return anchors


def validate_link(
    source: Path, text: str, link: str, anchors_cache: dict[Path, set[str]]
) -> str | None:
    if is_repo_github_link(link):
        return f"{source}: link must be relative (no repo-absolute GitHub URLs): {link}"
    if link.startswith(("http://", "https://", "mailto:")):
        return None
    if link.startswith("#"):
        anchor = link[1:]
        if anchor and anchor not in anchors_cache.setdefault(source, load_anchors(source)):
            return f"{source}: missing anchor #{anchor}"
        return None
    target_path = (source.parent / link).resolve()
    target_anchor = None
    if "#" in link:
        path_str, anchor = link.split("#", 1)
        target_path = (source.parent / path_str).resolve()
        target_anchor = anchor
    if not target_path.exists():
        return f"{source}: target not found {target_path}"
    if target_anchor:
        anchors = anchors_cache.setdefault(target_path, load_anchors(target_path))
        if target_anchor not in anchors:
            return f"{source}: target missing anchor #{target_anchor} in {target_path}"
    bad_text = {"here", "this", "click here"}
    if text.strip().lower() in bad_text:
        return f"{source}: link text must be descriptive, not '{text}'"
    return None


def main() -> int:
    parser = default_arg_parser("Check documentation links.")
    args = parser.parse_args()
    paths: Iterable[Path] = args.paths or list(ROOT.glob("documents/**/*.md")) + list(
        ROOT.glob("demo/**/documents/**/*.md")
    )
    errors: list[str] = []
    anchors_cache: dict[Path, set[str]] = {}
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for text, link in extract_links(content):
            err = validate_link(path, text, link, anchors_cache)
            if err:
                errors.append(err)
    if errors:
        for err in errors:
            print(f"❌ {err}")
        return 1
    print("✅ Documentation links are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
