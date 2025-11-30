# Code Quality Standards

> **SSoT** for all code quality enforcement, formatting, and type checking in effectful.

## check-code Command

**Usage**: `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code`

See [Command Reference](command_reference.md) for complete command table.

### Black + MyPy Workflow

Runs Black (formatter) → MyPy (strict type checker) with fail-fast behavior.

**Behavior**:
1. **Black**: Auto-formats Python code (line-length=100)
2. **MyPy**: Strict type checking with 30+ strict settings, disallow_any_explicit=true
3. **Fail-fast**: Exits on first failure

Must meet Universal Success Criteria (exit code 0, Black formatting applied, zero MyPy errors).

## Universal Success Criteria

All code changes must meet these requirements:

- ✅ Exit code 0 (all operations complete successfully)
- ✅ **Zero MyPy errors** (mypy --strict mandatory)
- ✅ Zero stderr output
- ✅ Zero console warnings/errors
- ✅ **Zero skipped tests** (pytest.skip() forbidden)
- ✅ 100% test pass rate
- ✅ **Zero `Any`, `cast()`, or `# type: ignore`** (escape hatches forbidden)
- ✅ **Minimum 45% code coverage** (adapters excluded)
- ✅ **Integration tests cover all features** (conceptual coverage)

**Referenced by**: Testing, Type Safety, Contributing Checklist.

## MyPy Strict Configuration

**pyproject.toml settings** (30+ strict options enabled):

```toml
[tool.mypy]
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_any_explicit = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_calls = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
```

**Critical Setting**: `disallow_any_explicit = true` - Forbids `Any` type in all code.

## Black Configuration

**Line length**: 100 characters (configured in pyproject.toml)

**Auto-formatting**: Black modifies files in-place to enforce consistent style.

**Target version**: Python 3.12+

## Coverage Requirements

**Minimum Coverage**: 45% overall (enforced by pytest-cov)

**Excluded from measurement**:
- `effectful/adapters/` - Real infrastructure implementations
- `effectful/infrastructure/` - Protocol definitions (no logic)
- Test files themselves

**Why 45%**: Balances quality signal vs. diminishing returns. Focus on:
- Core algebraic types (Result, EffectReturn)
- Domain models
- Interpreters
- Program runners
- Effect definitions

**Conceptual coverage**: Every feature must have integration tests, even if line coverage < 100%.

## Pre-commit Checks

Before committing code:

1. **Format**: `poetry run black effectful tests`
2. **Type check**: `poetry run check-code`
3. **Test**: `poetry run test-all` (see [Command Reference](command_reference.md))
4. **Coverage**: `poetry run pytest --cov=effectful --cov-report=term-missing`

All must meet Universal Success Criteria.

## Common Violations

### Type Safety Violations

**❌ WRONG** - Using Any:
```python
def process_data(data: Any) -> Any:  # Forbidden!
    return data
```

**✅ CORRECT** - Explicit types:
```python
def process_data(data: UserData) -> Result[ProcessedData, ProcessingError]:
    return Ok(ProcessedData(...))
```

### Coverage Violations

**❌ WRONG** - No tests for new feature:
```python
# Added new function, no tests = coverage drops below 45%
def calculate_metrics(data: MetricData) -> MetricResult:
    ...
```

**✅ CORRECT** - Tests for all features:
```python
# tests/test_metrics.py
def test_calculate_metrics():
    result = calculate_metrics(MetricData(...))
    assert_ok(result)
```

### Formatting Violations

Black automatically fixes these, but check-code will fail if code isn't formatted:

- Line length > 100 characters
- Inconsistent quote styles
- Missing trailing commas
- Inconsistent indentation

## Exit Codes

**Exit code 0**: All checks passed
**Exit code 1**: Black formatting needed OR MyPy errors found

**Fail-fast behavior**: check-code stops at first failure (Black or MyPy), does not continue.

## Integration with CI

**GitHub Actions** (future):
```yaml
- name: Check code quality
  run: docker compose -f docker/docker-compose.yml exec effectful poetry run check-code

- name: Run tests with coverage
  run: docker compose -f docker/docker-compose.yml exec effectful poetry run pytest --cov=effectful --cov-fail-under=45
```

## See Also

- [Type Safety](type_safety.md) - Eight type safety doctrines
- [Testing](testing.md) - Testing standards and coverage policy
- [Command Reference](command_reference.md) - All Docker commands
- [Development Workflow](development_workflow.md) - Daily development loop

---

**Last Updated**: 2025-11-29
**Referenced by**: CLAUDE.md, development_workflow.md, contributing.md
