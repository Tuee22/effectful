#!/bin/bash
# OptionalValue Doctrine Validation Script
#
# This script validates that the effectful codebase follows the OptionalValue doctrine:
# 1. No Optional[] usage in domain/effects (use OptionalValue or ADTs)
# 2. Normalization functions present in effects
# 3. No escape hatches (Any, cast, type: ignore)
# 4. ADT usage in domain layer
#
# See: documents/api/optional_value.md for complete OptionalValue patterns

set -e

echo "=============================================="
echo "   OptionalValue Doctrine Validation"
echo "=============================================="
echo ""

# Track overall success
ALL_CHECKS_PASSED=true

# Check 1: No Optional[] imports in domain/effects
echo "Check 1: Verifying no Optional[] usage in domain/effects..."
if grep -r "from typing import.*Optional" effectful/domain effectful/effects 2>/dev/null; then
    echo "❌ FAIL: Found Optional[] imports in domain/effects"
    echo "   Fix: Use OptionalValue[T] or custom ADTs instead"
    echo "   See: documents/api/optional_value.md#decision-tree"
    ALL_CHECKS_PASSED=false
else
    echo "✅ PASS: No Optional[] imports found"
fi
echo ""

# Check 2: Verify OptionalValue normalization pattern
echo "Check 2: Checking for normalization functions in effects..."
NORMALIZATION_COUNT=$(grep -r "_normalize_optional" effectful/effects 2>/dev/null | grep -c "def _normalize" || echo "0")
if [ "$NORMALIZATION_COUNT" -gt 0 ]; then
    echo "✅ PASS: Found $NORMALIZATION_COUNT normalization function(s)"
    echo "   Files with normalization:"
    grep -l "_normalize_optional" effectful/effects/*.py 2>/dev/null | sed 's/^/     - /' || echo "     (none)"
else
    echo "⚠️  WARNING: No normalization functions found"
    echo "   This is OK if no effects have optional parameters"
fi
echo ""

# Check 3: Verify no escape hatches (Any)
echo "Check 3: Checking for 'Any' type usage..."
if grep -r ": Any" effectful/ --include="*.py" 2>/dev/null | grep -v "# poetry.lock" | grep -v "__pycache__"; then
    echo "❌ FAIL: Found 'Any' type usage"
    echo "   Fix: Use explicit types instead of Any"
    echo "   See: documents/engineering/code_quality.md#1-no-escape-hatches-zero-exceptions"
    ALL_CHECKS_PASSED=false
else
    echo "✅ PASS: No 'Any' type usage found"
fi
echo ""

# Check 4: Verify no cast() usage
echo "Check 4: Checking for cast() usage..."
if grep -r "cast(" effectful/ --include="*.py" 2>/dev/null | grep -v "__pycache__"; then
    echo "❌ FAIL: Found cast() usage"
    echo "   Fix: Use type narrowing with isinstance() or pattern matching"
    echo "   See: documents/engineering/code_quality.md#6-type-narrowing-for-union-types"
    ALL_CHECKS_PASSED=false
else
    echo "✅ PASS: No cast() usage found"
fi
echo ""

# Check 5: Verify no type: ignore comments
echo "Check 5: Checking for '# type: ignore' comments..."
if grep -r "# type: ignore" effectful/ --include="*.py" 2>/dev/null | grep -v "__pycache__"; then
    echo "❌ FAIL: Found '# type: ignore' comments"
    echo "   Fix: Remove type: ignore and fix types properly"
    echo "   See: documents/engineering/code_quality.md#1-no-escape-hatches-zero-exceptions"
    ALL_CHECKS_PASSED=false
else
    echo "✅ PASS: No '# type: ignore' comments found"
fi
echo ""

# Check 6: Verify ADT usage in domain
echo "Check 6: Checking for ADT type aliases in domain..."
ADT_COUNT=$(grep -r "^type .* = .*|" effectful/domain --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$ADT_COUNT" -gt 0 ]; then
    echo "✅ PASS: Found $ADT_COUNT ADT type alias(es)"
    echo "   ADTs found:"
    grep -r "^type .* = .*|" effectful/domain --include="*.py" 2>/dev/null | sed 's/^/     - /' || echo "     (none)"
else
    echo "⚠️  WARNING: No ADT type aliases found"
    echo "   This is OK if domain models don't need variant types yet"
fi
echo ""

# Check 7: Verify OptionalValue import structure
echo "Check 7: Verifying OptionalValue import structure..."
OPTIONAL_VALUE_IMPORTS=$(grep -r "from effectful.domain.optional_value import" effectful/ --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$OPTIONAL_VALUE_IMPORTS" -gt 0 ]; then
    echo "✅ PASS: Found $OPTIONAL_VALUE_IMPORTS file(s) importing OptionalValue"
else
    echo "⚠️  INFO: No OptionalValue imports found"
    echo "   This is expected if not using OptionalValue yet"
fi
echo ""

# Summary
echo "=============================================="
echo "   Validation Summary"
echo "=============================================="
if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo "✅ ALL CHECKS PASSED"
    echo ""
    echo "Core library follows OptionalValue doctrine."
    echo "See: documents/api/optional_value.md for patterns"
    exit 0
else
    echo "❌ SOME CHECKS FAILED"
    echo ""
    echo "Please fix the issues above before committing."
    echo "See: documents/engineering/code_quality.md for standards"
    exit 1
fi
