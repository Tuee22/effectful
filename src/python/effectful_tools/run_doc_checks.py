#!/usr/bin/env python3
"""Run custom documentation validation scripts in sequence."""

from __future__ import annotations

import subprocess
import sys
from typing import Sequence


COMMANDS: list[tuple[str, Sequence[str]]] = [
    (
        "check_doc_filenames",
        ["python", "-m", "effectful_tools.check_doc_filenames", "--strict"],
    ),
    (
        "check_doc_artifacts",
        ["python", "-m", "effectful_tools.check_doc_artifacts", "--strict"],
    ),
    (
        "check_doc_headers",
        ["python", "-m", "effectful_tools.check_doc_headers", "--strict"],
    ),
    (
        "check_doc_links",
        ["python", "-m", "effectful_tools.check_doc_links", "--strict"],
    ),
    (
        "check_doc_crossrefs",
        ["python", "-m", "effectful_tools.check_doc_crossrefs", "--strict"],
    ),
    (
        "check_doc_code_blocks",
        ["python", "-m", "effectful_tools.check_doc_code_blocks", "--strict"],
    ),
    (
        "check_mermaid_metadata",
        ["python", "-m", "effectful_tools.check_mermaid_metadata", "--strict"],
    ),
    ("check_demo_docs", ["python", "-m", "effectful_tools.check_demo_docs", "--strict"]),
]


def run_step(name: str, command: Sequence[str]) -> int:
    print(f"- {name}")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        print(f"❌ {name} failed")
    else:
        print(f"✅ {name} passed")
    return result.returncode


def main() -> int:
    for name, command in COMMANDS:
        code = run_step(name, command)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
