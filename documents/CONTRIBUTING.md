# Contributing to Effectful

**Status**: Reference only  
**Supersedes**: none  
**Referenced by**: README.md

> **Purpose**: Contributor guide for Effectful, including prerequisites and core development commands.
> **📖 Authoritative Reference**: [Repository README](../README.md)

Welcome to the effectful project! We're excited to have you contribute.

## Prerequisites

All development happens inside Docker containers. See [Docker Workflow](engineering/docker_workflow.md) for complete policy.

**CRITICAL**: Poetry is configured to NOT create virtual environments (`poetry.toml`). Do NOT run `poetry install` locally.

All development commands follow the pattern `docker compose -f docker/docker-compose.yml exec effectful poetry run <command>`.

**See**: [Command Reference](engineering/command_reference.md) for the complete command table with all Docker commands.

## Quick Links

**Before contributing, read these engineering standards**:

| Standard | Purpose |
|----------|---------|
| [Engineering Standards](engineering/README.md) | Master index of all standards |
| [Architecture](engineering/architecture.md) | 5-layer architecture design |
| [Code Quality](engineering/code_quality.md) | Type safety + purity doctrines and anti-pattern routing |
| [Testing](engineering/testing.md) | Testing standards and 22 anti-patterns |
| [Docker Workflow](engineering/docker_workflow.md) | All development in Docker |

## Contributing Checklist

All contributions must meet the **Universal Success Criteria** including: zero MyPy errors (strict mode), zero stderr output, 100% test pass rate, and no escape hatches (Any/cast/type:ignore).

**See**: [Code Quality - Universal Success Criteria](engineering/code_quality.md#universal-success-criteria) for the complete list.

## Validation Checks

Before submitting code, run these validation checks:

### 1. Core Type Safety and Formatting

```bash
# Black formatting + MyPy strict + doc links
docker compose -f docker/docker-compose.yml exec effectful poetry run check-code
```

**Must pass**: Zero errors, exit code 0

### 2. OptionalValue Doctrine Validation

```bash
# Full OptionalValue doctrine validation
bash scripts/validate_optional_value_doctrine.sh

# Pattern checker (if modifying effects)
python3 scripts/check_optional_value_pattern.py
```

**Checks**:
- No Optional[] in domain/effects (use OptionalValue or ADTs)
- Normalization functions present in effects
- No escape hatches (Any, cast, type: ignore)
- Canonical pattern followed (frozen=True, init=False, object.__setattr__)

**See**: [Code Quality: OptionalValue Enforcement](engineering/code_quality.md#optionalvalue-doctrine-enforcement)

### 3. Pre-Commit Hooks (Recommended)

```bash
# One-time setup
pre-commit install

# Manual run (tests all files)
pre-commit run --all-files
```

**Prevents**: Optional[] commits, pattern violations, formatting issues

### 4. Test Suites

```bash
# Unit tests only (fast)
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest tests/unit

# Full test suite (unit + integration)
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest
```

**Must pass**: 100% pass rate, zero skipped tests

## How to Contribute

1. Fork the repository and create a branch for your change
2. Ensure Docker services are running (`docker compose -f docker/docker-compose.yml up -d`)
3. **Run validation checks** (see section above)
4. Update documentation and links if you add or move modules
5. Run pre-commit hooks: `pre-commit run --all-files`
6. Open a PR with:
   - Concise description of changes
   - List of commands you ran
   - Confirmation all validation checks passed

## Code of Conduct

Be respectful and inclusive. Follow the community guidelines in the project tracker.

## Cross-References

- [Engineering Standards](engineering/README.md) - Master index
- [Code Quality](engineering/code_quality.md#universal-success-criteria) - Success criteria
- [Testing](engineering/testing.md) - Test standards and anti-patterns
- [Docker Workflow](engineering/docker_workflow.md) - Docker-only development contract
- [Command Reference](engineering/command_reference.md) - Complete command table
- [Architecture](engineering/architecture.md) - 5-layer design
