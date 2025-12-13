#!/usr/bin/env python3
"""Validate documentation header metadata blocks."""

from __future__ import annotations

import sys
from pathlib import Path

from effectful_tools.doc_utils import DOCS_DIR, DEMO_DIR, default_arg_parser


VALID_STATUS = {"authoritative source", "reference only", "deprecated"}


def normalize(line: str) -> str:
    return line.strip().lower()


def check_header(path: Path, strict: bool) -> list[str]:
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if not strict and all("**Status**" not in line for line in lines[:5]):
        return errors
    idx = 0
    # Skip leading empty lines or HTML comments
    while idx < len(lines) and (not lines[idx].strip() or lines[idx].strip().startswith("<!--")):
        idx += 1
    if idx >= len(lines) or not lines[idx].startswith("# "):
        return [f"{path}: first non-empty line must be an H1 title"]
    idx += 1
    # Skip blank lines between the H1 and metadata
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    expected_keys = ["**Status**:", "**Supersedes**:", "**Referenced by**:"]
    status_value = ""
    for key in expected_keys:
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx >= len(lines) or not lines[idx].startswith(key):
            errors.append(f"{path}: missing header line '{key}' in required order")
        else:
            if key == "**Status**:":
                raw_value = lines[idx].split(":", 1)[1]
                status_value = normalize(raw_value).rstrip("\\").strip()
        idx += 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    purpose_block: list[str] = []
    if idx >= len(lines) or not lines[idx].startswith("> **Purpose**:"):
        errors.append(f"{path}: missing Purpose blockquote after metadata")
    else:
        while idx < len(lines) and (lines[idx].startswith(">") or not lines[idx].strip()):
            if lines[idx].startswith(">"):
                purpose_block.append(lines[idx])
            idx += 1
    if status_value not in VALID_STATUS:
        errors.append(f"{path}: Status must be one of {sorted(VALID_STATUS)}")
    if "reference only" in status_value:
        if not any("Authoritative Reference" in line for line in purpose_block):
            errors.append(f"{path}: Reference only docs must include Authoritative Reference line")
    if "authoritative source" in status_value:
        if "## Cross-References" not in "\n".join(lines):
            errors.append(
                f"{path}: Authoritative docs must include a '## Cross-References' section"
            )
    return errors


def main() -> int:
    parser = default_arg_parser("Check documentation header metadata.")
    args = parser.parse_args()
    paths = args.paths or list(DOCS_DIR.rglob("*.md")) + list(DEMO_DIR.rglob("documents/**/*.md"))
    errors: list[str] = []
    for path in paths:
        errors.extend(check_header(path, strict=args.strict))

    if errors:
        for err in errors:
            print(f"❌ {err}")
        return 1
    print("✅ Documentation headers are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
