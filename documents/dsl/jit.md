# JIT Compilation: Haskell Compute Graph to Rust

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: intro.md, ml_training.md, engineering/architecture.md

> **Purpose**: Define rules, standards, and verification requirements for JIT compilation from Haskell compute graphs to Rust code. Haskell excels at compute graph optimization and gives Rust its "marching orders" as pure effects. Rust, being imperative, lives outside the purity boundary but inside the proof boundary.

______________________________________________________________________

## SSoT Link Map

| Need                     | Link                                                                                    |
| ------------------------ | --------------------------------------------------------------------------------------- |
| Effectful overview       | [Effectful DSL Hub](intro.md)                                                           |
| Boundary model           | [Proof Boundary and Purity Boundary](intro.md#2-the-proof-boundary-and-purity-boundary) |
| Assumption documentation | [Assumption Documentation](intro.md#5-assumption-documentation)                         |
| ML training JIT          | [ML Training](ml_training.md)                                                           |
| Verification workflow    | [Verification Contract](../engineering/verification_contract.md)                        |
| Runner pattern           | [Runner Pattern](../engineering/runner_pattern.md)                                      |

______________________________________________________________________

## 1. Why JIT from Haskell to Rust

### 1.1 Haskell's Strengths

Haskell is ideal for expressing and optimizing computation:

- **Compute graph optimization**: Lazy evaluation and algebraic data types make it natural to build, inspect, and transform computation graphs
- **Pure effect descriptions**: Effects are values that can be analyzed and optimized before execution
- **Fusion**: Haskell compilers excel at fusing intermediate data structures
- **Whole-program optimization**: Pure semantics enable aggressive cross-module optimization

### 1.2 Rust's Necessity

Haskell is unsuitable for systems-level execution:

- **Garbage collection**: Haskell's GC creates unpredictable latency spikes
- **Tail latency**: For systems work, P99 latency matters more than throughput
- **Driver interfaces**: C FFI is cumbersome in Haskell, native in Rust
- **Memory layout**: Systems code often requires precise memory control

### 1.3 The Division of Labor

Haskell decides WHAT to compute; Rust decides HOW to execute it.

````mermaid
flowchart LR
  subgraph Haskell["HASKELL (Purity Boundary)"]
    DSL["Pure DSL"] --> Graph["Compute Graph"]
    Graph --> Optimize["Optimization Passes"]
    Optimize --> IR["Effect IR"]
  end
  subgraph Rust["RUST (Proof Boundary)"]
    IR --> Codegen["Code Generation"]
    Codegen --> Compile["Rust Compilation"]
    Compile --> Execute["Execution"]
  end
  Execute --> Drivers["Drivers/APIs"]
```mermaid

---

## 2. The Boundary Model in JIT

### 2.1 Purity Boundary: Haskell Compute Graph

Everything inside the purity boundary is:
- **Pure**: No side effects during graph construction
- **Deterministic**: Same inputs produce same outputs
- **Inspectable**: Graphs can be analyzed, validated, and transformed
- **Optimizable**: Fusion, vectorization, and placement optimization

### 2.2 Proof Boundary: Generated Rust

Generated Rust code is:
- **Imperative**: May have local mutable state
- **Verified**: Conforms to TLA+ specifications
- **Bounded**: Has deterministic resource limits (time, memory)
- **Safe by default**: Uses safe Rust unless explicitly justified

### 2.3 Outside Proof Boundary: Drivers and APIs

Generated Rust communicates with:
- Device drivers (GPU, network, storage)
- Operating system services
- Proprietary APIs

All interactions with this layer require documented assumptions.

---

## 3. Haskell Compute Graph Optimization

### 3.1 Graph Representation

The compute graph is an ADT representing:

```haskell
data ComputeNode
  = Pure PureOp [ComputeNode]           -- Pure computation
  | Effect EffectDesc [ComputeNode]     -- Effect requiring execution
  | Fork [ComputeNode]                  -- Parallel branches
  | Sequence ComputeNode ComputeNode    -- Sequential dependency
  | Cached CacheKey ComputeNode         -- Memoization point
````

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

## 4. JIT Code Generation Rules

### 4.1 HARD REQUIREMENTS

All JIT-generated Rust code MUST satisfy:

| Requirement                  | Description                                                      |
| ---------------------------- | ---------------------------------------------------------------- |
| **Deterministic generation** | Same compute graph always produces identical Rust code           |
| **Semantic preservation**    | Generated code has same behavior as interpreted graph            |
| **Footprint compliance**     | No access beyond declared read/write sets                        |
| **Error mapping**            | All errors map to typed Result variants                          |
| **Resource bounds**          | All loops have provable termination; all allocations are bounded |

### 4.2 Safe Rust by Default

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

______________________________________________________________________

## 5. TLA+ Verification at Proof Boundary

### 5.1 What TLA+ Proves

TLA+ specifications verify:

- **Optimizer correctness**: Transformations preserve semantics
- **Footprint compliance**: Generated code respects declared access patterns
- **Safe Rust behavior**: Safe Rust follows memory safety rules
- **Termination**: All generated loops terminate
- **Error handling**: All error paths produce typed results

### 5.2 What TLA+ Cannot Prove

TLA+ cannot verify:

- **Rust compiler correctness**: We assume rustc works correctly
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
```python

---

## 6. Communicating with Drivers and APIs

### 6.1 Rust's Role

Rust code at the proof boundary edge:

1. **Receives effect descriptions** from Haskell IR
2. **Translates to driver calls** using appropriate APIs
3. **Handles driver responses** including errors
4. **Returns typed results** back through the boundary

### 6.2 Driver Communication Pattern

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

### 7.1 When to Use Static Rust

Use hand-written static Rust when:

| Criterion | Reason |
|-----------|--------|
| **Known patterns** | Optimization has been manually tuned |
| **Unsafe required** | Complex unsafe code needs human review |
| **Stable operations** | The operation won't change dynamically |
| **Driver integration** | Complex driver protocols are hard to generate |
| **Performance critical** | Hand-optimization outperforms generated code |

### 7.2 When to Use JIT

Use JIT-generated Rust when:

| Criterion | Reason |
|-----------|--------|
| **Dynamic structures** | Data shapes aren't known until runtime |
| **Fusion opportunities** | Whole-program optimization finds savings |
| **Rapid iteration** | DSL changes don't require Rust expertise |
| **Portability** | Same IR targets multiple platforms |
| **Verification** | Generated code is easier to prove correct |

### 7.3 Hybrid Approach

Most systems use both:

```mermaid
flowchart TB
  Graph["Compute Graph"] --> Analysis["Analysis"]
  Analysis --> Static["Static Patterns"]
  Analysis --> Dynamic["Dynamic Patterns"]
  Static --> StaticRust["Hand-written Rust"]
  Dynamic --> JIT["JIT Generation"]
  JIT --> GeneratedRust["Generated Rust"]
  StaticRust --> Link["Link"]
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
  JitError --> CodegenFailed["CodegenFailed: could not generate valid Rust"]
  JitError --> RustCompileError["RustCompileError: rustc rejected generated code"]
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
   (Haskell)          (Rust)          (Drivers)
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
  Generating --> Compiling: invoke rustc
  Generating --> Failed: codegen error
  Compiling --> Ready: compilation success
  Compiling --> Failed: rustc error
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
- [ ] Generated code passes rustc with no warnings
- [ ] TLA+ conformance tests pass
- [ ] Assumption inventory is complete and current
- [ ] Unsafe blocks (if any) have full assumption documentation
- [ ] Error handling covers all driver failure modes
- [ ] Resource bounds are verified (time, memory)
- [ ] Cache invalidation strategy is documented

______________________________________________________________________

## Cross-References

- [intro.md](intro.md) — Effectful language overview and boundary model
- [proof_boundary.md](proof_boundary.md) — Philosophical foundation for verification limits
- [ml_training.md](ml_training.md) — JIT for ML workloads
- [engineering/verification_contract.md](../engineering/verification_contract.md) — TLA+ verification workflow
- [engineering/runner_pattern.md](../engineering/runner_pattern.md) — Effect runner contract
- [engineering/generated_code_validation.md](../engineering/generated_code_validation.md) — Code generation validation
