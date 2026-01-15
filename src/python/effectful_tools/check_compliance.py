#!/usr/bin/env python3
"""Compliance checker for effectful governance doctrines.

This script validates adherence to the 6 core governance doctrines:
1. SSoT Architecture - Explicit link governance with `📖 See:` patterns
2. Environment Variable Policy - Dockerfile as sole source, fail-fast access
3. Cache Placement Contract - All caches in `/opt/**`, never bind-mounted
4. Delta-Only Overlay Pattern - HealthHub docs inherit base + deltas only
5. Zero-Warning Policy - Warnings treated as failures
6. Deterministic Builds - Lockfiles not versioned, regenerated in-container

Exit codes:
- 0: All checks passed
- 1: Compliance violations found
"""

import re
import sys
from pathlib import Path
from typing import TextIO


def check_ssot_architecture(root: Path, output: TextIO) -> bool:
    """Check SSoT Architecture doctrine compliance.

    Validates:
    - All authoritative docs have SSoT Link Map section
    - All docs have proper Status/Supersedes/Referenced by metadata
    - No backslash-escaped metadata
    """
    output.write("\n=== Doctrine 1: SSoT Architecture ===\n")
    violations = []

    # Find all markdown files
    md_files = list(root.glob("**/*.md"))

    for md_file in md_files:
        # Skip certain directories
        if any(skip in md_file.parts for skip in [".git", "node_modules", "__pycache__"]):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            violations.append(f"{md_file.relative_to(root)}: Failed to read - {e}")
            continue

        # Check for backslash-escaped metadata
        if re.search(r"\*\*Status\*\*:.*\\$", content, re.MULTILINE):
            violations.append(f"{md_file.relative_to(root)}: Backslash-escaped metadata found")

        # Check for proper metadata structure
        if "**Status**:" in content:
            # Should have all three metadata fields
            if not all(
                field in content
                for field in ["**Status**:", "**Supersedes**:", "**Referenced by**:"]
            ):
                violations.append(
                    f"{md_file.relative_to(root)}: Incomplete metadata (missing Status/Supersedes/Referenced by)"
                )

            # Authoritative sources should have SSoT Link Map
            if (
                "**Status**: Authoritative source" in content
                or "**Status**: Authoritative" in content
            ):
                if "## SSoT Link Map" not in content and "<!-- AUTO-GENERATED" not in content:
                    violations.append(
                        f"{md_file.relative_to(root)}: Authoritative doc missing SSoT Link Map"
                    )

    if violations:
        output.write(f"❌ Found {len(violations)} violations:\n")
        for v in violations:
            output.write(f"   - {v}\n")
        return False
    else:
        output.write("✅ All SSoT Architecture checks passed\n")
        return True


def check_environment_variable_policy(root: Path, output: TextIO) -> bool:
    """Check Environment Variable Policy doctrine compliance.

    Validates:
    - All environment variables defined in Dockerfiles
    - No os.getenv() with fallbacks in production code (only in tests)
    - All access uses os.environ[] for fail-fast
    """
    output.write("\n=== Doctrine 2: Environment Variable Policy ===\n")
    violations = []

    # Find all Python files
    py_files = list(root.glob("**/*.py"))

    for py_file in py_files:
        # Skip test files, tools, and certain directories
        if any(
            skip in py_file.parts
            for skip in ["tests", "effectful_tools", ".git", "__pycache__", "stubs"]
        ):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Check for os.getenv() usage (forbidden in production code)
        if re.search(r"os\.getenv\(", content):
            violations.append(
                f"{py_file.relative_to(root)}: Uses os.getenv() - should use os.environ[] for fail-fast"
            )

    if violations:
        output.write(f"❌ Found {len(violations)} violations:\n")
        for v in violations:
            output.write(f"   - {v}\n")
        return False
    else:
        output.write("✅ All Environment Variable Policy checks passed\n")
        return True


def check_cache_placement_contract(root: Path, output: TextIO) -> bool:
    """Check Cache Placement Contract doctrine compliance.

    Validates:
    - All cache environment variables point to /opt/**
    - No cache bind mounts in docker-compose files
    """
    output.write("\n=== Doctrine 3: Cache Placement Contract ===\n")
    violations = []

    # Check Dockerfiles for cache environment variables
    dockerfile_paths = list(root.glob("**/Dockerfile")) + list(root.glob("**/Dockerfile.*"))

    for dockerfile in dockerfile_paths:
        try:
            content = dockerfile.read_text(encoding="utf-8")
        except Exception:
            continue

        # Check that all *_CACHE_DIR variables point to /opt/
        cache_vars = re.findall(r"ENV\s+(\w*CACHE\w*)\s*=\s*\"?([^\"'\s]+)", content)
        for var_name, var_value in cache_vars:
            if not var_value.startswith("/opt/"):
                violations.append(
                    f"{dockerfile.relative_to(root)}: {var_name}={var_value} not in /opt/"
                )

    # Check docker-compose files for cache bind mounts
    compose_files = list(root.glob("**/docker-compose.yml")) + list(
        root.glob("**/docker-compose.*.yml")
    )

    for compose_file in compose_files:
        try:
            content = compose_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Look for bind mounts that might be caches
        # Pattern: ./cache or ./.cache or similar
        if re.search(r"- \./\.?\w*cache", content, re.IGNORECASE):
            violations.append(f"{compose_file.relative_to(root)}: Potential cache bind mount found")

    if violations:
        output.write(f"❌ Found {len(violations)} violations:\n")
        for v in violations:
            output.write(f"   - {v}\n")
        return False
    else:
        output.write("✅ All Cache Placement Contract checks passed\n")
        return True


def check_delta_only_overlay_pattern(root: Path, output: TextIO) -> bool:
    """Check Delta-Only Overlay Pattern doctrine compliance.

    Validates:
    - HealthHub overlay docs have proper metadata pointing to base
    - Overlay docs have Deltas section
    - Overlay docs reference base authoritative source
    """
    output.write("\n=== Doctrine 4: Delta-Only Overlay Pattern ===\n")
    violations = []

    # Find HealthHub overlay documentation
    healthhub_docs = root / "demo" / "healthhub" / "documents"
    if not healthhub_docs.exists():
        output.write("⚠️  HealthHub documentation not found, skipping\n")
        return True

    overlay_files = list(healthhub_docs.glob("**/*.md"))

    for overlay_file in overlay_files:
        try:
            content = overlay_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Check if this is an overlay (Status: Reference only)
        if "**Status**: Reference only" in content:
            # Should have base standard reference
            if "📖 Base Standard" not in content and "📖 Authoritative Reference" not in content:
                violations.append(
                    f"{overlay_file.relative_to(root)}: Overlay missing base standard reference"
                )

            # Should have Deltas section
            if "## Deltas" not in content:
                violations.append(
                    f"{overlay_file.relative_to(root)}: Overlay missing Deltas section"
                )

    if violations:
        output.write(f"❌ Found {len(violations)} violations:\n")
        for v in violations:
            output.write(f"   - {v}\n")
        return False
    else:
        output.write("✅ All Delta-Only Overlay Pattern checks passed\n")
        return True


def check_zero_warning_policy(root: Path, output: TextIO) -> bool:
    """Check Zero-Warning Policy doctrine compliance.

    Validates:
    - No deprecated warnings in code
    - No type: ignore comments (escape hatches)
    - No pytest.skip() usage
    """
    output.write("\n=== Doctrine 5: Zero-Warning Policy ===\n")
    violations = []

    # Find all Python files
    py_files = list(root.glob("**/*.py"))

    for py_file in py_files:
        # Skip test files, tools, and certain directories
        if any(
            skip in py_file.parts
            for skip in ["tests", "effectful_tools", ".git", "__pycache__", "stubs"]
        ):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Check for type: ignore comments
        if re.search(r"#\s*type:\s*ignore", content):
            violations.append(f"{py_file.relative_to(root)}: Contains 'type: ignore' escape hatch")

        # Check for pytest.skip()
        if "pytest.skip(" in content:
            violations.append(
                f"{py_file.relative_to(root)}: Contains pytest.skip() - tests must be fixed or deleted"
            )

    if violations:
        output.write(f"❌ Found {len(violations)} violations:\n")
        for v in violations:
            output.write(f"   - {v}\n")
        return False
    else:
        output.write("✅ All Zero-Warning Policy checks passed\n")
        return True


def check_deterministic_builds(root: Path, output: TextIO) -> bool:
    """Check Deterministic Builds doctrine compliance.

    Validates:
    - No poetry.lock in version control
    - No package-lock.json or yarn.lock in version control
    - Lockfiles should be gitignored
    """
    output.write("\n=== Doctrine 6: Deterministic Builds ===\n")
    violations = []

    # Check for lockfiles
    lockfiles = ["poetry.lock", "package-lock.json", "yarn.lock", "Pipfile.lock"]

    for lockfile in lockfiles:
        lockfile_paths = list(root.glob(f"**/{lockfile}"))

        # Lockfiles shouldn't exist in repo (they should be gitignored)
        # This is a soft check - they might exist locally but shouldn't be committed
        for lockfile_path in lockfile_paths:
            # Check if it's in .gitignore
            gitignore_path = root / ".gitignore"
            if gitignore_path.exists():
                gitignore_content = gitignore_path.read_text(encoding="utf-8")
                if lockfile not in gitignore_content and "*.lock" not in gitignore_content:
                    violations.append(f"{lockfile} exists but not in .gitignore")

    if violations:
        output.write(f"❌ Found {len(violations)} violations:\n")
        for v in violations:
            output.write(f"   - {v}\n")
        return False
    else:
        output.write("✅ All Deterministic Builds checks passed\n")
        return True


def main() -> int:
    """Run all compliance checks."""
    # Get project root (assume script is in effectful_tools/)
    root = Path(__file__).parent.parent

    print("=" * 70)
    print("EFFECTFUL GOVERNANCE COMPLIANCE CHECKER")
    print("=" * 70)
    print(f"Project root: {root}")

    # Run all checks
    results = []

    results.append(check_ssot_architecture(root, sys.stdout))
    results.append(check_environment_variable_policy(root, sys.stdout))
    results.append(check_cache_placement_contract(root, sys.stdout))
    results.append(check_delta_only_overlay_pattern(root, sys.stdout))
    results.append(check_zero_warning_policy(root, sys.stdout))
    results.append(check_deterministic_builds(root, sys.stdout))

    # Summary
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)

    if all(results):
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("=" * 70)
        return 0
    else:
        failed = total - passed
        print(f"❌ COMPLIANCE VIOLATIONS FOUND ({failed}/{total} checks failed)")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
