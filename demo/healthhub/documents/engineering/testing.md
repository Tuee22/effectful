# Testing (HealthHub Deltas)

> Extends base [Testing](../../../../documents/engineering/testing.md). Base rules apply unless explicitly overridden here.

## Scope
- HealthHub-specific test structure, commands, and PHI safety rules layered on the base four-layer testing architecture.
- Applies to unit, integration, and E2E suites inside `tests/pytest/`.

## Base Inheritance (retain)
- Follow the four-layer testing model from base testing SSoT.
- Use `mocker.AsyncMock(spec=Protocol)` for infra fakes; avoid loose mocks.
- Prefer generator stepping for programs; interpreters tested with real infra in integration suite.

## HealthHub-specific additions
- **Test layout**: unit tests in `tests/pytest/backend/`; E2E flows in `tests/pytest/e2e/`; integration tests hit real Postgres/Redis/MinIO/Pulsar via Docker.
- **Commands**: run via demo service:  
  `docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest`
- **Generator stepping**: assert effect ordering and ADT narrowing for appointments, prescriptions, lab results.
- **PHI-safe fixtures**: scrub PHI from logs/assertions; seed data uses anonymized patients/doctors; never hardcode identifiers.
- **Notification flows**: assert business logic does not block on SMS/email/WebSocket; verify audit and metrics events on failure.
- **Audit coverage**: tests must assert audit effects for PHI access/mutation.
- **Output capture**: capture full E2E logs for WebSocket and notification flows to files (for triage and audit).

## Checklists
- [ ] Each test declares suite type (unit/integration/e2e) in docstring/markers.
- [ ] PHI-free fixtures; anonymized data only.
- [ ] Generators stepped with `send()` and `next()` assertions; exhaustiveness checked.
- [ ] Notification failures tested as non-blocking with metrics/audit assertions.
- [ ] Integration tests exercise real Postgres/Redis/MinIO/Pulsar via Docker.
- [ ] Command run via `healthhub` service to mirror CI.

## Anti-patterns (reject)
- Using production-like PHI in fixtures or snapshots.
- Allowing notification errors to raise in programs.
- Mocking interpreters in integration tests (they must hit real infra).
- Skipping generator stepping in unit tests.
- Relying on global state in tests instead of explicit fixtures.

## Suite mapping
- **Unit** (`tests/pytest/backend/unit_*`): pure programs, domain ADTs, effect construction; no I/O; generator stepping required.
- **Integration** (`tests/pytest/backend/integration_*`): interpreters + real Postgres/Redis/MinIO/Pulsar via Docker; no mocks for infra.
- **E2E** (`tests/pytest/e2e/*`): FastAPI entrypoints + background workers; includes WebSocket and notification paths.

## Fixtures (PHI-safe)
- Use anonymized patients/doctors (`Patient Alpha`, `Doctor Bravo`).
- Randomized IDs should be opaque (`lab_result_id="LR-001"`).
- No real addresses, phone numbers, or MRNs; replace with placeholders.
- Prefer factory helpers that ensure domain validity and frozen dataclasses.

## Coverage expectations
- Unit tests: effect order, ADT exhaustiveness, error ADTs surfaced.
- Integration tests: interpreter emits audit + metric side effects; verifies retries and idempotency.
- E2E tests: notification failures are non-blocking; audit events recorded; metrics emitted.

## Failure triage
- Capture failing test output to artifacts; include generator steps and effect traces.
- For notification failures, include channel, retry count, and audit correlation ID (opaque).
- For audit gaps, block release until audit events are emitted and verified.
- For infra flakiness, capture Docker container logs and interpreter error ADTs.

## Data seeding
- Integration/E2E tests seed Postgres/Redis/MinIO/Pulsar via fixtures; truncate between tests to avoid PHI leakage.
- Seed data must live in repo fixtures; no ad-hoc psql/redis commands with PHI.
- Prefer deterministic seeds for reproducibility; avoid random UUIDs unless required for idempotency tests.

## Command matrix
- Unit: `docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/backend/unit_*`
- Integration: `docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/backend/integration_*`
- E2E: `docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e`

## Reporting
- Attach E2E output artifacts to PRs when failures occur (redacted).
- Summarize audit coverage in PR description for PHI-touching changes.
- Note any skipped tests with rationale and target removal date.
- Capture container logs for Pulsar/MinIO/Redis/Postgres when integration tests fail.

## Tooling
- Use `pytest -q --maxfail=1` for quick local loops; reserve full suite for pre-merge.
- Run `check-code` first to catch doc link and type issues before long test runs.
- Use `pytest --lf` to iterate on failing tests while keeping generator stepping assertions intact.
- Capture coverage for effect programs and interpreters; treat coverage drops as regressions.
- Keep VSCode extensions aligned with base recommendations for Mermaid preview and Python linting.
- Prefer `rg` for searching fixtures and test data to avoid missing PHI leaks.

## Procedures
1. Choose the correct suite: unit for pure logic, integration for interpreter + infra, e2e for cross-service flows.
2. Build fixtures from anonymized data; avoid IDs/names in assertions.
3. Step generators to validate effect order and ADT handling.
4. Assert audit effects and PHI-free metrics/logs for PHI paths.
5. Run via `healthhub` service command; capture E2E output to artifact files.
6. Document any deviations from base standards in test docstrings and ADRs.

## See also
- Base standards: [Testing](../../../../documents/engineering/testing.md), [Code Quality](../../../../documents/engineering/code_quality.md)
- Related overlays: [Effect Patterns](effect_patterns.md), [Monitoring & Alerting](monitoring_and_alerting.md), [Documentation Standards](documentation_standards.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: code_quality.md, effect_patterns.md, monitoring_and_alerting.md, documentation_standards.md
