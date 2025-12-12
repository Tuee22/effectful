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
| [Testing Architecture](documents/engineering/testing_architecture.md) | Test organization and Test Terseness Doctrine |
| [Docker Workflow](documents/engineering/docker_workflow.md) | All development in Docker |
| [Command Reference](documents/engineering/command_reference.md) | Docker commands and test execution |
| [Monitoring & Alerting](documents/engineering/monitoring_and_alerting.md) | Metric standards + alert policy |
| [Development Workflow](documents/engineering/development_workflow.md) | Daily development loop |
| [Effect Patterns](documents/engineering/effect_patterns.md) | Real-world effect program patterns |

## Quick Reference

### Start Development

> **📖 SSoT**: [Command Reference](documents/engineering/command_reference.md)

All Docker commands follow the pattern `docker compose -f docker/docker-compose.yml exec effectful poetry run <command>`. For the complete command table including test execution, code quality checks, and service management, see [Command Reference](documents/engineering/command_reference.md).

### Universal Success Criteria

> **📖 SSoT**: [Code Quality - Universal Success Criteria](documents/engineering/code_quality.md#universal-success-criteria)

All code changes must achieve exit code 0 with zero MyPy errors, zero skipped tests, and zero escape hatches (Any/cast/type:ignore). See [Code Quality](documents/engineering/code_quality.md#universal-success-criteria) for the complete criteria list.

## Claude Code-Specific Patterns

### Test Output Management Pattern

> **📖 SSoT**: [Command Reference - Test Output Management](documents/engineering/command_reference.md#test-output-management)

**CRITICAL**: Bash tool truncates at 30,000 characters. Always redirect test output to `/tmp/test-output.txt 2>&1`, then read the complete file using the Read tool to see ALL failures. See [Command Reference](documents/engineering/command_reference.md#test-output-management) for complete pattern and forbidden practices.

### Git Workflow Policy

> **📖 SSoT**: [Development Workflow - Git Workflow Policy](documents/engineering/development_workflow.md#git-workflow-policy)

**Critical Rule**: Claude Code is NOT authorized to commit or push changes. Make all code changes and run tests, but leave ALL changes as uncommitted working directory changes for user review. See [Development Workflow](documents/engineering/development_workflow.md#git-workflow-policy) for complete policy and forbidden operations.

## Contributing

See [documents/contributing.md](documents/contributing.md) for complete contributing guidelines.

**Quick checklist**:
- [ ] Code quality: `poetry run check-code` exits 0
- [ ] Docs follow [documentation standards](documents/documentation_standards.md) and open items in [MIGRATION_PLAN.md](documents/MIGRATION_PLAN.md)
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
- [Testing Architecture](documents/engineering/testing_architecture.md) - Test organization and Test Terseness Doctrine
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
- [Messaging Workflow](examples/06_messaging_workflow.py)

### Demo Applications

- [HealthHub](demo/healthhub/) - Healthcare management portal demonstrating real-world effectful usage

---

**Status**: Library foundation complete | Docker infrastructure ready | 329 tests passing
**Philosophy**: If the type checker passes, the program is correct. Make the type system work for you, not against you.
**Architecture**: Pure functional effect system with 5-layer architecture (Application → Runner → Composite → Interpreters → Infrastructure)
