# JIT and Staged Lowering in the Compiler Morphology

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: intro.md, ml_training.md, engineering/architecture.md

> **Purpose**: Define rules, standards, and verification requirements for JIT and staged lowering in the Effectful compiler morphology. Pure workflow and compute descriptions remain inspectable inside the purity boundary; staged lowerings then target Rust where it can reach the runtime, or other target-native backends where the runtime, platform, or optimization envelope requires them.

______________________________________________________________________

## SSoT Link Map

| Need                       | Link                                                                                    |
| -------------------------- | --------------------------------------------------------------------------------------- |
| Effectful overview         | [DSL Intro](intro.md)                                                                   |
| Proof engine               | [Proof Engine](proof_engine.md)                                                         |
| Boundary model             | [Proof Boundary and Purity Boundary](intro.md#2-the-proof-boundary-and-purity-boundary) |
| Pure compute DAG semantics | [Pure Compute DAGs in Haskell](pure_compute_dags_in_haskell.md)                         |
| Assumption documentation   | [Assumption Documentation](intro.md#5-assumption-documentation)                         |
| ML training JIT            | [ML Training](ml_training.md)                                                           |
| Verification workflow      | [Verification Contract](../engineering/verification_contract.md)                        |
| Runner pattern             | [Runner Pattern](../engineering/runner_pattern.md)                                      |

______________________________________________________________________

## 1. Why JIT Exists Within the Morphology

### 1.1 Why Pure Workflow Descriptions Matter

Haskell is ideal for expressing and optimizing pure workflow descriptions:

- **Compute graph optimization**: Lazy evaluation and algebraic data types make it natural to build, inspect, and transform computation graphs
- **Pure compute DAGs as data**: Haskell can preserve workflow structure before execution, including applicative or traversable regions where independence is still visible
- **Pure effect descriptions**: Effects are values that can be analyzed and optimized before execution
- **Fusion**: combining adjacent operations into one larger lowered region without changing
  semantics, which reduces intermediates and can open more backend optimization
- **Whole-program optimization**: Pure semantics enable aggressive cross-module optimization

The FP vocabulary behind those claims is defined in
[pure_compute_dags_in_haskell.md](pure_compute_dags_in_haskell.md). This document assumes that
workflow descriptions are already available as pure, inspectable data and focuses on what happens
when they are lowered.

### 1.2 Why Runtime and Native Languages Still Matter

Pure descriptions are not enough by themselves. The runtime still has to execute on concrete
targets, interact with drivers, and satisfy latency constraints:

- **Garbage collection**: Haskell's GC creates unpredictable latency spikes
- **Tail latency**: For systems work, P99 latency matters more than throughput
- **Driver interfaces**: C FFI is cumbersome in Haskell, native in Rust
- **Memory layout**: Systems code often requires precise memory control
- **Forced-native platforms**: browsers, mobile runtimes, CUDA stacks, FPGA flows, and proprietary
  SDKs may force JS, Swift, Kotlin, C++, CUDA, HDL, or vendor-native toolchains

### 1.3 The Division of Labor

The pure layer decides WHAT to compute; the runtime layer decides HOW to execute it.

```mermaid
flowchart LR
  subgraph Haskell["PURE REPRESENTATION LAYER (Inside Purity Boundary)"]
    DSL["Source or EDSL"] --> Graph["Workflow / Compute Graph"]
    Graph --> Optimize["Optimization Passes"]
    Optimize --> IR["Effect IR"]
  end
  subgraph Runtime["IMPERATIVE RUNTIME OR TARGET-NATIVE BACKEND"]
    IR --> Codegen["Code Generation"]
    Codegen --> Compile["Rust / Native Compilation"]
    Compile --> Execute["Execution"]
  end
  Execute --> Drivers["Drivers/APIs"]
```

Crossing from a pure IR to code generation is a **purity-boundary crossing**, not an "extension"
of purity. Generated Rust can still remain inside the **proof boundary** when its lowering rules,
memory contracts, and runtime behavior are modeled and verified. The same is true for JS, Swift,
Kotlin, C++, CUDA, or other target-native artifacts. Drivers and external APIs remain outside the
proof boundary.

### 1.4 JIT Is One Backend Posture, Not the Whole Story

JIT is important because it allows late specialization against dynamic structure, but it is only
one posture within the larger morphology:

- **Static lowering** for stable operations and heavily reviewed code paths
- **JIT lowering** for dynamic structure, shape-dependent optimization, or deployment-time
  specialization
- **Hybrid lowering** where static kernels and generated regions are linked together
- **Full target-native lowering** when the best artifact is directly in CUDA, JS, Swift, Kotlin,
  HDL, or a vendor toolchain rather than Rust

### 1.5 Morphology Axes That Matter for JIT

JIT interacts with several of the morphology axes from
[dsl_compiler_morphology.md](dsl_compiler_morphology.md):

| Axis                      | JIT Question                                                                 |
| ------------------------- | ---------------------------------------------------------------------------- |
| **Surface language**      | which source layer preserves workflow structure long enough to optimize?     |
| **Core IR**               | where do free modeling, effect graphs, SSA, and region tracking each fit?    |
| **Backend realization**   | is Rust enough, or is a target-native artifact required?                     |
| **Runtime strategy**      | what should be interpreted, staged, or compiled ahead of time?               |
| **Verification boundary** | which generated artifacts and lowering contracts are modeled versus assumed? |

______________________________________________________________________

## 2. The Boundary Model in JIT

### 2.1 Purity Boundary: Pure Workflow Graph and Lowered Pure IR

Everything inside the purity boundary is:

- **Pure**: No side effects during graph construction
- **Deterministic**: Same inputs produce same outputs
- **Inspectable**: Graphs can be analyzed, validated, and transformed
- **Optimizable**: fusion, vectorization, and placement optimization

### 2.2 Proof Boundary: Generated Runtimes and Native Backends

Generated runtimes and native backends are:

- **Imperative**: May have local mutable state
- **Outside the purity boundary**: It consumes lowered pure descriptions rather than remaining pure itself
- **Verified**: Conforms to TLA+ specifications
- **Bounded**: Has deterministic resource limits (time, memory)
- **Safe by default where possible**: Uses safe Rust unless explicitly justified, or the safest
  equivalent discipline available for the chosen target

### 2.3 Outside Proof Boundary: Drivers and APIs

Generated runtimes communicate with:

- Device drivers (GPU, network, storage)
- Operating system services
- Proprietary APIs

All interactions with this layer require documented assumptions.

______________________________________________________________________

## 3. Graph Optimization and Lowering Structure

### 3.1 Graph Representation

The outer compute graph is one representation layer, not necessarily the only IR in the pipeline.
In practice, a staged lowering often moves through several forms:

- a pure workflow representation that preserves independence and dependency structure
- an effect graph that makes orchestration and hazard edges explicit
- an SSA-like or ANF-like IR for local compute-heavy regions
- region or capability tracking for placement, memory, and native escape hatches

One schematic outer graph looks like:

```haskell
data ComputeNode
  = Pure PureOp [ComputeNode]           -- Pure computation
  | Effect EffectDesc [ComputeNode]     -- Effect requiring execution
  | Fork [ComputeNode]                  -- Parallel branches
  | Sequence ComputeNode ComputeNode    -- Sequential dependency
  | Cached CacheKey ComputeNode         -- Memoization point
```

### 3.2 Optimization Passes

Standard optimization passes include:

| Pass                      | Description                                      |
| ------------------------- | ------------------------------------------------ |
| **Fusion**                | Eliminate intermediate allocations               |
| **Vectorization**         | Batch similar operations                         |
| **Memory planning**       | Pre-allocate buffers, minimize copies            |
| **Placement**             | Decide where operations execute (edge vs server) |
| **Batching**              | Group database/network operations                |
| **Dead code elimination** | Remove unreachable nodes                         |

### 3.3 Semantic Preservation

**HARD REQUIREMENT**: Every optimization pass must preserve semantics.

Verification approach:

1. Define semantics as a denotational function `eval :: ComputeNode -> Value`
1. Prove that for every pass `p`: `eval(p(g)) = eval(g)`
1. Encode preservation proofs in Haskell's type system where possible
1. Use property-based testing for complex passes

______________________________________________________________________

## 4. JIT and Code Generation Rules

### 4.1 HARD REQUIREMENTS

All JIT-generated code MUST satisfy:

| Requirement                  | Description                                                      |
| ---------------------------- | ---------------------------------------------------------------- |
| **Deterministic generation** | Same compute graph always produces identical generated code      |
| **Semantic preservation**    | Generated code has same behavior as interpreted graph            |
| **Footprint compliance**     | No access beyond declared read/write sets                        |
| **Error mapping**            | All errors map to typed Result variants                          |
| **Resource bounds**          | All loops have provable termination; all allocations are bounded |

### 4.2 Safe Rust by Default When Rust Is the Target

Generated code uses safe Rust exclusively unless:

1. Performance cannot be achieved via safe constructs
1. The unsafe block is documented as an assumption
1. The code is reviewed and approved explicitly

### 4.3 Unsafe Rust Policy

When unsafe Rust is required:

```rust
// ASSUMPTION: GPU driver correctly implements CUDA memcpy semantics
// DEPENDS ON: CUDA driver version >= 12.0
// TLA+ PROPERTY: MemcpyPreservesData
// FAILURE MODE: Silent data corruption
// MITIGATION: Checksum validation on critical paths
unsafe {
    cuda_memcpy(dst, src, len);
}
```

**Every unsafe block must include**:

- `ASSUMPTION`: What we assume is true
- `DEPENDS ON`: External dependencies
- `TLA+ PROPERTY`: Which TLA+ property relies on this
- `FAILURE MODE`: What happens if assumption is violated
- `MITIGATION`: How we detect or recover from failures

### 4.4 Target-Native Safety Policy

When the target is not Rust, the generated artifact must still satisfy the same semantic and
boundary discipline:

- preserve the meaning of the lowered pure IR
- declare its resource, memory, and failure contracts explicitly
- document assumptions at every driver, SDK, or vendor boundary
- remain inside the proof boundary only to the extent those contracts are actually modeled and
  verified

______________________________________________________________________

## 5. TLA+ Verification at Proof Boundary

### 5.1 What TLA+ Proves

TLA+ specifications verify:

- **Optimizer correctness**: Transformations preserve semantics
- **Footprint compliance**: Generated code respects declared access patterns
- **Lowering behavior**: Generated Rust or target-native code follows the modeled contracts
- **Termination**: All generated loops terminate
- **Error handling**: All error paths produce typed results

### 5.2 What TLA+ Cannot Prove

TLA+ cannot verify:

- **Rust compiler correctness**: We assume rustc works correctly
- **Other compiler toolchains**: We assume target-native compilers and vendor tools behave
  according to their contracts
- **Hardware behavior**: We assume CPU/GPU execute instructions correctly
- **Driver correctness**: We assume drivers implement their contracts
- **Unsafe Rust**: We cannot prove memory safety of unsafe blocks
- **External APIs**: We cannot prove third-party APIs behave correctly

### 5.3 Assumption Inventory

Every JIT compilation context maintains an assumption inventory:

````
# example
JIT Context: compute_graph_123
Assumptions:
  1. Rust compiler produces correct x86_64 code
  2. Linux scheduler provides fair CPU time
  3. PostgreSQL driver returns correct query results
  4. System clock is monotonically increasing
TLA+ Properties depending on assumptions:
  1. GeneratedCodeSemantics (depends on 1)
  2. TimeoutEnforcement (depends on 2, 4)
  3. QueryResultConsistency (depends on 3)
```

### 5.4 Proof Engine Integration

JIT-generated code must pass proof engine verification before deployment. The workflow:

1. Pure workflow or compute graph → generated runtime artifact
2. Extract phase generates verification obligations from the graph
3. Check phase verifies generated code preserves semantics
4. Verify phase confirms all TLA+ properties hold

This ensures JIT compilation does not introduce correctness regressions. See [proof_engine.md](proof_engine.md) for the complete proof engine architecture.

______________________________________________________________________

## 6. Communicating with Drivers and APIs

### 6.1 Rust's Role

Rust is the preferred proof-boundary-edge runtime where Rust can target the platform:

1. **Receives effect descriptions** from pure IR
2. **Translates to driver calls** using appropriate APIs
3. **Handles driver responses** including errors
4. **Returns typed results** back through the boundary

### 6.2 Driver Communication Pattern

The pattern below is shown in Rust because Rust is the preferred systems target when available. The
same boundary logic applies to JS, Swift, Kotlin, C++, CUDA host code, or other imperative
backends.

```rust
pub fn run_effect(effect: EffectIR) -> Result<Value, EffectError> {
    match effect {
        EffectIR::DbQuery { sql, params } => {
            // ASSUMPTION: PostgreSQL returns correct results for valid SQL
            let rows = db_driver.query(&sql, &params)
                .map_err(|e| EffectError::Db(classify_db_error(e)))?;
            Ok(Value::Rows(rows))
        }
        EffectIR::HttpRequest { request } => {
            // ASSUMPTION: HTTP client correctly implements HTTP/1.1 semantics
            let response = http_client.execute(request)
                .map_err(|e| EffectError::Http(classify_http_error(e)))?;
            Ok(Value::HttpResponse(response))
        }
        // ... other effects
    }
}
````

### 6.3 Assumption Documentation for Drivers

Every driver integration requires:

````markdown
## Driver: PostgreSQL (via tokio-postgres)

### Assumptions
1. Query results match SQL semantics for PostgreSQL 14+
2. Connection timeouts are enforced by the driver
3. SSL/TLS provides confidentiality and integrity

### Failure Modes
- Network partition: Connection error
- Query timeout: Timeout error (bounded by config)
- Invalid SQL: Syntax error at compile time (when possible)

### Mitigations
- Connection pooling with health checks
- Query timeout enforcement at application layer
- Prepared statements to prevent SQL injection
```text

---

## 7. Static vs JIT Decision Framework

### 7.1 When to Use Static Rust or Hand-Written Runtime Code

Use hand-written static runtime code when:

| Criterion | Reason |
|-----------|--------|
| **Known patterns** | Optimization has been manually tuned |
| **Unsafe required** | Complex unsafe code needs human review |
| **Stable operations** | The operation won't change dynamically |
| **Driver integration** | Complex driver protocols are hard to generate |
| **Performance critical** | Hand-optimization outperforms generated code |

### 7.2 When to Use JIT

Use JIT-generated Rust or target-native code when:

| Criterion | Reason |
|-----------|--------|
| **Dynamic structures** | Data shapes aren't known until runtime |
| **Fusion opportunities** | Whole-program optimization finds savings |
| **Rapid iteration** | Morphology changes do not require hand-editing every backend |
| **Portability** | Same IR can lower to multiple backends |
| **Verification** | Generated code is easier to prove correct |

### 7.3 When to Use Full Target-Native Lowering

Use full target-native lowering when:

| Criterion | Reason |
|-----------|--------|
| **Forced platform language** | Browser, mobile, CUDA, FPGA, or vendor toolchains require a native artifact |
| **Deeper fusion** | The target can fuse across a larger compute region than a thin bridge can expose |
| **Backend-specific optimization** | Placement, memory layout, or dead-node removal are materially better in the native IR |
| **Domain toolchain leverage** | The vendor stack already provides the strongest optimizer or scheduler |

### 7.4 Hybrid Approach

Most systems use both:

```mermaid
flowchart TB
  Graph["Compute Graph"] --> Analysis["Analysis"]
  Analysis --> Static["Static Patterns"]
  Analysis --> Dynamic["Dynamic Patterns"]
  Static --> StaticRust["Hand-written Runtime Code"]
  Dynamic --> JIT["JIT Generation"]
  JIT --> GeneratedRust["Generated Region"]
  StaticRust --> Link["Link or Host"]
  GeneratedRust --> Link
  Link --> Execute["Execute"]
```text

---

## 8. Error Handling

### 8.1 Compile-Time Errors

JIT compilation can fail for:

```mermaid
flowchart TB
  %% kind: ADT
  %% id: effectful.jit.JitError
  %% summary: JIT compilation and execution errors
  JitError["JitError"]
  JitError --> InvalidGraph["InvalidGraph: malformed compute graph"]
  JitError --> OptimizationFailed["OptimizationFailed: pass failed invariant"]
  JitError --> CodegenFailed["CodegenFailed: could not generate valid target code"]
  JitError --> RustCompileError["BackendCompileError: toolchain rejected generated code"]
  JitError --> ResourceExceeded["ResourceExceeded: graph too large to compile"]
````

All compile-time errors are typed and include:

- Which pass or stage failed
- The relevant subgraph
- Suggested remediation

### 8.2 Runtime Errors

Generated code never panics. All errors return `Result<T, RuntimeError>`:

- **Effect errors**: Driver/API failures → typed error variants
- **Resource errors**: Timeout, memory limit → typed error variants
- **Logic errors**: Assertion failures → typed error variants with context

### 8.3 Error Propagation

Errors propagate through the boundary model:

````
# example
Purity Boundary    Proof Boundary      Outside
   (Pure IR)        (Runtime)        (Drivers)
                                          │
                      ┌───────────────────┘
                      │ Driver error
                      ▼
                 classify_error()
                      │
                      │ Typed EffectError
                      ▼
              Result::Err(EffectError)
                      │
                      │ Effect result
   ┌──────────────────┘
   │
   ▼
Effect outcome in pure domain
```text

---

## 9. JIT Code Lifecycle

### 9.1 Lifecycle State Machine

```mermaid
stateDiagram-v2
  %% kind: StateMachine
  %% id: effectful.jit.JitCodeLifecycle
  %% summary: JIT code from generation to execution
  [*] --> GraphReceived
  GraphReceived --> Optimizing: optimize()
  Optimizing --> Generating: codegen()
  Optimizing --> Failed: optimization error
  Generating --> Compiling: invoke backend compiler
  Generating --> Failed: codegen error
  Compiling --> Ready: compilation success
  Compiling --> Failed: backend compiler error
  Ready --> Executing: execute()
  Executing --> Ready: execution complete
  Executing --> Failed: runtime error
  Failed --> [*]
  Ready --> Evicted: cache pressure
  Evicted --> [*]
````

### 9.2 Caching

JIT-compiled code is cached by:

- Compute graph hash (content-addressed)
- Optimization configuration hash
- Target platform identifier

Cache eviction follows LRU policy with configurable limits.

### 9.3 Hot Code Replacement

For long-running systems:

1. New graph version triggers JIT compilation
1. Old version continues executing current requests
1. New version handles new requests after compilation completes
1. Old version is evicted when all in-flight requests complete

______________________________________________________________________

## 10. Verification Checklist

Before deploying JIT-generated code:

- [ ] All optimization passes have preservation proofs
- [ ] Generated code passes the relevant backend toolchain checks
- [ ] TLA+ conformance tests pass
- [ ] Assumption inventory is complete and current
- [ ] Unsafe blocks (if any) have full assumption documentation
- [ ] Error handling covers all driver failure modes
- [ ] Resource bounds are verified (time, memory)
- [ ] Cache invalidation strategy is documented

______________________________________________________________________

## Cross-References

- [intro.md](intro.md) — Effectful compiler morphology overview and boundary model
- [proof_engine.md](proof_engine.md) — Effectful Proof Engine architecture
- [proof_boundary.md](proof_boundary.md) — Philosophical foundation for verification limits
- [ml_training.md](ml_training.md) — JIT for ML workloads
- [engineering/verification_contract.md](../engineering/verification_contract.md) — TLA+ verification workflow
- [engineering/runner_pattern.md](../engineering/runner_pattern.md) — Effect runner contract
- [engineering/generated_code_validation.md](../engineering/generated_code_validation.md) — Code generation validation
