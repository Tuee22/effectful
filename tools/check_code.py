#!/usr/bin/env python3
"""Comprehensive code + documentation gate.

Order:
1) black
2) ruff
3) mypy
4) mdformat --check
5) pymarkdown scan
6) codespell
7) Custom doc validators
8) Functional catalogue check
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parent.parent


def run_step(name: str, command: Sequence[str]) -> int:
    print("=" * 80)
    print(name)
    print("=" * 80)
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        print(f"\n❌ {name} failed.")
    else:
        print(f"\n✅ {name} passed.")
    return result.returncode


def main() -> int:
    pymarkdown_config = ROOT / "configs" / ".pymarkdown.json"
    codespell_config = ROOT / "configs" / ".codespellrc"
    steps: list[tuple[str, list[str]]] = [
        ("STEP 1/8: Black", ["black", "effectful", "tests", "tools"]),
        ("STEP 2/8: Ruff", ["ruff", "check", "effectful", "tests", "tools"]),
        ("STEP 3/8: MyPy", ["mypy", "effectful", "tests", "tools"]),
        (
            "STEP 4/8: mdformat",
            [
                "mdformat",
                "--check",
                "documents",
                "demo",
            ],
        ),
        (
            "STEP 5/8: PyMarkdown",
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
            "STEP 6/8: codespell",
            ["codespell", "--config", str(codespell_config), "documents", "demo"],
        ),
        ("STEP 7/8: Custom doc checks", ["python", "-m", "tools.run_doc_checks"]),
        (
            "STEP 8/8: Functional catalogue",
            ["python", "-m", "tools.generate_functional_catalogue", "--check"],
        ),
    ]
    for name, command in steps:
        code = run_step(name, command)
        if code != 0:
            return code
    print("\n✅ ALL CHECKS PASSED!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
