# Effectual DSL and Effectful Compiler Specification

**Status**: Authoritative source
**Supersedes**: effectual_dsl_and_effectful_compiler_spec_final.md
**Referenced by**: documents/documentation_standards.md, documents/engineering/functional_catalogue.md, verification_boundary.md

> **Purpose**: Define the **Effectual DSL** for expressing real-world business behavior as a **total, pure mathematical model** in **TLA+/PlusCal** (SSoT), and define the **Effectful Compiler** (Haskell) that deterministically generates **pure ADTs**, **pure state machines**, **Mermaid**, and **typed execution boundaries** for use in **Python**, **TypeScript**, and other languages.

## SSoT Link Map

| Need                    | Link                                                           |
| ----------------------- | -------------------------------------------------------------- |
| Documentation standards | [Documentation Standards](../documentation_standards.md)       |
| Functional catalogue    | [Functional Catalogue](../engineering/functional_catalogue.md) |
| Total pure modelling    | [Total Pure Modelling](../engineering/total_pure_modelling.md) |
| Architecture            | [Architecture](../engineering/architecture.md)                 |
| Code quality            | [Code Quality](../engineering/code_quality.md)                 |

______________________________________________________________________

## 1. Total Pure Modelling

### 1.1 The core idea

Total Pure Modelling (TPM) is a doctrine for keeping software aligned with reality by making the **model** the truth:

- The domain is represented as a **pure mathematical state space**.
- All possible external inputs are represented as **events**.
- All real-world actions are represented as **effects** (pure data).
- The model evolves only by a **total** step function/relation.

```mermaid
flowchart LR
Reality[Reality] --> Observe[Observe]
Observe --> Event[Event]
Event --> Model[Model]
Model --> Effect[Effect]
Effect --> Act[Act]
Act --> Reality
```

TPM is not primarily a coding style. It is a discipline of **representation**:

- If somdething can happen in reality, the model has a representation for it.
- If something cannot happen in reality, the model must not be able to represent it.
- If the model does not decide, the system must not “guess”.

### 1.2 Totality and illegal states

**Totality** means there are no “stuck” states or unhandled inputs:

- Every modeled state has a defined response to every modeled event.
- Missing cases are treated as specification errors.

**Illegal states are impossible to represent** means:

- Absence, partiality, and intermediate states are expressed as explicit ADT variants.
- If an “authenticated session” requires user identity and roles, those must be payload fields of the corresponding variant, not scattered nullable values.

```mermaid
flowchart TB
ADTs[ADTs] --> TotalMatch[TotalMatch]
TotalMatch --> NoStuck[NoStuckStates]
ADTs --> Illegal[IllegalStates]
Illegal --> Unrepresentable[Unrepresentable]
```

### 1.3 Effects, not ambient reality

TPM eliminates ambient sources of truth. The model never reads:

- time
- randomness
- environment flags
- network state
- database state

Instead, the model requests effects and receives events.

```mermaid
flowchart TB
Model[Model] --> Request[RequestEffect]
Request --> World[World]
World --> Outcome[OutcomeEvent]
Outcome --> Model
```

### 1.4 Provability and auditability

Because the model is pure and total:

- it can be checked (model checking, invariants, trace exploration)
- it can be generated into many target languages consistently
- its decision points are auditable as data and functions

```mermaid
flowchart TB
Model[Model] --> Prove[Prove]
Model --> Generate[Generate]
Model --> Audit[Audit]
```

______________________________________________________________________

## 2. System overview

### 2.1 One diagram: the whole system

```mermaid
flowchart TB
Models[Models] --> Verify[Verify]
Verify --> Extract[Extract]
Extract --> IR[IR]
IR --> GenDocs[GenDocs]
IR --> GenPurePy[GenPurePy]
IR --> GenPureTs[GenPureTs]
IR --> GenTests[GenTests]
GenPurePy --> RuntimePy[RuntimePy]
GenPureTs --> RuntimeTs[RuntimeTs]
```

- **Models**: `documents/models/**/*.tla` (Tier 0 SSoT)
- **Verify**: TLA+ validation and TLC model checks (deterministic configs)
- **Extract**: parse Effectual DSL blocks from TLA+/PlusCal
- **IR**: normalized compiler IR (Tier 1, internal)
- **GenDocs**: generated Mermaid + model views (Tier 2)
- **GenPurePy / GenPureTs**: generated Tier 2 pure code
- **RuntimePy / RuntimeTs**: Tier 3 interpreters + Tier 4 effect runners + Tier 5 framework glue

______________________________________________________________________

## 3. Tier taxonomy

```mermaid
flowchart TB
T0[Tier0 Model] --> T1[Tier1 IR]
T1 --> T2[Tier2 Pure]
T2 --> T3[Tier3 Interpreter]
T3 --> T4[Tier4 Runner]
T4 --> T5[Tier5 Framework]
```

| Tier | Name        | Must be                             | Examples                             |
| ---- | ----------- | ----------------------------------- | ------------------------------------ |
| 0    | Model       | TLA+/PlusCal SSoT                   | `documents/models/healthhub/*.tla`   |
| 1    | IR          | compiler-internal                   | Haskell IR values                    |
| 2    | Pure        | total and pure                      | generated ADTs, reducers, decisions  |
| 3    | Interpreter | generic orchestration               | dispatch, scheduling, retries policy |
| 4    | Runner      | one impure function per effect type | `runDbQuery(eff) -> Result[...]`     |
| 5    | Framework   | glue only                           | FastAPI routes, React components     |

**Hard rule**: Tier 5 contains no business decisions. It only translates external inputs into pure events and pure outputs into framework responses.

______________________________________________________________________

## 4. Effect runners

### 4.1 Runners are language-agnostic operations

Runners execute the same real-world operation regardless of language. The operation is determined by the effect value.

Example:

- a SQL query effect describes a SQL query
- running that effect executes that SQL query
- this meaning is identical across Python, TypeScript, Rust, etc

```mermaid
flowchart TB
Eff[Effect] --> Meaning[Meaning]
Meaning --> RunnerPy[RunnerPython]
Meaning --> RunnerTs[RunnerTypeScript]
RunnerPy --> Same[SameOperation]
RunnerTs --> Same
```

### 4.2 One impure function per effect type

For each effect type, there is exactly one impure runner function.

- Input: the **pure effect value only**
- Output: `Result[OkT, ErrT]` or an async container that resolves to it
- No other call arguments exist (dependencies are injected at construction time)

```mermaid
flowchart TB
Eff[Effect] --> Run[RunEffect]
Run --> Ok[Ok]
Run --> Err[Err]
```

### 4.3 Result is the only outcome type

```mermaid
flowchart TB
%% kind: ADT
%% id: effectful.core.Result
%% summary: Result[E,A] is Ok or Err
Result[Result]
Result --> Ok
Result --> Err
Ok["Ok(value)"]
Err["Err(error)"]
```

- Runners must not throw exceptions to signal expected failures.
- Runners must convert dependency failures into typed `Err(...)`.

### 4.4 Dependency injection is allowed

Runners may require injected dependencies (DB pools, HTTP clients, filesystem handles, mocks).

Injection occurs when constructing the runner implementation.

```mermaid
flowchart TB
Deps[Deps] --> RunnerImpl[RunnerImpl]
RunnerImpl --> Run[RunEffect]
Run --> Result[Result]
```

### 4.5 Dependency failures are converted

Failures from injected dependencies are converted into typed error values.

```mermaid
flowchart TB
Call[Call] --> Catch[Catch]
Catch --> Ok[Ok]
Catch --> Err[Err]
```

### 4.6 No hanging forever

Runners must not hang forever without returning.

Policy:

- Each runner has a deterministic timeout and cancellation policy.
- Timeouts are represented as typed `Err(Timeout(...))`.

```mermaid
flowchart TB
Start[Start] --> Work[Work]
Work --> Done[Result]
Work --> Timeout[Timeout]
Timeout --> Err[Err]
```

______________________________________________________________________

## 5. Generic effects are mandatory

Maximizing what the DSL can represent requires minimizing the impure surface.

- Domain logic is pure.
- Repository patterns are pure.
- Runners implement a small reusable standard effect set.

```mermaid
flowchart TB
Domain[DomainLogic] --> Std[StdEffects]
Std --> Runner[Runner]
Runner --> Std
Std --> Domain
```

### 5.1 Standard effect kit (StdEffects)

```mermaid
flowchart TB
%% kind: ADT
%% id: effectful.std.Effect
%% summary: Generic, reusable effect set
Effect[Effect]
Effect --> DbQuery
Effect --> HttpRequest
Effect --> KvGet
Effect --> KvSet
Effect --> NowMs
Effect --> RandomBytes
Effect --> Log
DbQuery["DbQuery(sql, params, mode)"]
HttpRequest["HttpRequest(request)"]
KvGet["KvGet(key)"]
KvSet["KvSet(key, value)"]
NowMs["NowMs()"]
RandomBytes["RandomBytes(n)"]
Log["Log(level, message)"]
```

______________________________________________________________________

## 6. Generic DB query effect

### 6.1 DB types

```mermaid
flowchart TB
%% kind: ADT
%% id: effectful.std.db.DbMode
%% summary: DbMode selects query execution mode
DbMode[DbMode]
DbMode --> One
DbMode --> Many
DbMode --> Exec
One["One()"]
Many["Many()"]
Exec["Exec()"]
```

```mermaid
flowchart TB
%% kind: ADT
%% id: effectful.std.db.DbFailure
%% summary: DbFailure is typed and exhaustive
DbFailure[DbFailure]
DbFailure --> NotFound
DbFailure --> Conflict
DbFailure --> Constraint
DbFailure --> Timeout
DbFailure --> Connection
DbFailure --> Unknown
NotFound["NotFound()"]
Conflict["Conflict()"]
Constraint["Constraint(message)"]
Timeout["Timeout()"]
Connection["Connection(message)"]
Unknown["Unknown(message)"]
```

### 6.2 Repository pattern is pure

```mermaid
flowchart TB
Req[DomainRequest] --> Repo[PureRepo]
Repo --> Eff[DbQuery]
Eff --> RunDb[RunDbQuery]
RunDb --> Rows[DbRows]
Rows --> Repo
Repo --> Res[DomainResult]
```

- SQL and parameters are pure.
- Mapping `DbRows` to domain ADTs is pure.
- Only the runner is impure.

______________________________________________________________________

## 7. Effectual DSL in TLA+/PlusCal

### 7.1 Where it lives

- SSoT lives under `documents/models/**`.

### 7.2 What is declared

Effectual DSL declarations define:

- payload ADTs (sum types and records)
- state machines
- usage of standard effects
- verification bindings: `Init`, `Next`, `TypeOK`, `Invariants`

### 7.3 Example: HealthHub auth flow (pure)

```mermaid
stateDiagram-v2
%% kind: StateMachine
%% id: healthhub.auth.AuthFlow
%% summary: Auth readiness machine
[*] --> Initializing
Initializing --> Unauthenticated: HydrateNone
Initializing --> SessionRestoring: HydrateStored
SessionRestoring --> Authenticated: RefreshOk
SessionRestoring --> SessionExpired: RefreshExpired
SessionRestoring --> Unauthenticated: RefreshFail
Authenticated --> Unauthenticated: Logout
SessionExpired --> Unauthenticated: RedirectLogin
```

______________________________________________________________________

## 8. Effectful Compiler responsibilities

### 8.1 Compiler pipeline

```mermaid
flowchart TB
Discover[Discover] --> Verify[Verify]
Verify --> Parse[ParseDSL]
Parse --> Normalize[NormalizeIR]
Normalize --> Gen[Generate]
Gen --> Check[CheckNoDiff]
```

### 8.2 Outputs are tiered

```mermaid
flowchart TB
IR[IR] --> Docs[Docs]
IR --> Pure[PureCode]
IR --> Tests[Tests]
Docs --> T2Doc[Tier2Docs]
Pure --> T2Code[Tier2Code]
Tests --> T2Tests[Tier2Tests]
```

______________________________________________________________________

## 9. Why Haskell for the compiler

Haskell is a good fit for the Effectful Compiler because the compiler itself must embody the same values as the system:

- **First-class ADTs**: the compiler IR is naturally represented as sum types and records.
- **Pure transformations**: parsing, normalization, fingerprinting, and generation are deterministic functions.
- **Totality pressure**: exhaustive pattern matching and strong typing make “missing cases” loud.
- **Backends as composable modules**: code generation can be expressed as pure pretty-printing over IR.
- **Reference semantics runner**: Haskell can host a reference interpreter for pure models for testing and cross-language validation.

```mermaid
flowchart TB
IR[IR] --> PureXforms[PureTransforms]
PureXforms --> Backends[Backends]
Backends --> Outputs[Outputs]
```

______________________________________________________________________

## 10. Generated code structure

### 10.1 Recommended repository layout

```mermaid
flowchart TB
Repo[Repo]
Repo --> Documents[documents]
Documents --> Models[models]
Documents --> GenDocs[generated]
Repo --> Generated[generated]
Generated --> Py[python]
Generated --> Ts[typescript]
Repo --> Demo[demo]
Demo --> Healthhub[healthhub]
```

### 10.2 Generated paths

- `generated/python/effectful_std/**` (Tier 2 std effects + Result + stubs)
- `generated/python/healthhub_pure/**` (Tier 2 HealthHub pure logic)
- `generated/typescript/effectful_std/**` (Tier 2)
- `generated/typescript/healthhub_pure/**` (Tier 2)

______________________________________________________________________

## 11. Interpreter and runner sketches

### 11.1 Python runner sketch (DB)

#### Tier map

| Artifact                  | Tier |
| ------------------------- | ---- |
| `effectful_std` ADTs      | 2    |
| `healthhub_pure` logic    | 2    |
| interpreter orchestration | 3    |
| runner implementations    | 4    |
| FastAPI glue              | 5    |

#### Generated runner signature (generic)

```python
# file: generated/python/effectful_std/runtime/runners.py
from __future__ import annotations
from typing import Protocol, Awaitable
from effectful_std.core.result import Result
from effectful_std.db.effects import DbQuery
from effectful_std.db.types import DbRows, DbFailure

class DbRunner(Protocol):
    def run_db_query(self, eff: DbQuery) -> Awaitable[Result[DbFailure, DbRows]]: ...
```

#### Handwritten runner implementation (generic)

```python
# file: demo/healthhub/backend/runtime/db_runner_asyncpg.py
from __future__ import annotations
from dataclasses import dataclass
from effectful_std.core.result import Ok, Err, Result
from effectful_std.db.effects import DbQuery
from effectful_std.db.types import DbRows, DbFailure

@dataclass(frozen=True)
class AsyncpgDbRunner:
    pool: object
    timeout_s: float

    async def run_db_query(self, eff: DbQuery) -> Result[DbFailure, DbRows]:
        try:
            # timeout enforcement is required by policy
            rows = await self.pool.fetch(eff.sql, *eff.params_native())
            return Ok(driver_rows_to_dbrows(rows))
        except Exception as ex:
            return Err(DbFailure.Unknown(message=str(ex)))
```

### 11.2 TypeScript runner sketch (HTTP)

#### Generated runner signature (generic)

```ts
// file: generated/typescript/effectful_std/runtime/runners.ts
import { Result } from '../core/result'
import { HttpRequest } from '../http/effects'
import { HttpResponse, HttpFailure } from '../http/types'

export type HttpRunner = {
  readonly runHttpRequest: (eff: HttpRequest) => Promise<Result<HttpFailure, HttpResponse>>
}
```

#### Handwritten runner implementation (generic)

```ts
// file: demo/healthhub/frontend/src/runtime/httpRunnerFetch.ts
import { ok, err, Result } from 'generated/typescript/effectful_std/core/result'
import { HttpRequest } from 'generated/typescript/effectful_std/http/effects'
import { HttpResponse, HttpFailure } from 'generated/typescript/effectful_std/http/types'

export const runHttpRequest = async (eff: HttpRequest): Promise<Result<HttpFailure, HttpResponse>> => {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), eff.timeoutMs)
    const res = await fetch(eff.url, { method: eff.method, headers: eff.headers, body: eff.body, signal: controller.signal })
    clearTimeout(timeout)
    const text = await res.text()
    return ok({ status: res.status, bodyText: text })
  } catch (e) {
    return err({ kind: 'NetworkFailure', message: String(e) })
  }
}
```

______________________________________________________________________

## 12. Deterministic enforcement

### 12.1 Gate stack

```mermaid
flowchart TB
TLC[TLC] --> Gen[Gen]
Gen --> Check[CheckNoDiff]
Check --> Type[Typecheck]
Type --> Conf[ConformanceTests]
Conf --> Ship[Ship]
```

- TLC checks Tier 0
- compiler generation is deterministic
- no diffs allowed
- typechecking ensures generated code and handwritten glue compile
- conformance tests ensure state machines and decisions match the model

______________________________________________________________________

## 13. Summary of required handwritten artifacts

### 13.1 Python backend

- Framework glue (Tier 5)
- Runner implementations with injected dependencies (Tier 4)
- Interpreter orchestration (Tier 3)

### 13.2 TypeScript frontend

- Framework glue (Tier 5)
- Runner implementations with timeouts (Tier 4)
- Interpreter orchestration (Tier 3)

______________________________________________________________________

## Cross-References

- `documents/documentation_standards.md` (Mermaid subset and metadata rules)
- `documents/models/**` (SSoT TLA+/PlusCal)
- `demo/healthhub/**` (example integration)
