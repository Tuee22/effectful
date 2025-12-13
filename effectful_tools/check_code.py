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

from effectful_tools import doc_suite


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
    steps: list[tuple[str, list[str] | None]] = [
        ("STEP 1/5: Black", ["black", "effectful", "tests", "effectful_tools"]),
        ("STEP 2/5: Ruff", ["ruff", "check", "effectful", "tests", "effectful_tools"]),
        ("STEP 3/5: MyPy", ["mypy", "effectful", "tests", "effectful_tools"]),
        ("STEP 4/5: Documentation suite", None),
        (
            "STEP 5/5: Functional catalogue",
            ["python", "-m", "effectful_tools.generate_functional_catalogue", "--check"],
        ),
    ]
    for name, command in steps:
        print("=" * 80)
        print(name)
        print("=" * 80)
        if command is None:
            code = doc_suite.run()
        else:
            result = subprocess.run(command, check=False)
            code = result.returncode
            if code != 0:
                print(f"\n❌ {name} failed.")
            else:
                print(f"\n✅ {name} passed.")
        if code != 0:
            return code
    print("\n✅ ALL CHECKS PASSED!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
