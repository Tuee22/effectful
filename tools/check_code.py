#!/usr/bin/env python3
"""Code quality checker: MyPy (strict) → Black (formatter) → Ruff (linter).

This script runs type checking, formatting, and linting in sequence with fail-fast behavior.
All checks must pass (exit code 0) for the script to succeed.

Execution order:
1. MyPy --strict: Type checking with zero tolerance for type safety violations
2. Black: Code formatting (auto-formats if MyPy passes)
3. Ruff: Linting with 100+ rules (checks if Black passes)

Usage:
    poetry run check-code
    python -m tools.check_code
"""

import subprocess
import sys


def main() -> int:
    """Run MyPy strict type checking, Black formatting, and Ruff linting.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("=" * 80)
    print("STEP 1/3: MyPy strict type checking")
    print("=" * 80)

    mypy_result = subprocess.run(
        ["mypy", "effectful", "tests"],
        check=False,
    )

    if mypy_result.returncode != 0:
        print("\n❌ MyPy failed! Fix type errors before proceeding.")
        print("=" * 80)
        return mypy_result.returncode

    print("\n✅ MyPy passed!")
    print("\n" + "=" * 80)
    print("STEP 2/3: Black code formatting")
    print("=" * 80)

    black_result = subprocess.run(
        ["black", "effectful", "tests", "tools"],
        check=False,
    )

    if black_result.returncode != 0:
        print("\n❌ Black failed!")
        print("=" * 80)
        return black_result.returncode

    print("\n✅ Black passed!")
    print("\n" + "=" * 80)
    print("STEP 3/3: Ruff linting")
    print("=" * 80)

    ruff_result = subprocess.run(
        ["ruff", "check", "effectful", "tests", "tools"],
        check=False,
    )

    if ruff_result.returncode != 0:
        print("\n❌ Ruff linting failed!")
        print("=" * 80)
        return ruff_result.returncode

    print("\n✅ Ruff passed!")
    print("\n" + "=" * 80)
    print("✅ ALL CHECKS PASSED!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
