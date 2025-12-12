#!/usr/bin/env python3
"""Validate demo documentation overlays."""

from __future__ import annotations

import sys
from pathlib import Path

from tools.doc_utils import DOCS_DIR, DEMO_DIR, default_arg_parser


def base_doc_for_demo(path: Path) -> Path:
    relative = path.relative_to(DEMO_DIR)
    parts = relative.parts
    try:
        idx = parts.index("documents")
    except ValueError:
        return DOCS_DIR
    return DOCS_DIR / "/".join(parts[idx + 1 :])


def has_base_link(lines: list[str]) -> bool:
    return any("**📖 Base Standard**" in line for line in lines[:5])


def main() -> int:
    parser = default_arg_parser("Check demo documentation overlays.")
    args = parser.parse_args()
    paths = args.paths or list(DEMO_DIR.rglob("documents/**/*.md"))
    errors: list[str] = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        base = base_doc_for_demo(path)
        if not base.exists():
            errors.append(f"{path}: missing corresponding base document {base}")
        if not has_base_link(lines):
            errors.append(f"{path}: missing Base Standard link at top")
    if errors:
        for err in errors:
            print(f"❌ {err}")
        return 1
    print("✅ Demo overlays are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
