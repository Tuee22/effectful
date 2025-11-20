#!/usr/bin/env python3
"""Test runner for effectful library.

Provides separate entrypoints for running different test categories:
- Unit tests: Fast tests using pytest-mock only (no real infrastructure)
- Integration tests: Tests against real PostgreSQL, Redis, MinIO, Pulsar
- All tests: Complete test suite

Usage:
    poetry run test-all
    poetry run test-unit
    poetry run test-integration
"""

import subprocess
import sys
from typing import List


def run_unit() -> int:
    """Run unit tests only (pytest-mock, no real infrastructure).

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("=" * 80)
    print("Running Unit Tests (pytest-mock only)")
    print("=" * 80)
    print("Infrastructure: Mocked (no I/O)")
    print("Expected duration: <1 second")
    print("=" * 80)

    result = subprocess.run(
        ["pytest", "-m", "unit", "-v"],
        check=False,
    )

    if result.returncode != 0:
        print("\n❌ Unit tests failed!")
        print("=" * 80)
        return result.returncode

    print("\n✅ Unit tests passed!")
    print("=" * 80)
    return 0


def run_integration() -> int:
    """Run integration tests that require real infrastructure.

    These tests use real PostgreSQL, Redis, MinIO, and Pulsar services
    from Docker Compose. They are slower than unit tests but validate
    actual infrastructure behavior.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("=" * 80)
    print("Running Integration Tests (Real Infrastructure)")
    print("=" * 80)
    print("Infrastructure: PostgreSQL, Redis, MinIO, Pulsar")
    print("Expected duration: 1-2 seconds")
    print("=" * 80)

    result = subprocess.run(
        ["pytest", "-m", "integration", "-v"],
        check=False,
    )

    if result.returncode != 0:
        print("\n❌ Integration tests failed!")
        print("=" * 80)
        return result.returncode

    print("\n✅ Integration tests passed!")
    print("=" * 80)
    return 0


def run_all() -> int:
    """Run all tests (unit + integration + unmarked).

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("=" * 80)
    print("Running All Tests")
    print("=" * 80)
    print("Infrastructure: Mixed (mocks + real infrastructure)")
    print("Expected duration: 1-2 seconds")
    print("=" * 80)

    result = subprocess.run(
        ["pytest", "-v"],
        check=False,
    )

    if result.returncode != 0:
        print("\n❌ Tests failed!")
        print("=" * 80)
        return result.returncode

    print("\n✅ All tests passed!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    # Allow running directly with function name as argument
    if len(sys.argv) > 1:
        if sys.argv[1] == "unit":
            sys.exit(run_unit())
        elif sys.argv[1] == "integration":
            sys.exit(run_integration())
        elif sys.argv[1] == "all":
            sys.exit(run_all())
        else:
            print(f"Unknown test category: {sys.argv[1]}")
            print("Usage: python -m tools.test_runner [unit|integration|all]")
            sys.exit(1)
    else:
        # Default to all tests
        sys.exit(run_all())
