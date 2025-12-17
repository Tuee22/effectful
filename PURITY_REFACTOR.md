# Purity Migration Plan (HealthHub Backend)

**Purpose**: Move HealthHub backend setup/configuration logic into pure effect programs and interpreters while keeping infrastructure code minimal and domain-agnostic, in line with engineering doctrines.

## Goals
- Express middleware, routing, and resource wiring as pure effect flows; impure code only instantiates external handles.
- Keep effects domain-independent (no healthcare-specific naming in base effects) and lean on **core effectful library primitives** instead of re-implementing them in HealthHub.
- Treat validated Pydantic settings as the only injected dependency; all subsequent steps are modeled as effects returning typed handles (`Result[T, E]`).
- Use effect composition to keep the combined codebase (core + HealthHub overlay) terse and DRY.
- Update engineering docs to encode the “pure-first interpreter” intent.

## Phases
1) **Define config effects (pure)**
   - Prefer existing **effectful core** primitives for config/infra intents; add only missing generic effects to the core library (not HealthHub).
   - Add effects for: settings-to-config plan, database pool creation intent, router registration plan, middleware plan, observability registry binding, static mounts, metrics route wiring.
   - Keep names generic (e.g., `BuildHttpApp`, `ConfigureMiddleware`, `CreateDbPool`), with payloads carrying domain-agnostic descriptors.
2) **Interpreter for app assembly**
   - Implement an interpreter that consumes the config effects and produces typed handles (e.g., `AppAssembly`, `PoolHandle`) wrapped in `Result[T, E]`.
   - Ensure interpreter owns I/O; failures stay typed (no ambient exceptions).
   - Keep impure layer thin: map effect data → infra calls (asyncpg pool, FastAPI router include, middleware attach, static mounts), reusing core interpreter helpers where available.
3) **Tokenized handles + lifecycle**
   - Represent external resources as opaque tokens/handles returned on success; pure code never touches concrete clients.
   - Manage lifecycle (startup/shutdown) via effect-driven steps; no mutable globals.
4) **Settings injection boundary**
   - Lifespan creates `Settings` (Pydantic, frozen) and passes it as the sole injected dependency to the interpreter runner.
   - All downstream actions are effects derived from settings (pure), composed from core primitives wherever possible.
5) **Refactor FastAPI lifespan**
   - Lifespan becomes: load settings → run config program via interpreter → receive handles (app, pool, redis factory, observability adapter, static mounts) → expose via `app.state`.
   - Shutdown path: run teardown effects (close pool, redis, etc.) through interpreter.
6) **Retire DatabaseManager imperative path**
   - Replace `DatabaseManager` with an effect-driven pool creation/close flow; adapter remains minimal (`AsyncPgPoolAdapter`) and built from core effect outputs.
7) **Testing strategy**
   - Unit-test pure config program with fakes; assert effect emission and typed results.
   - Integration: interpreter against real infra (asyncpg/redis) via existing docker stack.
   - Add regression tests for startup/shutdown flows using typed handles and ensure HealthHub coverage reuses any core test fixtures/helpers for shared effects.

## Documentation Updates (per documentation_standards)
- Add an SSoT declaration of the “pure-first interpreter assembly” end state in the engineering docs (e.g., `architecture.md`), and mirror a concise doctrine pointer in `code_quality.md`.
- Update `documentation_standards.md` to require overlays/deltas (like HealthHub docs) to link to that SSoT section when describing startup/config flows.
- In the HealthHub overlay docs, note only the domain-specific deltas while pointing to the core SSoT for the generic assembly pattern.
- Ensure new effects stay domain-agnostic; domain-specific routing remains data passed into effects, not effect types themselves; lean on core primitives to avoid duplication.

## Risks / Mitigations
- **Risk**: Effect layer drifts into domain-specific names → **Mitigation**: enforce naming review; lint for healthcare strings in core effects.
- **Risk**: Interpreter grows complex → **Mitigation**: keep impure code limited to infra calls; factor shared helpers.
- **Risk**: Startup failures hidden → **Mitigation**: return `Result[Handle, StartupErrorADT]` and log via observability interpreter.

## Acceptance Criteria
- App startup/shutdown flows run entirely through effect programs/interpreter with only settings injected.
- No module-level mutable state; external resources represented as tokens/handles.
- Docs updated to encode the doctrine shift and link-compliant.
