#!/usr/bin/env python3
"""Validate demo documentation overlays."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

from effectful_tools.doc_utils import DOCS_DIR, DEMO_DIR, default_arg_parser


def base_doc_for_demo(path: Path) -> Path:
    relative = path.relative_to(DEMO_DIR)
    parts = relative.parts
    try:
        idx = parts.index("documents")
    except ValueError:
        return DOCS_DIR
    return DOCS_DIR / "/".join(parts[idx + 1 :])


def has_base_link(lines: list[str], expected_link: str) -> bool:
    """True if a base standard link appears near the top with the expected target."""
    return any("**📖 Base Standard**" in line and expected_link in line for line in lines[:15])


def _strip_metadata(lines: Iterable[str]) -> list[str]:
    """Remove metadata/purpose boilerplate for duplication checks."""
    filtered: list[str] = []
    skip_prefixes = {
        "# ",
        "**Status**:",
        "**Supersedes**:",
        "**Referenced by**:",
        "> **Purpose**:",
        "> **📖 Base Standard**",
        "> **📖 Authoritative Reference**",
    }
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(prefix) for prefix in skip_prefixes):
            continue
        if "**📖 Base Standard**" in stripped:
            continue
        filtered.append(stripped)
    return filtered


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
        rel_base = Path(os.path.relpath(base, path.parent)).as_posix()
        expected_link = f"[{base.name}]({rel_base})"
        if not has_base_link(lines, expected_link):
            errors.append(f"{path}: missing Base Standard link at top referencing {expected_link}")
        if not any(line.strip() == "## Deltas" for line in lines):
            errors.append(f"{path}: missing '## Deltas' section to scope overlay content")
        # Delta-only enforcement: overlay body should not largely duplicate base content.
        overlay_body = _strip_metadata(lines)
        base_body = (
            _strip_metadata(base.read_text(encoding="utf-8").splitlines()) if base.exists() else []
        )
        if overlay_body and base_body:
            shared = sum(1 for line in overlay_body if line in set(base_body))
            overlap = shared / max(len(overlay_body), 1)
            if overlap > 0.6 and len(overlay_body) >= 10:
                errors.append(
                    f"{path}: overlay duplicates base content ({overlap:.0%} line overlap); keep delta-only"
                )
    if errors:
        for err in errors:
            print(f"❌ {err}")
        return 1
    print("✅ Demo overlays are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
