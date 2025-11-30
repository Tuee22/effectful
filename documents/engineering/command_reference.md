# Command Reference

> **SSoT** for all Docker commands, test execution patterns, and output management in effectful.

## Docker Command Prefix

**All commands run inside Docker**: `docker compose -f docker/docker-compose.yml exec effectful poetry run <command>`

**Important**: Poetry is configured to NOT create virtual environments via `poetry.toml` (`create = false`). Running `poetry install` outside the container will fail. All development happens inside Docker.

See [Docker Workflow](docker_workflow.md) for complete policy.

## Command Table

| Task | Command |
|------|---------|
| Start services | `docker compose -f docker/docker-compose.yml up -d` |
| View logs | `docker compose -f docker/docker-compose.yml logs -f effectful` |
| Check code quality | `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code` |
| Test all | `docker compose -f docker/docker-compose.yml exec effectful poetry run test-all` |
| Test unit | `docker compose -f docker/docker-compose.yml exec effectful poetry run test-unit` |
| Test integration | `docker compose -f docker/docker-compose.yml exec effectful poetry run test-integration` |
| Python shell | `docker compose -f docker/docker-compose.yml exec effectful poetry run python` |
| Build package | `docker compose -f docker/docker-compose.yml exec effectful poetry build` |

## Poetry Entrypoints

**Defined in pyproject.toml `[tool.poetry.scripts]`**:

- `check-code` - Black formatter + MyPy strict type checking
- `test-unit` - Unit tests only (pytest-mock, no I/O)
- `test-integration` - Integration tests (real PostgreSQL, Redis, MinIO, Pulsar)
- `test-all` - Complete test suite

**Test Isolation**: Each test is responsible for creating reproducible starting conditions (e.g., TRUNCATE + seed in fixtures).

## Test Statistics

| Category | Test Count | Duration | Infrastructure |
|----------|-----------|----------|----------------|
| Unit Tests | 200+ tests | ~0.5s | pytest-mock only |
| Integration | 27+ tests | ~1.1s | Real PostgreSQL/Redis/MinIO |
| Full suite | **329 tests** | **~1.6s** | Mixed |
| Coverage | 69% overall | - | Adapters/infrastructure excluded from measurement |

**Test Organization**:
- `tests/test_algebraic/` - Result, EffectReturn type tests
- `tests/test_domain/` - Domain model tests
- `tests/test_effects/` - Effect definition tests
- `tests/test_interpreters/` - Individual interpreter tests (pytest-mock)
- `tests/test_programs/` - Program runner tests
- `tests/test_integration/` - Multi-effect workflows (real infrastructure)

## Test Output Management

**CRITICAL - Output Truncation**: Bash tool truncates at 30,000 characters. Large test suites can exceed this.

**REQUIRED Pattern**:

```bash
# Step 1: Run tests with output redirection
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest > /tmp/test-output.txt 2>&1

# Step 2: Read complete output using Read tool on /tmp/test-output.txt

# Step 3: Analyze ALL failures, not just visible ones
```

**Why This Matters**: Truncated output hides failures, making diagnosis impossible. File-based approach ensures complete output is always available. Read tool has no size limits.

**For all test categories**: Use pattern above with `pytest`, `test-integration`, or specific test paths.

### Forbidden Practices

- ❌ `Bash(command="...pytest...", timeout=60000)` - Kills tests mid-run, truncates output
- ❌ `Bash(command="...pytest...", run_in_background=True)` - Loses real-time failure visibility
- ❌ Reading partial output with `head -n 100` or similar truncation
- ❌ Checking test status before completion (polling BashOutput prematurely)
- ❌ Running tests via Bash tool and analyzing truncated stdout
- ❌ Drawing conclusions without seeing complete output
- ❌ Creating fix plans based on partial failure information

### Required Practices

- ✅ Always redirect to /tmp/, then read complete output
- ✅ Verify you have seen ALL test results before creating fix plans
- ✅ If output is truncated, STOP and re-run with file redirection
- ✅ Let tests complete naturally (integration tests may take 1-2 seconds - patience required!)
- ✅ Review ALL stdout/stderr output before drawing conclusions

## See Also

- [Docker Workflow](docker_workflow.md) - Complete Docker development policy
- [Testing](testing.md) - Testing standards and anti-patterns
- [Code Quality](type-safety-enforcement.md) - check-code workflow and MyPy strict enforcement

---

**Last Updated**: 2025-11-29
**Referenced by**: CLAUDE.md, development_workflow.md
