# Effectful Engineering Standards

**Status**: Reference only\
**Supersedes**: none\
**Referenced by**: documents/readme.md, CLAUDE.md, contributing.md

> **Purpose**: Navigation hub for engineering practices, coding standards, and development workflows.
> **📖 Authoritative Reference**: [Documentation Standards](../documentation_standards.md)

The **engineering/** directory contains **effectful-specific engineering standards** for building pure functional effect programs in Python. These documents define **HOW to implement** features following type safety, purity, and testing doctrines.

## SSoT Link Map

```mermaid
flowchart TB
  Hub[Engineering Hub SSoT]
  Arch[Architecture SSoT]
  CodeQuality[Code Quality SSoT]
  Testing[Testing SSoT]
  TestingArch[Testing Architecture SSoT]
  Docker[Docker Workflow SSoT]
  Docs[Documentation Standards SSoT]
  Observability[Observability SSoT]
  MonAlert[Monitoring & Alerting SSoT]

  Hub --> Arch
  Hub --> CodeQuality
  Hub --> Testing
  Hub --> TestingArch
  Hub --> Docker
  Hub --> Docs
  Hub --> Observability
  Hub --> MonAlert
  Testing --> TestingArch
  Observability --> Arch
  CommandRef[Command Reference]
  Docker --> CommandRef
```

| What do you need?                 | SSoT Document                                             |
| --------------------------------- | --------------------------------------------------------- |
| Understand system design          | [Architecture](architecture.md)                           |
| Model authentication flows        | [Authentication](authentication.md)                       |
| Write type-safe, pure code        | [Code Quality](code_quality.md)                           |
| Test programs correctly           | [Testing](testing.md)                                     |
| Organize test suites and fixtures | [Testing Architecture](testing_architecture.md)           |
| Set up development environment    | [Docker Workflow](docker_workflow.md)                     |
| Run quality checks                | [Code Quality](code_quality.md#detection-and-enforcement) |
| Add metrics/observability         | [Observability](observability.md)                         |
| Monitoring + alerting policy      | [Monitoring & Alerting](monitoring_and_alerting.md)       |
| Write documentation               | [Documentation Standards](../documentation_standards.md)  |

## Core Standards

**[Architecture](architecture.md)** (614 lines)

- 5-layer architecture (Application → Runner → Composite → Interpreters → Infrastructure)
- Separation of concerns
- Effect system design decisions
- Why pure functional programming for Python

**[Code Quality](code_quality.md)** (Type safety + purity, consolidated)

- Eight type safety doctrines (zero escape hatches, ADTs over Optional, Result for errors, immutable/frozen dataclasses)
- Six purity doctrines (effects as data, yield-don't-call, exhaustive matches)
- Generator rules and anti-pattern routing
- Detection + remediation workflow (check-code, MyPy strict, link verification)

**[Testing](testing.md)** (3,761 lines)

- Test execution and service-specific patterns
- 22 test anti-patterns with examples
- Generator testing patterns
- Zero skipped tests policy

**[Testing Architecture](testing_architecture.md)** (~900 lines)

- Test suite boundaries (Unit/Integration/E2E)
- Fixture architecture and cleanup patterns
- Four-layer testing architecture
- DRY doctrine framework (5 doctrines)

**[Docker Workflow](docker_workflow.md)** (496 lines)

- Docker-only development policy
- Container architecture
- Named volumes vs bind mounts
- Forbidden local commands
- Why Docker for all operations

## Development Guides

**[Documentation Guidelines](../documentation_standards.md)** (500+ lines)

- SSoT (Single Source of Truth) enforcement
- DRY (Don't Repeat Yourself) principles
- Mermaid diagram best practices (GitHub + VSCode compatibility)
- Cross-reference management
- Document templates (engineering, tutorial, API)
- Writing style guidelines

**[Build Artifact Management](build_artifact_management.md)** (new)

- SSoT for what is versioned vs regenerated
- Treats lockfiles (`poetry.lock`, `package-lock.json`) as build artifacts (not versioned)
- Artifacts remain inside containers under `/opt/**`; never copied back to host/images

**[Command Reference](command_reference.md)** (157 lines)

- All Docker compose commands
- Test execution patterns
- Test statistics (current counts from `rg "def test_" tests`)
- Output capture techniques

**[Code Quality](code_quality.md)** (combined)

- check-code workflow (Black → MyPy → doc link verification)
- Universal success criteria
- Purity + type safety doctrines and generators
- Anti-pattern routing and remediation

**[Development Workflow](development_workflow.md)** (271 lines)

- Daily development loop
- Adding new effects (9-step procedure)
- Adding new domain models (5-step procedure)
- Database management
- Integration test setup

**[Configuration](configuration.md)** (183 lines)

- Environment variables for all services
- PostgreSQL configuration
- Redis configuration
- MinIO S3 configuration
- Apache Pulsar configuration

**[Effect Patterns](effect_patterns.md)** (373 lines)

- Generator-based DSL pattern
- Fail-fast error propagation
- Composing programs with yield from
- Recording metrics without failing on errors
- Real-world code examples

## Observability Standards

**[Observability](observability.md)** (710 lines)

- Metrics philosophy (dual-layer architecture)
- Recording vs alerting separation
- Cardinality management
- What to measure and why

**[Monitoring & Alerting](monitoring_and_alerting.md)** (combined)

- Metric naming conventions, label standards, default framework metrics
- Cardinality rules and registry pattern
- Alert severity levels, runbook requirements, routing patterns
- Alert/PromQL testing expectations

## Relationship to Other Documentation

### Engineering → Tutorials

- **Engineering** defines standards and patterns (HOW)
- **Tutorials** teach how to apply them step-by-step (LEARN)
- Example: [Code Quality](code_quality.md) (standard) → [tutorials/adts_and_results.md](../tutorials/adts_and_results.md) (tutorial)

### Engineering → API

- **Engineering** explains architectural decisions (WHY)
- **API** documents specific functions and types (WHAT)
- Example: [Architecture](architecture.md) (design) → [api/programs.md](../api/programs.md) (reference)

### Engineering → Contributing

- **Engineering** defines what is required
- **[Contributing](../contributing.md)** explains the contribution process
- Both must be satisfied for pull requests

## Philosophy

> **Make invalid states unrepresentable through the type system.**

All engineering decisions flow from this principle. Every standard, pattern, and anti-pattern serves to eliminate entire classes of bugs at compile time rather than runtime.

### Core Principles

1. **Type Safety First**: If it type-checks with MyPy strict, it's likely correct
1. **Purity by Default**: Effects as data, not execution
1. **Test to Find Problems**: Tests exist to catch bugs, not provide false confidence
1. **DRY Documentation**: Link liberally, duplicate never
1. **SSoT Enforcement**: Each piece of knowledge lives in exactly one place

## Document Status

**Total**: 15 engineering documents (8 core + 7 guides)
**Lines of Code**: ~7,600 lines of engineering documentation

All engineering documents marked with "**SSoT**" are authoritative. When conflicts arise between documents, SSoT documents take precedence.

## Meta-Documentation

**How to update these standards:**

1. Read [Documentation Guidelines](../documentation_standards.md) for standards and open items in [Documentation Migration Plan](../MIGRATION_PLAN.md)
1. Make changes to appropriate SSoT document
1. Confirm header metadata (Status/Supersedes/Referenced by/Purpose) is correct
1. Update "Referenced by" list if adding new cross-references
1. Run full gate: `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code` (black → ruff → mypy → mdformat/pymarkdown/codespell → custom doc checks → functional catalogue)
1. Create pull request (see [Contributing](../contributing.md))

**Naming convention**: All files lowercase with underscores, descriptive names (e.g., `code_quality.md` not `types.md`)

## See Also

- **[Documentation Hub](../readme.md)** - Complete documentation index (tutorials + API + engineering)
- **[Contributing Guide](../contributing.md)** - How to contribute to effectful
- **[Main README](../../README.md)** - Project overview and quickstart

## Cross-References

- [Code Quality](code_quality.md) - Type safety and purity doctrines
- [Architecture](architecture.md) - 5-layer architecture design
- [Testing](testing.md) - Test standards and anti-patterns
- [Testing Architecture](testing_architecture.md) - Test organization and DRY doctrine
- [Docker Workflow](docker_workflow.md) - Docker-only development contract
- [Command Reference](command_reference.md) - All Docker commands
- [Development Workflow](development_workflow.md) - Daily development loop
- [Effect Patterns](effect_patterns.md) - Functional composition patterns
- [Documentation Standards](../documentation_standards.md) - SSoT and DRY principles
- [Contributing Guide](../contributing.md) - How to contribute
