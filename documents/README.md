# effectful Documentation

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/readme.md

> **Purpose**: Navigation hub for all effectful documentation (engineering standards, tutorials, and API reference).
> **📖 Authoritative Reference**: [Engineering README](engineering/README.md)

Welcome to the **effectful** documentation!

## Prerequisites

All development happens inside Docker containers. See [Docker Workflow](engineering/docker_workflow.md).

**Multiple stacks**: The base library runs in the `effectful` service defined in `docker/docker-compose.yml`. Demo apps (e.g., HealthHub) ship their own compose files and service names under `demo/**/docker/`; use the correct compose file and service when running Poetry commands.

**CRITICAL**: Poetry is configured to NOT create virtual environments (`poetry.toml`). Do NOT run `poetry install` locally.
See [Command Reference](engineering/command_reference.md#command-table) for all canonical commands.

## Getting Started

New to effectful? Start here:

1. [Quickstart Guide](tutorials/quickstart.md) - Get running in 10 minutes
2. [Effect Types](tutorials/effect_types.md) - Learn about all available effects
3. [ADTs and Result Types](tutorials/adts_and_results.md) - Master type safety

## Documentation Structure

### Engineering Standards (SSoT)

Project engineering practices and standards:

- **[Code Quality](engineering/code_quality.md)** - Type safety + purity doctrines, anti-pattern routing (SSoT)
- **[Architecture](engineering/architecture.md)** - 5-layer architecture, design decisions (SSoT)
- **[Docker Workflow](engineering/docker_workflow.md)** - All development in Docker (SSoT)
- **[Testing](engineering/testing.md)** - Coverage requirements, 22 test anti-patterns (SSoT)
- **[Effect Patterns](engineering/effect_patterns.md)** - Functional composition patterns (SSoT)
- **[Command Reference](engineering/command_reference.md)** - All Docker commands and test execution
- **[Development Workflow](engineering/development_workflow.md)** - Daily development loop
- **[Configuration](engineering/configuration.md)** - Environment variables for all services
- **[Documentation Guidelines](documentation_standards.md)** - SSoT/DRY principles, mermaid best practices (SSoT)

**Observability**:
- **[Observability](engineering/observability.md)** - Metrics philosophy and cardinality management (SSoT)
- **[Monitoring & Alerting](engineering/monitoring_and_alerting.md)** - Naming conventions, label standards, severity levels, and runbook requirements (SSoT)

### Tutorials

Step-by-step guides for learning effectful:

**Getting Started**:
- **[quickstart.md](tutorials/quickstart.md)** - Your first effect program
- **[effect_types.md](tutorials/effect_types.md)** - WebSocket, Database, Cache effects
- **[adts_and_results.md](tutorials/adts_and_results.md)** - Type-safe error handling

**Advanced Topics**:
- **[testing_guide.md](tutorials/testing_guide.md)** - Comprehensive testing strategies
- **[production_deployment.md](tutorials/production_deployment.md)** - Deploy with Docker, PostgreSQL, Redis
- **[advanced_composition.md](tutorials/advanced_composition.md)** - Build complex workflows
- **[migration_guide.md](tutorials/migration_guide.md)** - Migrate from imperative code

**Effect-Specific Guides**:
- **[messaging_effects.md](tutorials/messaging_effects.md)** - Pub/sub with Apache Pulsar
- **[storage_effects.md](tutorials/storage_effects.md)** - S3-compatible object storage
- **[auth_effects.md](tutorials/auth_effects.md)** - JWT authentication and passwords

**Observability**:
- **[metrics_quickstart.md](tutorials/metrics_quickstart.md)** - Get started with metrics in 15 minutes
- **[metric_types_guide.md](tutorials/metric_types_guide.md)** - Choose the right metric type
- **[prometheus_setup.md](tutorials/prometheus_setup.md)** - Docker integration with Prometheus/Grafana
- **[alert_rules.md](tutorials/alert_rules.md)** - Write actionable Prometheus alerts
- **[grafana_dashboards.md](tutorials/grafana_dashboards.md)** - Build beautiful dashboards

### API Reference

Complete API documentation:

- **[API Overview](api/README.md)** - Quick reference and navigation
- **[effects.md](api/effects.md)** - WebSocket, Database, Cache effects
- **[auth.md](api/auth.md)** - JWT authentication effects
- **[messaging.md](api/messaging.md)** - Pub/sub messaging effects
- **[storage.md](api/storage.md)** - S3 object storage effects
- **[metrics.md](api/metrics.md)** - Prometheus metrics effects (Counter, Gauge, Histogram, Summary)
- **[result.md](api/result.md)** - Result type and utilities
- **[interpreters.md](api/interpreters.md)** - Interpreter interfaces and error types
- **[programs.md](api/programs.md)** - Program execution and composition

## Core Concepts (Pointers Only)

- **Architecture (SSoT)**: See [engineering/architecture.md](engineering/architecture.md) for layers, data flow, and effect hierarchy.
- **Type Safety + Purity (SSoT)**: See [engineering/code_quality.md](engineering/code_quality.md) for Result/ADT patterns.
- **Testing (SSoT)**: See [engineering/testing.md](engineering/testing.md) for policy, fixtures, and anti-patterns.
- **Interpreter Responsibilities**: See [api/interpreters.md](api/interpreters.md) for execution contracts.
- **Examples**: Browse [examples/](../examples/) for runnable programs; each tutorial links to its companion code.

## Quick Links

- [Engineering Standards](engineering/README.md)
- [Docker Workflow](engineering/docker_workflow.md)
- [Architecture](engineering/architecture.md)
- [Testing](engineering/testing.md)
- [Code Quality](engineering/code_quality.md)
- [Examples](../examples/)

## Support

- **Questions?** Open a discussion in the project tracker.
- **Bug reports?** File an issue in the project tracker.
- **Contributing?** See [Contributing Guide](contributing.md) and [Engineering Standards](engineering/README.md)

## Cross-References

- [Engineering README](engineering/README.md) - Master index of standards
- [Code Quality](engineering/code_quality.md) - Type safety and purity
- [Architecture](engineering/architecture.md) - 5-layer design
- [Testing](engineering/testing.md) - Test standards and anti-patterns
- [Docker Workflow](engineering/docker_workflow.md) - Docker-only development
- [Command Reference](engineering/command_reference.md) - All Docker commands
- [Contributing Guide](contributing.md) - How to contribute
- [Documentation Standards](documentation_standards.md) - SSoT and DRY principles
