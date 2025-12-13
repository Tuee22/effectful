#!/usr/bin/env python3
"""Code quality checker for HealthHub: Black (formatter) → MyPy (strict type checker).

This script runs formatting and type checking in sequence with fail-fast behavior.
All checks must pass (exit code 0) for the script to succeed.

Execution order:
1. Black: Code formatting (auto-formats)
2. MyPy --strict: Type checking with zero tolerance for type safety violations

Usage:
    poetry run check-code
    python -m tools.check_code
"""

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run Black formatting and MyPy strict type checking.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("=" * 80)
    print("HEALTHHUB CODE QUALITY CHECK")
    print("=" * 80)
    print()
    print("=" * 80)
    print("STEP 1/2: Black code formatting")
    print("=" * 80)

    black_result = subprocess.run(
        ["black", "--check", "backend", "tests", "tools"],
        check=False,
    )

    if black_result.returncode != 0:
        print("\n❌ Black failed (formatting required)!")
        print("=" * 80)
        return black_result.returncode

    print("\n✅ Black passed!")
    print("\n" + "=" * 80)
    print("STEP 2/2: MyPy strict type checking")
    print("=" * 80)

    # Get the root directory (where this script is run from)
    root_dir = Path.cwd()
    backend_dir = root_dir / "backend"
    stubs_dir = root_dir / "stubs"

    # Run mypy from backend directory to avoid module name conflicts
    # (app.database vs backend.app.database)
    # Set MYPYPATH to include stubs directory for asyncpg, redis, pydantic stubs
    env = dict(os.environ)
    env["MYPYPATH"] = str(stubs_dir)

    mypy_result = subprocess.run(
        ["mypy", "app"],
        check=False,
        cwd=backend_dir,
        env=env,
    )

    if mypy_result.returncode != 0:
        print("\n❌ MyPy failed on backend! Fix type errors before proceeding.")
        print("=" * 80)
        return mypy_result.returncode

    print("\n✅ Backend MyPy passed!")

    # Now run mypy on tests and tools from root
    # Include both stubs and backend in MYPYPATH for test imports
    test_env = dict(os.environ)
    test_env["MYPYPATH"] = f"{stubs_dir}:{backend_dir}"

    mypy_tests_result = subprocess.run(
        ["mypy", "tests/pytest", "tools"],
        check=False,
        cwd=root_dir,
        env=test_env,
    )

    if mypy_tests_result.returncode != 0:
        print("\n❌ MyPy failed on tests/tools! Fix type errors before proceeding.")
        print("=" * 80)
        return mypy_tests_result.returncode

    print("\n✅ Tests/Tools MyPy passed!")

    # Run documentation suite from effectful core (mdformat + PyMarkdown + codespell + custom checks)
    print("\n" + "=" * 80)
    print("STEP 3/3: Documentation suite (effectful library)")
    print("=" * 80)
    effectful_root = Path(__file__).resolve().parents[3]
    doc_suite_result = subprocess.run(
        ["python", "-m", "effectful_tools.doc_suite"],
        check=False,
        cwd=effectful_root,
        env=dict(os.environ, PYTHONPATH=os.environ.get("PYTHONPATH", str(effectful_root))),
    )

    if doc_suite_result.returncode != 0:
        print("\n❌ Documentation suite failed!")
        print("=" * 80)
        return doc_suite_result.returncode

    print("\n✅ Documentation suite passed!")
    print("\n" + "=" * 80)
    print("✅ ALL CHECKS PASSED!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
