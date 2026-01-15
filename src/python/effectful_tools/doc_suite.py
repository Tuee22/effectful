#!/usr/bin/env python3
"""Shared documentation suite runner for core and demos.

Steps:
1) mdformat --check (documents + demo)
2) PyMarkdown scan (with configured rules)
3) codespell
4) Custom doc validators (run_doc_checks)
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


# ROOT is the repository root (/app in container)
# Path: /app/src/python/effectful_tools/doc_suite.py -> /app
ROOT = Path(__file__).resolve().parent.parent.parent.parent


def run_step(name: str, command: Sequence[str]) -> int:
    print(f"- {name}")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        print(f"❌ {name} failed.")
    else:
        print(f"✅ {name} passed.")
    return result.returncode


def run() -> int:
    pymarkdown_config = ROOT / "configs" / ".pymarkdown.json"
    codespell_config = ROOT / "configs" / ".codespellrc"
    steps: list[tuple[str, list[str]]] = [
        (
            "mdformat",
            [
                "mdformat",
                "--check",
                "documents",
                "demo",
            ],
        ),
        (
            "PyMarkdown",
            [
                "pymarkdown",
                "--config",
                str(pymarkdown_config),
                "--disable-rules",
                "md013,md036",
                "scan",
                "documents",
                "demo",
            ],
        ),
        (
            "codespell",
            ["codespell", "--config", str(codespell_config), "documents", "demo"],
        ),
        ("Custom doc checks", ["python", "-m", "effectful_tools.run_doc_checks"]),
    ]
    for name, command in steps:
        code = run_step(name, command)
        if code != 0:
            return code
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
