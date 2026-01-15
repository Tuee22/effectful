#!/usr/bin/env python3
"""Detect forbidden backup/temp artifacts in documentation directories."""

from __future__ import annotations

import sys
from pathlib import Path

from effectful_tools.doc_utils import DOCS_DIR, DEMO_DIR, default_arg_parser


FORBIDDEN_SUFFIXES = [
    ".bak",
    ".bak2",
    ".backup",
    ".old",
    ".tmp",
    ".temp",
    ".swp",
    ".swo",
    ".txt",
]
FORBIDDEN_TRAILING = "~"


def iter_doc_dirs() -> list[Path]:
    paths = [DOCS_DIR]
    if DEMO_DIR.exists():
        paths.extend(DEMO_DIR.glob("*/documents"))
    return paths


def main() -> int:
    parser = default_arg_parser("Check for forbidden artifacts in documentation directories.")
    _ = parser.parse_args()

    errors: list[str] = []
    for doc_dir in iter_doc_dirs():
        for path in doc_dir.rglob("*"):
            if path.is_dir():
                continue
            if any(path.name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
                errors.append(f"{path}: forbidden artifact suffix")
            if path.name.endswith(FORBIDDEN_TRAILING):
                errors.append(f"{path}: trailing '~' forbidden")

    if errors:
        for err in errors:
            print(f"❌ {err}")
        return 1

    print("✅ No forbidden doc artifacts found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
