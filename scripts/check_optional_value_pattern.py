#!/usr/bin/env python3
"""Verify OptionalValue normalization pattern in effects.

This script validates that effect files using OptionalValue follow the
canonical normalization pattern documented in:
    documents/api/optional_value.md#pattern-3-effect-parameters

Checks:
1. If OptionalValue is imported, ensure normalization function exists
2. If normalization exists, ensure it uses object.__setattr__ pattern
3. If normalization exists, ensure frozen dataclass with init=False

See: documents/engineering/effect_patterns.md#pattern-6-boundary-normalization
"""

import re
import sys
from pathlib import Path


def check_effect_file(filepath: Path) -> list[str]:
    """Check effect file for proper OptionalValue patterns.

    Args:
        filepath: Path to effect file to check

    Returns:
        List of error messages (empty if no errors)
    """
    errors = []
    content = filepath.read_text()

    # Check 1: If OptionalValue is imported, ensure normalization exists
    has_optional_value_import = (
        "from effectful.domain.optional_value import" in content
        or "from effectful.domain import.*OptionalValue" in content
    )

    has_normalization = "_normalize_optional" in content

    if has_optional_value_import and not has_normalization:
        errors.append(
            f"{filepath.name}: Imports OptionalValue but missing "
            "_normalize_optional_value() function. "
            "See: documents/api/optional_value.md#pattern-3"
        )

    # Check 2: If normalization exists, ensure object.__setattr__ pattern used
    if has_normalization:
        if "object.__setattr__" not in content:
            errors.append(
                f"{filepath.name}: Has normalization function but not using "
                "object.__setattr__ pattern for frozen dataclass. "
                "See: documents/engineering/effect_patterns.md#pattern-6"
            )

    # Check 3: If normalization exists, ensure frozen=True and init=False
    if has_normalization:
        # Look for dataclass decorators
        frozen_pattern = r"@dataclass\s*\(\s*frozen\s*=\s*True"
        init_false_pattern = r"@dataclass\s*\([^)]*init\s*=\s*False"

        has_frozen = bool(re.search(frozen_pattern, content))
        has_init_false = bool(re.search(init_false_pattern, content))

        if not has_frozen:
            errors.append(
                f"{filepath.name}: Has normalization but missing frozen=True on dataclass. "
                "See: documents/api/optional_value.md#pattern-3"
            )

        if not has_init_false:
            errors.append(
                f"{filepath.name}: Has normalization but missing init=False on dataclass. "
                "See: documents/api/optional_value.md#pattern-3"
            )

    return errors


def check_all_effect_files() -> int:
    """Check all effect files for OptionalValue pattern compliance.

    Returns:
        Exit code (0 if all pass, 1 if errors found)
    """
    effects_dir = Path("effectful/effects")

    if not effects_dir.exists():
        print(f"❌ Error: {effects_dir} directory not found")
        return 1

    all_errors = []
    checked_files = []

    for effect_file in sorted(effects_dir.glob("*.py")):
        if effect_file.name == "__init__.py":
            continue

        checked_files.append(effect_file.name)
        errors = check_effect_file(effect_file)
        all_errors.extend(errors)

    print("==============================================")
    print("  OptionalValue Pattern Checker")
    print("==============================================")
    print()
    print(f"Checked {len(checked_files)} effect file(s):")
    for filename in checked_files:
        print(f"  - {filename}")
    print()

    if all_errors:
        print("❌ PATTERN VIOLATIONS FOUND:")
        print()
        for error in all_errors:
            print(f"  {error}")
        print()
        print("Fix: Follow the canonical normalization pattern:")
        print("  documents/api/optional_value.md#pattern-3")
        return 1

    print("✅ ALL FILES FOLLOW CANONICAL PATTERN")
    print()
    print("Effect files correctly implement OptionalValue normalization:")
    print("  - Local type-specific _normalize_optional_value() functions")
    print("  - Frozen dataclasses with init=False")
    print("  - Custom __init__ using object.__setattr__")
    print()
    print("See: documents/engineering/effect_patterns.md#pattern-6")
    return 0


def main() -> int:
    """Entry point for pattern checker.

    Returns:
        Exit code (0 if pass, 1 if fail)
    """
    return check_all_effect_files()


if __name__ == "__main__":
    sys.exit(main())
