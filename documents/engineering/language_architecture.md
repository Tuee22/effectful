# Language Topology: Haskell, Rust, and Legacy Systems

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: architecture.md, dsl/intro.md, boundary_model.md

> **Purpose**: Document the multi-language architecture of Effectful, including the roles of Haskell (core logic), Rust (systems layer), and legacy Python/TypeScript (transitional).

______________________________________________________________________

## SSoT Link Map

| Need                | Link                                 |
| ------------------- | ------------------------------------ |
| Effectful overview  | [Effectful DSL Hub](../dsl/intro.md) |
| Boundary model      | [Boundary Model](boundary_model.md)  |
| JIT compilation     | [JIT Compilation](../dsl/jit.md)     |
| Runner pattern      | [Runner Pattern](runner_pattern.md)  |
| System architecture | [Architecture](architecture.md)      |

______________________________________________________________________

## 1. Language Roles

### 1.1 Overview

Effectful uses multiple languages, each optimized for its role:

| Language   | Role                          | Boundary        |
| ---------- | ----------------------------- | --------------- |
| Haskell    | Core logic, DSL, compiler     | Purity boundary |
| Rust       | Systems layer, effect runners | Proof boundary  |
| TLA+       | Formal specification          | Proof boundary  |
| Python     | Legacy effectful library      | Transitional    |
| TypeScript | Legacy frontend               | Transitional    |

### 1.2 The Design Principle

**Use the right language for each boundary**:

- Purity boundary needs pure functional programming → Haskell
- Proof boundary needs memory safety without GC → Rust
- Specification needs temporal logic → TLA+
- Legacy systems use existing languages → Python/TypeScript

______________________________________________________________________

## 2. Haskell Core Logic

### 2.1 What Haskell Does

Haskell is responsible for:

| Component               | Purpose                                      |
| ----------------------- | -------------------------------------------- |
| **DSL**                 | High-level language for distributed systems  |
| **Compiler**            | Parse, type-check, optimize, generate        |
| **Compute Graph**       | Represent entire distributed computation     |
| **Optimizer**           | Fusion, placement, batching, parallelization |
| **Effect Descriptions** | Pure values describing what to do            |
| **Type Checker**        | Ensure security and consistency constraints  |

### 2.2 Why Haskell

Haskell's features align with purity boundary requirements:

| Feature                  | Benefit                                        |
| ------------------------ | ---------------------------------------------- |
| **Pure by default**      | Effects are explicit, reasoning is tractable   |
| **Lazy evaluation**      | Compute graphs can be built incrementally      |
| **Strong types**         | Catch errors at compile time                   |
| **Algebraic data types** | Natural representation for effects and state   |
| **Type classes**         | Extensible optimization strategies             |
| **GHC optimizer**        | Already excellent at fusion and specialization |

### 2.3 Haskell's Limitations

Why Haskell can't do everything:

| Limitation             | Impact                         |
| ---------------------- | ------------------------------ |
| **Garbage collection** | Unpredictable latency spikes   |
| **Runtime overhead**   | Lazy thunks have cost          |
| **C FFI friction**     | Calling drivers is cumbersome  |
| **Memory layout**      | No control over struct packing |

These limitations are handled by Rust.

______________________________________________________________________

## 3. Rust Systems Layer

### 3.1 What Rust Does

Rust is responsible for:

| Component               | Purpose                               |
| ----------------------- | ------------------------------------- |
| **Effect Runners**      | Execute pure effect descriptions      |
| **Driver Integration**  | Communicate with hardware and OS      |
| **Performance Code**    | Latency-critical paths                |
| **JIT Target**          | Generated code from Haskell optimizer |
| **Resource Management** | Bounded memory, timeouts              |

### 3.2 Why Rust

Rust's features align with proof boundary requirements:

| Feature                    | Benefit                                  |
| -------------------------- | ---------------------------------------- |
| **No GC**                  | Predictable latency                      |
| **Memory safety**          | No use-after-free, no data races         |
| **C FFI**                  | Direct driver integration                |
| **Zero-cost abstractions** | High-level code, low-level performance   |
| **Ownership system**       | Resource management without runtime cost |
| **Compile-time checks**    | Many errors caught before runtime        |

### 3.3 Rust's Role in Verification

Rust code is verifiable because:

1. **Safe Rust** provides memory safety guarantees
1. **Conformance tests** ensure Rust matches TLA+ specs
1. **Typed errors** make failure handling exhaustive
1. **Resource bounds** are enforced at compile time

### 3.4 Unsafe Rust Policy

Unsafe Rust is permitted only when:

1. Safe Rust cannot achieve required performance
1. The unsafe block is documented as an assumption
1. The code is reviewed and approved explicitly

See [jit.md](../dsl/jit.md#4-jit-code-generation-rules) for documentation requirements.

______________________________________________________________________

## 4. TLA+ Specification

### 4.1 What TLA+ Does

TLA+ is responsible for:

| Component               | Purpose                          |
| ----------------------- | -------------------------------- |
| **State Machines**      | Formal protocol definitions      |
| **Invariants**          | Properties that must always hold |
| **Temporal Properties** | Liveness and fairness            |
| **Model Checking**      | Exhaustive state exploration     |

### 4.2 Why TLA+

TLA+ is the industry standard for distributed systems verification:

| Feature                       | Benefit                                   |
| ----------------------------- | ----------------------------------------- |
| **Temporal Logic of Actions** | Precise semantics for state transitions   |
| **TLC Model Checker**         | Exhaustive verification up to bounds      |
| **TLAPS Prover**              | Machine-checked proofs when needed        |
| **Industry Adoption**         | Amazon, Microsoft, others use it          |
| **Lamport's Authority**       | Designed by the Byzantine Generals author |

### 4.3 What TLA+ Verifies

TLA+ verifies properties of protocols:

- **Safety**: Bad things never happen
- **Liveness**: Good things eventually happen
- **Invariants**: State predicates that always hold
- **Refinement**: Implementation matches specification

TLA+ does NOT verify:

- Code correctness (that's what conformance tests do)
- Hardware behavior (that's an assumption)
- Driver correctness (that's an assumption)

______________________________________________________________________

## 5. Legacy Python (Transitional)

### 5.1 Current State

The existing effectful Python library provides:

| Component            | Purpose                                 |
| -------------------- | --------------------------------------- |
| **Effect Types**     | ADTs for effects (Result, Option, etc.) |
| **Runners**          | Async effect execution                  |
| **Interpreters**     | Effect orchestration                    |
| **Type Annotations** | MyPy-checked type safety                |

### 5.2 Migration Path

Python code migrates to Haskell/Rust:

| Python Component    | Migration Target  |
| ------------------- | ----------------- |
| Pure business logic | Haskell DSL       |
| Effect runners      | Rust runners      |
| Type definitions    | Haskell ADTs      |
| Integration tests   | Conformance tests |

### 5.3 Coexistence Strategy

During transition:

1. **New logic** goes in Haskell
1. **New runners** go in Rust
1. **Existing code** continues working
1. **Migration** happens incrementally per module

______________________________________________________________________

## 6. Legacy TypeScript (Transitional)

### 6.1 Current State

TypeScript is used for:

| Component            | Purpose                   |
| -------------------- | ------------------------- |
| **Frontend UI**      | React/web components      |
| **API Clients**      | HTTP/WebSocket clients    |
| **Type Definitions** | Shared types with backend |

### 6.2 Migration Path

TypeScript migrates to Effectful's compute graph:

| TypeScript Component | Migration Target                     |
| -------------------- | ------------------------------------ |
| UI logic             | Haskell DSL (compiled to WASM or JS) |
| API calls            | Effect descriptions                  |
| State management     | Distributed state machines           |

### 6.3 Frontend Strategy

Effectful's vision eliminates frontend/backend distinction:

1. **Logic lives in Haskell** (the purity boundary)
1. **Optimizer decides placement** (edge vs server)
1. **UI is generated** from component descriptions
1. **No separate frontend framework** needed

______________________________________________________________________

## 7. Effect Runners Across Languages

### 7.1 The Universal Contract

Effect runners share semantics across languages:

```text
                     ┌─────────────────────┐
                     │  Effect Description │
                     │   (Pure Value)      │
                     └──────────┬──────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Rust Runner   │   │  Python Runner  │   │    TS Runner    │
│  (Primary)      │   │  (Legacy)       │   │  (Legacy)       │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                               ▼
                     ┌─────────────────────┐
                     │   Same Real-World   │
                     │     Operation       │
                     └─────────────────────┘
```

### 7.2 Semantic Equivalence

All runners for the same effect type must produce the same result:

- **Same SQL query** → Same database rows
- **Same HTTP request** → Same response (modulo timing)
- **Same file operation** → Same file changes

This enables migration without behavior changes.

______________________________________________________________________

## 8. Compilation Pipeline

### 8.1 End-to-End Flow

```mermaid
┌─────────────────────────────────────────────────────────────┐
│                      HASKELL                                │
│  Source DSL → Parse → Type Check → Build Graph → Optimize  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    TLA+ VERIFICATION                        │
│  Extract Protocol → Model Check → Generate Conformance      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      RUST CODEGEN                           │
│  Effect IR → Static Rust OR JIT → Compile → Link            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT                              │
│  Edge Binary, Server Binary, WASM Module                    │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Output Artifacts

| Artifact              | Purpose                        |
| --------------------- | ------------------------------ |
| **Edge Binary**       | Runs on user devices           |
| **Server Binary**     | Runs on infrastructure         |
| **WASM Module**       | Runs in browsers               |
| **TLA+ Spec**         | Documentation and verification |
| **Conformance Tests** | Validate implementations       |

______________________________________________________________________

## 9. When to Use Each Language

### 9.1 Decision Framework

| Task               | Language       | Reason                      |
| ------------------ | -------------- | --------------------------- |
| Business logic     | Haskell        | Purity, types, optimization |
| Protocol design    | TLA+           | Formal verification         |
| Effect execution   | Rust           | Performance, drivers        |
| Legacy integration | Python/TS      | Compatibility               |
| UI components      | Haskell → WASM | Unified logic               |

### 9.2 Anti-Patterns

| Anti-Pattern              | Problem                          | Fix              |
| ------------------------- | -------------------------------- | ---------------- |
| Business logic in Rust    | Loses purity, harder to optimize | Move to Haskell  |
| Driver calls from Haskell | FFI overhead, GC pauses          | Use Rust runner  |
| Unspecified protocols     | No formal verification           | Add TLA+ spec    |
| New code in Python        | Delays migration                 | Start in Haskell |

______________________________________________________________________

## Cross-References

- [dsl/intro.md](../dsl/intro.md) — Effectful language overview
- [dsl/jit.md](../dsl/jit.md) — JIT compilation standards
- [boundary_model.md](boundary_model.md) — Boundary definitions
- [runner_pattern.md](runner_pattern.md) — Effect runner contract
- [architecture.md](architecture.md) — System architecture
- [verification_contract.md](verification_contract.md) — TLA+ workflow
