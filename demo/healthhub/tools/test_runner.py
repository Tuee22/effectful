#!/usr/bin/env python3
"""Test runner for HealthHub application.

Provides separate entrypoints for running different test categories:
- Backend tests: Fast tests using pytest-mock only (no real infrastructure)
- Integration tests: Tests against real PostgreSQL, Redis, Pulsar, MinIO
- E2E tests: Browser automation tests using Playwright (ShipNorth pattern)
- All tests: Complete test suite

Usage:
    poetry run test-all
    poetry run test-backend
    poetry run test-integration
    poetry run test-e2e
"""

import os
import subprocess
import sys


def run_backend() -> int:
    """Run backend unit tests only (pytest-mock, no real infrastructure).

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("=" * 80)
    print("HEALTHHUB BACKEND UNIT TESTS")
    print("=" * 80)
    print("Infrastructure: Mocked (no I/O)")
    print("Expected duration: <1 second")
    print("=" * 80)

    result = subprocess.run(
        ["python", "-m", "pytest", "tests/pytest/backend", "-v"],
        check=False,
    )

    if result.returncode != 0:
        print("\n❌ Backend unit tests failed!")
        print("=" * 80)
        return result.returncode

    print("\n✅ Backend unit tests passed!")
    print("=" * 80)
    return 0


def run_integration() -> int:
    """Run integration tests that require real infrastructure.

    These tests use real PostgreSQL, Redis, Pulsar, and MinIO services
    from Docker Compose. They are slower than unit tests but validate
    actual infrastructure behavior.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("=" * 80)
    print("HEALTHHUB INTEGRATION TESTS")
    print("=" * 80)
    print("Infrastructure: PostgreSQL, Redis, Pulsar, MinIO")
    print("Expected duration: 1-2 seconds")
    print("=" * 80)

    result = subprocess.run(
        ["python", "-m", "pytest", "tests/pytest/integration", "-v"],
        check=False,
    )

    if result.returncode != 0:
        print("\n❌ Integration tests failed!")
        print("=" * 80)
        return result.returncode

    print("\n✅ Integration tests passed!")
    print("=" * 80)
    return 0


def reseed_database() -> int:
    """Reseed the database with demo data for E2E tests.

    This ensures that E2E tests have the expected users and data available,
    especially after integration tests may have truncated tables.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("Reseeding database for E2E tests...")
    env = os.environ.copy()
    db_host = env.get("POSTGRES_HOST", "postgres")
    db_user = env.get("POSTGRES_USER", "healthhub")
    db_name = env.get("POSTGRES_DB", "healthhub_db")
    db_password = env.get("POSTGRES_PASSWORD", "healthhub_secure_pass")
    env["PGPASSWORD"] = db_password
    result = subprocess.run(
        [
            "psql",
            "-h",
            db_host,
            "-U",
            db_user,
            "-d",
            db_name,
            "-f",
            "/app/healthhub/backend/scripts/seed_data.sql",
        ],
        env=env,
        check=False,
        capture_output=True,
    )

    if result.returncode != 0:
        print(f"Failed to reseed database: {result.stderr.decode()}")
        return result.returncode

    print("Database reseeded successfully!")
    return 0


def run_e2e() -> int:
    """Run E2E browser tests using Playwright (ShipNorth pattern).

    These tests use Playwright to automate browser interactions against
    the running frontend service. Tests run across Chromium, Firefox, and WebKit.

    Key patterns from ShipNorth:
    - Function-scoped browser fixtures (prevents resource exhaustion)
    - ADT state synchronization (no timing hacks)
    - Storage clearing after each test (prevents auth token leakage)
    - TRUNCATE + seed before each test (reproducible starting state)

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Reseed database before E2E tests (integration tests may have truncated)
    reseed_result = reseed_database()
    if reseed_result != 0:
        return reseed_result

    print("=" * 80)
    print("HEALTHHUB E2E BROWSER TESTS")
    print("=" * 80)
    print("Infrastructure: Playwright (Chromium, Firefox, WebKit)")
    frontend_url = os.environ.get("E2E_FRONTEND_URL", "http://localhost:8851")
    backend_url = os.environ.get("E2E_BACKEND_URL", "http://localhost:8851")
    expected_url = "http://localhost:8851"
    if frontend_url != expected_url or backend_url != expected_url:
        print(
            "❌ E2E base URLs must target the compose-managed server (http://localhost:8851). "
            "Do not start ad-hoc uvicorn servers or override ports. "
            "See documents/engineering/docker_workflow.md#port-and-server-policy."
        )
        return 1
    print(f"Target: Frontend at {frontend_url}")
    print("Expected duration: 5-15 minutes (53 tests × 3 browsers)")
    print("=" * 80)

    env = os.environ.copy()
    env["E2E_FRONTEND_URL"] = frontend_url
    env["E2E_BACKEND_URL"] = backend_url

    result = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "tests/pytest/e2e",
            "-v",
            "--tb=short",
        ],
        env=env,
        check=False,
    )

    if result.returncode != 0:
        print("\n❌ E2E tests failed!")
        print("=" * 80)
        return result.returncode

    print("\n✅ E2E tests passed!")
    print("=" * 80)
    return 0


def run_all() -> int:
    """Run all tests (backend + integration + e2e).

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    print("=" * 80)
    print("HEALTHHUB FULL TEST SUITE")
    print("=" * 80)
    print("Infrastructure: Mixed (mocks + real infrastructure + browsers)")
    print("Expected duration: 5-15 minutes")
    print("=" * 80)

    # Run backend tests first (fastest)
    backend_result = run_backend()
    if backend_result != 0:
        return backend_result

    # Run integration tests
    integration_result = run_integration()
    if integration_result != 0:
        return integration_result

    # Run E2E tests last (slowest)
    e2e_result = run_e2e()
    if e2e_result != 0:
        return e2e_result

    print("\n✅ All tests passed!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    # Allow running directly with function name as argument
    if len(sys.argv) > 1:
        if sys.argv[1] == "backend":
            sys.exit(run_backend())
        elif sys.argv[1] == "integration":
            sys.exit(run_integration())
        elif sys.argv[1] == "e2e":
            sys.exit(run_e2e())
        elif sys.argv[1] == "all":
            sys.exit(run_all())
        else:
            print(f"Unknown test category: {sys.argv[1]}")
            print("Usage: python -m tools.test_runner [backend|integration|e2e|all]")
            sys.exit(1)
    else:
        # Default to all tests
        sys.exit(run_all())
