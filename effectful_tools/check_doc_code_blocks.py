#!/usr/bin/env python3
"""Validate fenced code blocks for language and first-line comment rules."""

from __future__ import annotations

import sys
from pathlib import Path

from effectful_tools.doc_utils import default_arg_parser, fenced_blocks


COMMENT_LANGS = {
    "python": "#",
    "py": "#",
    "bash": "#",
    "sh": "#",
    "shell": "#",
    "yaml": "#",
    "yml": "#",
    "toml": "#",
    "json": "//",
    "javascript": "//",
    "js": "//",
    "typescript": "//",
    "ts": "//",
}
FORBIDDEN_PATTERNS = ("Any", "cast(", "# type: ignore", "from typing import Any")


def is_wrong_example(lines: list[str], start_idx: int, all_lines: list[str]) -> bool:
    for i in range(start_idx - 3, start_idx):
        if i >= 0 and "Wrong" in all_lines[i]:
            return True
    return False


def main() -> int:
    parser = default_arg_parser("Check fenced code blocks for language and safety.")
    args = parser.parse_args()
    paths = args.paths or list(Path("documents").rglob("*.md")) + list(
        Path("demo").rglob("documents/**/*.md")
    )

    errors: list[str] = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for start, lang, body in fenced_blocks(lines):
            if not lang:
                errors.append(f"{path}:{start+1}: fenced code block missing language")
                continue
            if lang in COMMENT_LANGS and body:
                first_line = body[0].strip()
                comment_prefix = COMMENT_LANGS[lang]
                if not first_line.startswith(comment_prefix):
                    errors.append(
                        f"{path}:{start+1}: first non-empty line must be a comment in {lang} blocks"
                    )
            if lang == "python" and not is_wrong_example(body, start, lines):
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern in "\n".join(body):
                        errors.append(
                            f"{path}:{start+1}: forbidden pattern '{pattern}' in python block"
                        )
    if errors:
        for err in errors:
            print(f"❌ {err}")
        return 1
    print("✅ Code blocks are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
