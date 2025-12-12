#!/usr/bin/env python3
"""Validate Cross-References sections for authoritative docs."""

from __future__ import annotations

import sys
from pathlib import Path

from tools.doc_utils import anchorize, default_arg_parser


ROOT = Path(__file__).resolve().parent.parent


def section_lines(lines: list[str], heading: str) -> list[str]:
    heading_anchor = anchorize(heading)
    collected: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("#"):
            current = anchorize(line.lstrip("#").strip())
            if current == heading_anchor:
                in_section = True
                continue
            if in_section:
                break
        if in_section:
            collected.append(line)
    return collected


def main() -> int:
    parser = default_arg_parser("Check Cross-References sections.")
    args = parser.parse_args()
    paths = args.paths or list(ROOT.glob("documents/**/*.md")) + list(
        ROOT.glob("demo/**/documents/**/*.md")
    )
    errors: list[str] = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            continue
        if "**Status**: Authoritative source" not in lines[1]:
            continue
        section = section_lines(lines, "Cross-References")
        if not section:
            errors.append(f"{path}: missing Cross-References content")
            continue
        has_link = any("](" in line for line in section)
        if not has_link:
            errors.append(f"{path}: Cross-References section must contain links")
    if errors:
        for err in errors:
            print(f"❌ {err}")
        return 1
    print("✅ Cross-References sections are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
