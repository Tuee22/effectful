# Repository Guidelines

## Project Structure & Module Organization
- Core package lives in `effectful/`: `effects` (dataclasses describing side effects), `interpreters` (runtime handlers), `adapters` (infra integrations), `domain` (frozen ADTs), `programs` (generators), and `observability`.
- Tests in `tests/`: `unit/` and top-level `tests/test_*` cover pure logic; `tests/integration/` hits real PostgreSQL/Redis/MinIO/Pulsar via Docker; `tests/e2e/` exercises chat workflow.
- Docs in `documents/` (engineering standards, API, tutorials); runnable examples in `examples/`.
- Supporting assets: `docker/` for local stack, `tools/` for linters/scripts, `stubs/` for third-party typing. `demo/healthhub/` is an example app; keep changes scoped unless working on the demo.

## Build, Test, and Development Commands
- Start stack: `docker compose -f docker/docker-compose.yml up -d`
- Lint + type check: `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code`
- Tests: `... poetry run test-unit`, `... poetry run test-integration`, or `... poetry run test-all`
- Packaging: `... poetry build`
- Run ad-hoc code: `... poetry run python`
Poetry virtualenvs are disabled; always run commands through Docker with the `compose exec effectful` prefix.

## Coding Style & Naming Conventions
- Black (line length 100) + MyPy `--strict`; zero tolerance for `Any`, `cast()`, or `# type: ignore`.
- Python 4-space indentation; prefer frozen dataclasses for data/ADTs.
- Effects use verb-noun names (`SendText`, `GetUserById`); domain models are nouns (`User`, `Message`); keep unions exhaustive and avoid `Optional` when an ADT is clearer.

## Testing Guidelines
- Pytest everywhere; name files `test_*.py`, keep async tests using `pytest.mark.asyncio`.
- Use `mocker.AsyncMock(spec=Protocol)` for infrastructure fakes; fixtures in `tests/fixtures/` seed deterministic data.
- Integration/e2e tests require Docker services running; they operate on real infra and may TRUNCATE/seed state per test.

## Commit & Pull Request Guidelines
- Git history favors short, imperative, lowercase subjects (`cleanup`, `documentation refactor`).
- Before proposing changes: run `check-code` and the relevant test suite; note any skipped coverage.
- PRs should describe intent, list commands run, link issues, and include screenshots/log snippets for user-facing or observability changes.
- Internal agents must not run `git commit`/`git push`; leave changes uncommitted unless you are a human contributor preparing the PR.*** End Patch
