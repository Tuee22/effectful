# Claude Code Patterns for Effectful

## Project Overview

**Effectful** is a pure functional effect system library for Python that brings algebraic data types, explicit error handling, and composable programs to async Python applications.

**Core Philosophy**: Make invalid states unrepresentable through the type system.

**Architecture**: Pure Python library (no web framework) with Docker-managed development environment for integration testing against real infrastructure (PostgreSQL, Redis, MinIO S3, Apache Pulsar).

## Engineering Standards

**All engineering practices documented in [documents/engineering/](documents/engineering/README.md)**.

Quick links to key standards:

| Standard | Purpose |
|----------|---------|
| [Engineering Standards](documents/engineering/README.md) | Master index of all standards |
| [Architecture](documents/engineering/architecture.md) | 5-layer architecture design |
| [Code Quality](documents/engineering/code_quality.md) | Type safety + purity doctrines and anti-pattern routing |
| [Testing](documents/engineering/testing.md) | 22 test anti-patterns |
| [Docker Workflow](documents/engineering/docker_workflow.md) | All development in Docker |
| [Command Reference](documents/engineering/command_reference.md) | Docker commands and test execution |
| [Monitoring & Alerting](documents/engineering/monitoring_and_alerting.md) | Metric standards + alert policy |
| [Development Workflow](documents/engineering/development_workflow.md) | Daily development loop |
| [Effect Patterns](documents/engineering/effect_patterns.md) | Real-world effect program patterns |

## Quick Reference

### Start Development

> **📖 SSoT**: [Command Reference](documents/engineering/command_reference.md)
>
> _This section duplicates commands for AI agent context. Humans should consult the SSoT._

```bash
# Start services
docker compose -f docker/docker-compose.yml up -d

# Run tests
docker compose -f docker/docker-compose.yml exec effectful poetry run test-all

# Check code quality
docker compose -f docker/docker-compose.yml exec effectful poetry run check-code
```

**See**: [Command Reference](documents/engineering/command_reference.md) for complete command table.

### Universal Success Criteria

> **📖 SSoT**: [Code Quality - Universal Success Criteria](documents/engineering/code_quality.md#universal-success-criteria)
>
> _This section duplicates criteria for AI agent context. Humans should consult the SSoT._

All code changes must meet these requirements:

- ✅ Exit code 0 (all operations complete successfully)
- ✅ **Zero MyPy errors** (mypy --strict mandatory)
- ✅ Zero stderr output
- ✅ Zero console warnings/errors
- ✅ **Zero skipped tests** (pytest.skip() forbidden)
- ✅ 100% test pass rate
- ✅ **Zero `Any`, `cast()`, or `# type: ignore`** (escape hatches forbidden)
- ✅ **Integration tests cover all features** (conceptual coverage)

**See**: [Code Quality](documents/engineering/code_quality.md) for complete standards.

## Claude Code-Specific Patterns

### Test Output Management Pattern

> **📖 SSoT**: [Command Reference - Test Output Management](documents/engineering/command_reference.md#test-output-management)
>
> _This section duplicates the test pattern for AI agent context. Humans should consult the SSoT._

**CRITICAL - Output Truncation**: Bash tool truncates at 30,000 characters. Large test suites can exceed this.

**REQUIRED Pattern for Claude Code**:

```bash
# Step 1: Run tests with output redirection
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest > /tmp/test-output.txt 2>&1

# Step 2: Read complete output using Read tool on /tmp/test-output.txt

# Step 3: Analyze ALL failures, not just visible ones
```

**Why This Matters**: Truncated output hides failures, making diagnosis impossible. File-based approach ensures complete output is always available. Read tool has no size limits.

**Forbidden Practices**:
- ❌ `Bash(command="...pytest...", timeout=60000)` - Kills tests mid-run, truncates output
- ❌ `Bash(command="...pytest...", run_in_background=True)` - Loses real-time failure visibility
- ❌ Reading partial output with `head -n 100` or similar truncation
- ❌ Drawing conclusions without seeing complete output

**Required Practices**:
- ✅ Always redirect to /tmp/, then read complete output
- ✅ Verify you have seen ALL test results before creating fix plans
- ✅ Let tests complete naturally (integration tests may take 1-2 seconds)

**See**: [Command Reference](documents/engineering/command_reference.md) for complete test execution patterns.

### Git Workflow Policy

> **📖 SSoT**: [Development Workflow - Git Workflow Policy](documents/engineering/development_workflow.md#git-workflow-policy)
>
> _This section duplicates the Git policy for AI agent context. Humans should consult the SSoT._

**Critical Rule**: Claude Code is NOT authorized to commit or push changes.

**Forbidden Git Operations**:
- ❌ **NEVER** run `git commit` (including `--amend`, `--no-verify`, etc.)
- ❌ **NEVER** run `git push` (including `--force`, `--force-with-lease`, etc.)
- ❌ **NEVER** run `git add` followed by commit operations
- ❌ **NEVER** create commits under any circumstances

**Required Workflow**:
- ✅ Make all code changes as requested
- ✅ Run tests and validation
- ✅ Leave ALL changes as **uncommitted** working directory changes
- ✅ User reviews changes using `git status` and `git diff`
- ✅ User manually commits and pushes when satisfied

**Rationale**: All changes must be human-reviewed before entering version control.

**See**: [Development Workflow](documents/engineering/development_workflow.md) for complete daily workflow.

## Contributing

See [documents/contributing.md](documents/contributing.md) for complete contributing guidelines.

**Quick checklist**:
- [ ] Code quality: `poetry run check-code` exits 0
- [ ] Tests for all features (unit + integration)
- [ ] No forbidden constructs (Any/cast/type:ignore)
- [ ] No anti-patterns (see [Code Quality](documents/engineering/code_quality.md#anti-pattern-index-routing-to-canonical-fixes))
- [ ] All dataclasses frozen (`frozen=True`)
- [ ] ADTs used instead of Optional for domain logic
- [ ] Result type used for all fallible operations
- [ ] Exhaustive pattern matching (all cases handled)
- [ ] Changes left uncommitted

## References

### Engineering Standards

**Primary reference**: [documents/engineering/README.md](documents/engineering/README.md) - Complete master index

**Core standards**:
- [Architecture](documents/engineering/architecture.md) - 5-layer design
- [Code Quality](documents/engineering/code_quality.md) - Type safety + purity doctrines
- [Testing](documents/engineering/testing.md) - 22 anti-patterns
- [Docker Workflow](documents/engineering/docker_workflow.md) - All development in Docker

### Documentation

- [Documentation Hub](documents/readme.md) - Complete documentation index
- [Tutorials](documents/tutorials/) - Step-by-step guides (15 tutorials)
- [API Reference](documents/api/) - Complete API documentation (9 references)
- [Contributing Guide](documents/contributing.md) - How to contribute

### Examples

- [Hello World](examples/01_hello_world.py)
- [User Greeting](examples/02_user_greeting.py)
- [Caching Workflow](examples/03_caching_workflow.py)
- [Error Handling](examples/04_error_handling.py)
- [Messaging Workflow](examples/05_messaging_workflow.py)

### Demo Applications

- [HealthHub](demo/healthhub/) - Healthcare management portal demonstrating real-world effectful usage

---

**Status**: Library foundation complete | Docker infrastructure ready | 329 tests passing
**Philosophy**: If the type checker passes, the program is correct. Make the type system work for you, not against you.
**Architecture**: Pure functional effect system with 5-layer architecture (Application → Runner → Composite → Interpreters → Infrastructure)
