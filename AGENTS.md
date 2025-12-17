# Repository Guidelines

## Project Structure & Module Organization

- Core package lives in `effectful/`: `effects` (dataclasses describing side effects), `interpreters` (runtime handlers), `adapters` (infra integrations), `domain` (frozen ADTs), `programs` (generators), and `observability`.
- Tests in `tests/`: `unit/` and top-level `tests/test_*` cover pure logic; `tests/integration/` hits real PostgreSQL/Redis/MinIO/Pulsar via Docker; `tests/e2e/` exercises chat workflow.
- Docs in `documents/` (engineering standards, API, tutorials); runnable examples in `examples/`.
- Supporting assets: `docker/` for local stack, `effectful_tools/` for linters/scripts, `stubs/` for third-party typing. `demo/healthhub/` is an example app; keep changes scoped unless working on the demo.

## Build, Test, and Development Commands

- Base library stack: `docker compose -f docker/docker-compose.yml up -d` (service: `effectful`)
- Base lint + type check: `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code`
- Base tests: `... poetry run test-unit`, `... poetry run test-integration`, or `... poetry run test-all` (Codex must set its own test-run timeout and it must be >= 4 hours; never shorten or pre-empt runs)
- Packaging: `... poetry build`
- Run ad-hoc code (base): `docker compose -f docker/docker-compose.yml exec effectful poetry run python`

**Multiple containers**: Each demo has its own Docker environment and service names (e.g., HealthHub under `demo/healthhub/docker/`). Before running any `docker compose ... exec ... poetry run ...`, decide whether you are targeting the base library (`effectful` service) or a demo’s container; use that compose file and service name consistently.

**Only Python entrypoint**: Always run Python via the appropriate container + Poetry command for the target (base vs demo). Never call `python` or `python3` on the host; Poetry virtualenvs are disabled and host interpreters are unsupported.

## Coding Style & Naming Conventions

- Black (line length 100) + MyPy `--strict`; zero tolerance for `Any`, `cast()`, or `# type: ignore`.
- Python 4-space indentation; prefer frozen dataclasses for data/ADTs.
- Effects use verb-noun names (`SendText`, `GetUserById`); domain models are nouns (`User`, `Message`); keep unions exhaustive and avoid `Optional` when an ADT is clearer.

## Testing Guidelines

- Pytest everywhere; name files `test_*.py`, keep async tests using `pytest.mark.asyncio`.
- pytest-timeout default is 60s **per test** (unit, integration, e2e), including fixture setup/teardown; increase per test only with evidence, never disable globally.
- Use `mocker.AsyncMock(spec=Protocol)` for infrastructure fakes; fixtures in `tests/fixtures/` seed deterministic data.
- Integration/e2e tests require Docker services running; they operate on real infra and may TRUNCATE/seed state per test.
- Tests run **only inside Docker via Poetry** (`docker compose -f <compose> exec <service> poetry run pytest ...`); never invoke `pytest` or `poetry run pytest` on the host (see documents/engineering/docker_workflow.md#forbidden-running-pytest-locally).

## Commit & Pull Request Guidelines

- Git history favors short, imperative, lowercase subjects (`cleanup`, `documentation refactor`).
- Before proposing changes: run `check-code` and the relevant test suite; note any skipped coverage.
- PRs should describe intent, list commands run, link issues, and include screenshots/log snippets for user-facing or observability changes.
- Internal agents must not run `git commit`/`git push`; leave changes uncommitted unless you are a human contributor preparing the PR.\*\*\* End Patch
