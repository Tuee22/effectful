#!/usr/bin/env python3
"""Enforce documentation filename and placement rules."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from tools.doc_utils import DOCS_DIR, DEMO_DIR, default_arg_parser


EXCEPTIONS = {"README.md", "AGENTS.md", "CLAUDE.md", "MIGRATION_PLAN.md"}
PATTERN = re.compile(r"^[a-z0-9_]+\.md$")
VERSION_PATTERN = re.compile(r"_v\d")


def validate_path(path: Path) -> list[str]:
    errors: list[str] = []
    name = path.name
    if name in EXCEPTIONS:
        return errors
    if not PATTERN.match(name):
        errors.append(f"{path}: filename must be snake_case markdown")
    if VERSION_PATTERN.search(name):
        errors.append(f"{path}: filename must not contain version suffixes")
    allowed = path.is_relative_to(DOCS_DIR) or (
        DEMO_DIR in path.parents and "documents" in path.parts
    )
    if not allowed:
        errors.append(f"{path}: markdown docs must reside in documents/ or demo/*/documents/")
    return errors


def main() -> int:
    parser = default_arg_parser("Check documentation filenames and placement.")
    args = parser.parse_args()
    paths = args.paths or list(DOCS_DIR.rglob("*.md")) + list(DEMO_DIR.rglob("documents/**/*.md"))

    errors: list[str] = []
    for path in paths:
        errors.extend(validate_path(path))

    if errors:
        for err in errors:
            print(f"❌ {err}")
        return 1

    print("✅ Documentation filenames and placement are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
