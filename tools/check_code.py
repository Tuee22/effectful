#!/usr/bin/env python3
"""Code quality checker: Black (formatter) → MyPy (strict type checker).

This script runs formatting and type checking in sequence with fail-fast behavior.
All checks must pass (exit code 0) for the script to succeed.

Execution order:
1. Black: Code formatting (auto-formats)
2. MyPy --strict: Type checking with zero tolerance for type safety violations

Usage:
    poetry run check-code
    python -m tools.check_code
"""

import subprocess
import sys


def main() -> int:
    """Run Black formatting and MyPy strict type checking.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("=" * 80)
    print("STEP 1/2: Black code formatting")
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
    print("STEP 2/2: MyPy strict type checking")
    print("=" * 80)

    mypy_result = subprocess.run(
        ["mypy", "effectful", "tests", "tools"],
        check=False,
    )

    if mypy_result.returncode != 0:
        print("\n❌ MyPy failed! Fix type errors before proceeding.")
        print("=" * 80)
        return mypy_result.returncode

    print("\n✅ MyPy passed!")
    print("\n" + "=" * 80)
    print("✅ ALL CHECKS PASSED!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
