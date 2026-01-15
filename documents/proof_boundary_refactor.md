# Expansive Refactoring Plan: Proof Boundary and Purity Boundary Framework

**Status**: Reference only
**Supersedes**: none
**Referenced by**: none

> **Purpose**: Comprehensive plan to refactor the entire documentation suite to reflect the new formal methods framework with explicit Proof Boundary and Purity Boundary concepts, pivoting from the Python-centric "effectful library" model to "Effectful Language" — a high-level programming language for provably correct distributed systems.
> **Authoritative Reference**: [DSL Intro](dsl/intro.md)

______________________________________________________________________

## Central Theme

**Effectful is a high-level application language for writing high-quality UX and software, where everything is modeled as an abstract distributed system with a global interpreter of pure effects.**

This single unifying idea drives all documentation:

- Effects are pure types; effect interpreters run them on "nodes"
- A node is either a user-facing UI or a server—internally safe and trusted
- All communication into/out of nodes is modeled as Paxos messages
- One language for UI, server logic, and infrastructure deployment
- The two-stage Haskell→Rust effect interpreter is the purity boundary
- Purity means correctness is self-verifying: a GHC-built Haskell binary is a self-verified effect system

______________________________________________________________________

## Table of Contents

1. [Why Effectful Exists](#why-effectful-exists)
1. [The New Conceptual Framework](#the-new-conceptual-framework)
1. [Scope of Changes](#scope-of-changes)
1. [Phase 1: DSL Foundation](#phase-1-dsl-foundation)
1. [Phase 2: Engineering Standards](#phase-2-engineering-standards)
1. [Phase 3: Tutorials and API](#phase-3-tutorials-and-api)
1. [Phase 4: Demo and Product Docs](#phase-4-demo-and-product-docs)
1. [Phase 5: Validation](#phase-5-validation)
1. [Phase 6: Unified Node Model and Infrastructure Deployment](#phase-6-unified-node-model-and-infrastructure-deployment)
1. [Phase 7: Effect Interpreter Architecture](#phase-7-effect-interpreter-architecture)
1. [Implementation Sequence](#implementation-sequence)
1. [Validation Checklist](#validation-checklist)

______________________________________________________________________

## Why Effectful Exists

**Effectful is a high-level, all-purpose programming language for distributed systems based on formal methods.** Our formal methods are inspired by the work of Leslie Lamport—the Byzantine Generals paper, the Paxos distributed consensus protocol, and the TLA+ specification language.

### The Problem: Distributed Systems Are Impossibly Hard

Major cloud providers (AWS, GCP, Azure) solve incredibly difficult distributed consensus problems so developers don't have to. They offer cloud products with simple APIs that have massive horizontal scaling built on proprietary algorithms. Their consensus protocols perform distributed operations at scale that would be **impossible to implement correctly without formal proofs** (see [proof_boundary.md](dsl/proof_boundary.md)).

Consider apps with complex distributed backends: large online retailers, ride-sharing platforms, major social media networks. Non-technical users interact with these apps daily, vaguely aware they require large teams and millions of dollars annually to operate—but they don't understand *why*. The reasons are explored in [proof_boundary.md](dsl/proof_boundary.md).

### The Opportunity: Moving the Proof Boundary for the LLM Era

Effectful is built on a core belief: **empowering non-technical people to successfully "vibe code" requires moving the proof boundary.**

In the pre-LLM era, formal software methods were a niche concern. But as argued in [proof_boundary.md](dsl/proof_boundary.md), shifting to formal methods allows humans to move the proof boundary outward, **unlocking the expressive power of LLMs to create distributed systems with formal guarantees**.

This is why the world needs another high-level programming language: **none have put provably correct distributed systems at their core.**

### Effectful's Approach

1. **Single Pure DSL**: All business logic for distributed systems (edge devices and servers) expressed in a single pure Haskell-derived DSL. No traditional frameworks (web backends, secrets stores, ML libraries).

1. **Distributed Compute Graph Optimization**: The distinction between frontend and backend becomes obsolete. Logic is freely optimized to execute where it is safe and permissioned to do so.

1. **Pure Security Model**: A rich, purely representable security model makes it impossible to represent insecure states. This is a message-based abstraction layer above transport security (TCP/UDP with SSL). In Effectful's model:

   - **Two node types**: Edge devices and servers reachable over public APIs
   - **Byzantine messaging system**: Expressive threat modelling replaces traditional firewalls *within the purity boundary*
   - (This complements—not replaces—industry-standard firewalls, ingress controls, certificates, and web protocols)

1. **Compiler as Proof**: If the compiler succeeds (itself written in Haskell), you've followed the language's rules. This gives LLMs the signal needed to write **provably correct distributed system code** for specific applications.

1. **Impossible to Represent Unsafe States**: Effectful must make it impossible to represent states that are unsafe according to the pure threat model and which TLA+ cannot prove.

______________________________________________________________________

## The New Conceptual Framework

### Proof Boundary and Purity Boundary (Nested Model)

Replace the 5-tier taxonomy and 5-layer architecture with a nested boundary model:

```mermaid
┌─────────────────────────────────────────────────────────────────────────┐
│                     OUTSIDE PROOF BOUNDARY                               │
│  Device drivers, proprietary APIs (iOS ARKit, CUDA, etc.), hardware      │
│  Assumptions documented explicitly; TLA+ proofs depend on them           │
│  (These assumptions may be wrong—they can never be proven)               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PROOF BOUNDARY                                    │
│  TLA+ specifications, invariants, temporal properties                    │
│  Rust lives here: imperative, inside proof boundary, outside purity      │
│  Communicates with drivers/APIs; receives marching orders from Haskell   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       PURITY BOUNDARY                                    │
│  Haskell core logic with distributed compute graph optimization          │
│  Pure functional, deterministic, exhaustively testable                   │
│  Composes with distributed consensus state machines                      │
│  Byzantine security model replaces firewalls within this layer           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why This Layering?

**Where we put the proof boundary is always a subjective human decision.** Effectful puts the proof boundary at the **driver level**:

- **Outside proof boundary**: Device drivers, OS APIs, proprietary software (ARKit, CUDA, etc.)
- **Inside proof boundary, outside purity boundary**: Rust code that communicates with drivers
- **Inside purity boundary**: Haskell DSL expressing all distributed system logic

### Why Haskell + Rust?

**Haskell** is ideal for:

- Compute graph optimization
- Pure expression of distributed system effects
- Giving Rust its "marching orders" as pure effect descriptions

**Rust** is necessary because:

- Effectful avoids most existing software frameworks (they're not formally checked)
- The proof boundary cannot be pushed past unchecked frameworks
- Rust communicates directly with device drivers and "must-use" APIs
- For performance (especially tail latency), Haskell is a poor choice for systems-level work
- Custom effects may be JIT'd in Rust for performance

### Assumption Documentation

When Rust code communicates with something outside the proof boundary:

1. **State assumptions explicitly** about the driver/API behavior
1. **TLA+ proofs are based on these assumptions** (right or wrong)
1. **There is never a way to prove assumptions are correct**—they live outside the proof boundary

### Unsafe Rust Policy

Unsafe Rust is permitted ONLY when:

1. Performance cannot be achieved via Haskell compute graph JIT optimization
1. The unsafe code is explicitly documented as an **unprovable assumption**
1. The unsafe code effectively lives **outside the proof boundary** for that operation

______________________________________________________________________

## Scope of Changes

### Documentation Inventory

| Directory                | Files   | Current State                        | Required Changes                |
| ------------------------ | ------- | ------------------------------------ | ------------------------------- |
| `documents/dsl/`         | 4 → 5   | TPM doctrine, 5-tier taxonomy        | Major rewrite + new jit.md      |
| `documents/engineering/` | 24 → 31 | 5-layer architecture, Python-centric | 7 new docs + major updates      |
| `documents/tutorials/`   | 29      | Python effectful library             | Add legacy notices, link to DSL |
| `documents/api/`         | 10      | Python library reference             | Add legacy notices              |
| `documents/domain/`      | 3       | Medical state machines               | Stable (no changes)             |
| `documents/product/`     | 10      | HealthHub Python demo                | Add legacy transition path      |
| `documents/` (root)      | 5       | Standards, contributing              | Minor updates                   |

### Key Terminology Changes

| Term                   | Old Usage                       | New Usage                                |
| ---------------------- | ------------------------------- | ---------------------------------------- |
| "effectful"            | Python effect system library    | Effectful Language (Haskell-derived DSL) |
| "5-tier taxonomy"      | Tier 0-5 for Python/TS code gen | Replaced by proof/purity boundaries      |
| "5-layer architecture" | Layer 1-5 Python execution      | Reframed within boundary model           |
| "Total Pure Modelling" | Standalone doctrine             | Foundation within purity boundary        |
| "Proof Boundary"       | Philosophical essay             | Core architectural concept               |
| "Purity Boundary"      | Not documented                  | New core concept                         |
| "Runner"               | Python interpreter              | Rust code inside proof boundary          |

______________________________________________________________________

## Phase 1: DSL Foundation

### 1.1 intro.md — COMPLETE REWRITE (Hub Document)

**New Title**: `Effectful: A Formally Verified Language for Distributed Systems`

**New Header:**

```markdown
# Effectful: A Formally Verified Language for Distributed Systems

**Status**: Authoritative source
**Supersedes**: effectual_dsl_and_effectful_compiler_spec_final.md
**Referenced by**: ml_training.md, consensus.md, jit.md, engineering/architecture.md

> **Purpose**: Define Effectful, a high-level programming language for distributed systems based on formal methods. Effectful makes it possible to express complex distributed systems in a single pure Haskell-derived DSL, using distributed compute graph optimization to make frontend/backend distinctions obsolete, with a Byzantine security model that makes unsafe states unrepresentable.
```

**New Structure:**

1. **SSoT Link Map**
1. **Document Navigation Table** (DSL documentation index)
1. **Why Effectful Exists**
   - The problem: distributed systems are impossibly hard
   - The opportunity: moving the proof boundary for the LLM era
   - Why the world needs another language
   - Link to proof_boundary.md for philosophical foundation
1. **The Proof Boundary and Purity Boundary**
   - Outside proof boundary: drivers, proprietary APIs, assumptions
   - Proof boundary: TLA+ specs, Rust code
   - Purity boundary: Haskell DSL, Byzantine security model
   - Why this layering matters
   - Canonical BoundaryModel diagram
1. **Effectful's Architecture**
   - Single pure DSL for all distributed logic
   - Distributed compute graph optimization
   - Pure security model (Byzantine messaging)
   - Compiler as proof
1. **The Haskell + Rust Story**
   - Why Haskell: compute graph optimization, pure effect descriptions
   - Why Rust: driver communication, performance, systems-level work
   - JIT compilation from Haskell to Rust (link to jit.md)
1. **Assumption Documentation**
   - How to document assumptions about things outside proof boundary
   - TLA+ proofs depend on these assumptions
   - Assumptions can never be proven correct
1. **TLA+ Integration**
   - Specification patterns
   - Leslie Lamport's influence (Byzantine Generals, Paxos, TLA+)
1. **Consolidated References Section**
   - Formal Methods References
   - Consensus Protocol References
   - TLA+ Resources
   - Haskell/Rust Compilation References
   - GPU and Hardware References
1. **Cross-References Section**

**Content to REMOVE:**

- Section 1: Total Pure Modelling (TPM) doctrine — move to engineering/total_pure_modelling.md context
- Section 3: Tier Taxonomy (Tier 0-5) — replaced by boundary model
- Python/TypeScript effect runner sketches — not relevant to Haskell/Rust model

**Content to RETAIN (reframed):**

- TLA+/PlusCal concepts → TLA+ Integration section
- ADT patterns → Haskell type system context
- Effect patterns → boundary context

______________________________________________________________________

### 1.2 jit.md — CREATE NEW

**Header:**

```markdown
# JIT Compilation: Haskell Compute Graph to Rust

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: intro.md, ml_training.md, engineering/architecture.md

> **Purpose**: Define rules, standards, and verification requirements for JIT compilation from Haskell compute graphs to Rust code. Haskell excels at compute graph optimization and gives Rust its "marching orders" as pure effects. Rust, being imperative, lives outside the purity boundary but inside the proof boundary.
```

**Structure:**

1. **SSoT Link Map**
1. **Why JIT from Haskell to Rust**
   - Haskell's strength: compute graph optimization, pure effect descriptions
   - Rust's necessity: tail latency, systems-level work, driver communication
   - Haskell gives Rust "marching orders" as pure effects
   - Rust lives outside purity boundary but INSIDE proof boundary
1. **The Boundary Model in JIT**
   - Purity boundary: Haskell compute graph (pure, optimizable)
   - Proof boundary: Generated Rust (imperative, verified against TLA+)
   - Outside proof boundary: Drivers, APIs Rust communicates with
1. **Haskell Compute Graph Optimization**
   - Graph representation
   - Optimization passes (fusion, vectorization, memory planning)
   - Semantic preservation guarantees
   - Why Haskell is well-suited (but poor for systems-level execution)
1. **JIT Code Generation Rules** (HARD REQUIREMENTS)
   - **MUST**: Deterministic generation
   - **MUST**: Semantic preservation
   - **MUST**: Footprint compliance (no access beyond declared read/write sets)
   - **MUST**: Error mapping to typed Result variants
   - **SAFE RUST BY DEFAULT**: Generated code uses safe Rust
   - **UNSAFE PERMITTED** only when:
     a) Performance cannot be achieved via Haskell compute graph JIT optimization
     b) The unsafe block is documented as an **unprovable assumption**
     c) The unsafe code effectively lives **outside the proof boundary**
1. **TLA+ Verification at Proof Boundary**
   - Assumption inventory template for JIT-generated code
   - What TLA+ proves (optimizer transformation, footprint compliance, safe Rust behavior)
   - What TLA+ cannot prove (Rust compiler correctness, hardware, unsafe blocks, drivers)
   - How unsafe blocks are documented as assumptions
1. **Communicating with Drivers and APIs**
   - Rust's role: bridge between proof boundary and external world
   - Documenting assumptions about driver/API behavior
   - These assumptions can never be proven
1. **Static vs JIT Decision Framework**
   - When to use static Rust: hand-optimized code, unsafe blocks, known patterns
   - When to use JIT: dynamic structures, fusion opportunities, whole-program optimization
1. **Error Handling**
   - Compile-time errors
   - Runtime errors (all via Result, no panics in generated code)
1. **Canonical Diagrams** (for Functional Catalogue)
   - JitError ADT
   - JitCodeLifecycle state machine
1. **Cross-References Section**

______________________________________________________________________

### 1.3 ml_training.md — UPDATE METADATA + FRAMING

**New Header:**

```markdown
# Formal Methods Playbook for Reproducible Distributed ML Workflows

**Status**: Reference only
**Supersedes**: none
**Referenced by**: intro.md

> **Purpose**: Apply the proof boundary and purity boundary framework to distributed ML training on GPUs, defining proof boundaries for reproducibility and hardware execution.
> **Authoritative Reference**: [Effectful DSL Hub](intro.md#references)
```

**Changes:**

1. Add new Section 0: "ML Training in the Boundary Model"
   - Proof boundary: determinism contracts, checkpoint protocols
   - Purity boundary: DAG construction, scheduler logic (Haskell)
   - Outside proof boundary: CUDA kernels, GPU drivers (Rust/assumptions)
1. **REMOVE**: `## References` section — move to intro.md
1. **ADD**: Reference callouts linking to `intro.md#references`
1. Reframe existing proof boundary content to align with new terminology

______________________________________________________________________

### 1.4 consensus.md — UPDATE METADATA + FRAMING

**New Header:**

```markdown
# Formal Methods for Distributed Consensus and Blockchains

**Status**: Reference only
**Supersedes**: none
**Referenced by**: intro.md

> **Purpose**: Apply the proof boundary and purity boundary framework to distributed consensus protocols, covering Paxos, PBFT, hybrid trust models, and DAG-based systems.
> **Authoritative Reference**: [Effectful DSL Hub](intro.md#references)
```

**Changes:**

1. Add new Section 0: "Consensus in the Boundary Model"
   - Proof boundary: safety/liveness properties, quorum intersection
   - Purity boundary: state machine logic, message handling (Haskell)
   - Outside proof boundary: network I/O, cryptographic operations (Rust)
1. **REMOVE**: `## References` and `## Source URLs` sections
1. **ADD**: Reference callouts to `intro.md#references`

______________________________________________________________________

### 1.5 proof_boundary.md — NO CHANGES

This document remains completely untouched:

- Self-contained philosophical essay
- Maintains own HTML anchor references
- Other documents link TO it but it does not link outside itself
- Document Navigation Table in intro.md explicitly notes this exception

______________________________________________________________________

## Phase 2: Engineering Standards

### 2.1 NEW DOCUMENTS TO CREATE

#### 2.1.1 boundary_model.md

**Title**: `Proof Boundary and Purity Boundary: Architectural Foundation`

**Purpose**: Define the two-boundary model that replaces the 5-layer/5-tier architecture.

**Content:**

1. The nested boundary model (diagram)
1. What lives at each boundary
1. Language assignment (Haskell = purity, Rust = proof boundary edge)
1. How existing "layers" map to boundaries
1. Relationship to TLA+ verification
1. Relationship to Total Pure Modelling (applies within purity boundary)

______________________________________________________________________

#### 2.1.2 language_architecture.md

**Title**: `Language Topology: Haskell, Rust, and Legacy Systems`

**Purpose**: Document the multi-language architecture.

**Content:**

1. Haskell core logic (compiler, DSL, compute graph optimization)
1. Rust systems layer (drivers, APIs, performance-critical paths)
1. Legacy Python/TypeScript (effectful library, transitional)
1. Effect runners across languages (same semantics, different implementations)
1. JIT compilation pipeline (Haskell → Rust)
1. When to use each language

______________________________________________________________________

#### 2.1.3 verification_contract.md

**Title**: `Formal Verification: TLA+ Model Checking and Conformance`

**Purpose**: Document how TLA+ integrates with the development workflow.

**Content:**

1. Proof boundary definition (where formal verification applies)
1. TLA+ properties to verify (Init, Next, TypeOK, Invariants)
1. TLC model checker integration
1. Conformance tests (generated code matches TLA+ spec)
1. Determinism gates (TLC → Generate → CheckNoDiff → Typecheck → Ship)
1. Cost/benefit of formal verification

______________________________________________________________________

#### 2.1.4 runner_pattern.md

**Title**: `Effect Runners: The Proof Boundary Edge`

**Purpose**: Define the contract for Rust code that bridges purity and hardware.

**Content:**

1. Runner = one impure function per effect type
1. Input: pure effect value only
1. Output: Result[OkT, ErrT] (no exceptions)
1. Dependency injection at construction
1. Timeout enforcement and cancellation
1. Error conversion (only place exceptions → Result)
1. Safe Rust by default; unsafe requires assumption documentation

______________________________________________________________________

#### 2.1.5 byzantine_security_model.md

**Title**: `Byzantine Security Model: Distributed Trust`

**Purpose**: Document the pure security model for distributed systems.

**Content:**

1. Byzantine Generals problem and its relevance
1. Two node types: edge devices and servers
1. Message-based security abstraction (above TCP/SSL)
1. Threat modelling as types (impossible to represent unsafe states)
1. Relationship to industry-standard security (complement, not replace)
1. ADT-based failure modes

______________________________________________________________________

#### 2.1.6 generated_code_validation.md

**Title**: `Code Generation Pipeline and Validation`

**Purpose**: Document how code is generated and validated.

**Content:**

1. Discovery (TLA+ models)
1. Verification (TLC model checker)
1. Generation (Haskell IR → Rust)
1. Fingerprinting (deterministic hash)
1. CheckNoDiff gate
1. CI/CD integration

______________________________________________________________________

#### 2.1.7 standard_effects.md

**Title**: `Standard Effect Library`

**Purpose**: Document language-agnostic standard effects.

**Content:**

1. Standard effects (DbQuery, HttpRequest, KvGet, KvSet, NowMs, RandomBytes, Log)
1. Why standard effects matter (minimize impure surface)
1. Domain effects (app-specific extensions)
1. Repository pattern (pure composition of standard effects)

______________________________________________________________________

### 2.2 EXISTING DOCUMENTS TO UPDATE

#### 2.2.1 architecture.md — MAJOR UPDATE

**Changes:**

1. **ADD** new section: "Boundary Model Overview" (link to boundary_model.md)
1. **REFRAME** 5-layer architecture as implementation detail within boundaries
1. **ADD** section: "Language Topology" (link to language_architecture.md)
1. **ADD** section: "Proof Boundary and Verification" (link to verification_contract.md)
1. **ADD** section: "Runner Contract" (link to runner_pattern.md)
1. **ADD** section: "Byzantine Security" (link to byzantine_security_model.md)
1. **UPDATE** Pure Interpreter Assembly Doctrine to reference boundary model
1. **UPDATE** Referenced by to include new documents

______________________________________________________________________

#### 2.2.2 code_quality.md — SIGNIFICANT UPDATE

**Changes:**

1. **ADD** Doctrine 9: "Runner Error Conversion" — runners are the only place exceptions become Result types
1. **ADD** Doctrine 10: "Deterministic Timeouts" — all runners have bounded execution time
1. **ADD** Doctrine 11: "Assumption Documentation" — unsafe code requires explicit assumptions
1. **CLARIFY** Type Safety Doctrines apply within purity boundary
1. **CLARIFY** Purity Doctrines define purity boundary edge
1. **ADD** section: "Boundary-Specific Quality Rules"
1. **EXPAND** Anti-Pattern Index to include boundary confusion patterns

______________________________________________________________________

#### 2.2.3 total_pure_modelling.md — CONTEXTUALIZE

**Changes:**

1. **ADD** section at top: "Relationship to Boundary Model"
   - TPM applies within purity boundary
   - Foundation for formal verification
   - Link to boundary_model.md
1. **ADD** section: "Byzantine Assumptions in Auth"
   - What fails if nodes can lie
   - Typed error ADTs for Byzantine failures
1. **RETAIN** all existing content (it's foundational)

______________________________________________________________________

#### 2.2.4 effect_patterns.md — EXPAND

**Changes:**

1. **ADD** section at top: "Standard vs Domain Effects"
1. **ADD** Pattern 7: "Pure Repository Pattern"
1. **ADD** Pattern 8: "Runner Implementation Pattern"
1. **LINK** to standard_effects.md and runner_pattern.md

______________________________________________________________________

#### 2.2.5 development_workflow.md — UPDATE

**Changes:**

1. **UPDATE** "Adding New Effects" to distinguish standard vs domain
1. **ADD** section: "Adding TLA+ Specifications"
1. **ADD** section: "Validating Generated Code"
1. **CLARIFY** which workflow steps apply to which boundary

______________________________________________________________________

#### 2.2.6 testing.md — EXPAND

**Changes:**

1. **ADD** section: "Boundary-Specific Testing Strategy"
   - Purity boundary: property-based testing, exhaustive
   - Proof boundary: conformance tests, TLA+ model checking
   - Outside proof boundary: integration tests, assumptions validated
1. **ADD** section: "Testing Generated vs Handwritten Code"

______________________________________________________________________

#### 2.2.7 testing_architecture.md — UPDATE

**Changes:**

1. **ADD** new test category: "Conformance Tests"
1. **UPDATE** fixture strategy for boundary-aware injection

______________________________________________________________________

#### 2.2.8 command_reference.md — EXPAND

**Changes:**

1. **ADD** TLA+ commands: model checking, invariant discovery
1. **ADD** code generation commands
1. **ADD** determinism check commands

______________________________________________________________________

#### 2.2.9 README.md (engineering/) — UPDATE

**Changes:**

1. **UPDATE** SSoT Link Map to include new documents
1. **ADD** "Boundary Model Overview" section
1. **UPDATE** navigation to reflect new structure

______________________________________________________________________

## Phase 3: Tutorials and API

### 3.1 tutorials/ — ADD LEGACY NOTICES

All 29 tutorial files need:

1. **ADD** notice at top:

   ```markdown
   > **Note**: This tutorial covers the legacy Python effectful library. For the Effectful Language (Haskell-derived DSL for distributed systems), see [DSL Documentation](../dsl/intro.md).
   ```

1. **RETAIN** all content (still valid for Python library users)

1. **ADD** link to migration path when available

______________________________________________________________________

### 3.2 api/ — ADD LEGACY NOTICES

All 10 API reference files need:

1. **ADD** notice at top:

   ```markdown
   > **Note**: This API reference covers the legacy Python effectful library. For the Effectful Language, see [DSL Documentation](../dsl/intro.md).
   ```

1. **RETAIN** all content

______________________________________________________________________

## Phase 4: Demo and Product Docs

### 4.1 demo/healthhub/ — ADD TRANSITION PATH

**Changes:**

1. **ADD** section to README: "Relationship to Effectful Language"
   - HealthHub demonstrates Python effectful library patterns
   - Patterns inform but don't constrain Effectful Language design
   - Future: HealthHub may be reimplemented in Effectful Language
1. **RETAIN** all existing content

______________________________________________________________________

### 4.2 product/ — ADD CONTEXT

**Changes:**

1. **ADD** notice explaining Python library context
1. **RETAIN** all content

______________________________________________________________________

## Phase 5: Validation

### 5.1 Documentation Standards Compliance

All new and updated documents must follow `documentation_standards.md`:

- Header metadata (Status, Supersedes, Referenced by, Purpose)
- SSoT Link Maps in hub documents
- Cross-References sections in authoritative documents
- Relative links with section anchors
- No external references in non-hub documents (link to intro.md#references)

### 5.2 Canonical Diagrams

New canonical diagrams for Functional Catalogue:

**In dsl/intro.md:**

```text
# example mermaid diagram (not canonical)
flowchart TB
  %% kind: ADT
  %% id: dsl.boundaries.BoundaryModel
  %% summary: Nested boundary model - proof boundary contains purity boundary
```

**In dsl/jit.md:**

```text
# example mermaid diagram (not canonical)
flowchart TB
  %% kind: ADT
  %% id: effectful.jit.JitError
  %% summary: JIT compilation and execution errors
```

```text
# example mermaid diagram (not canonical)
stateDiagram-v2
  %% kind: StateMachine
  %% id: effectful.jit.JitCodeLifecycle
  %% summary: JIT code from generation to execution
```

### 5.3 Cross-Reference Consistency

Verify bidirectional consistency:

- All "Referenced by" lists match actual references
- All links resolve to valid anchors
- No orphaned documents

### 5.4 proof_boundary.md Unchanged

**CRITICAL**: Verify `git diff documents/dsl/proof_boundary.md` shows no changes.

______________________________________________________________________

## Implementation Sequence

### Wave 1: DSL Foundation (Blocking)

1. Rewrite `dsl/intro.md` as boundary model hub
1. Create `dsl/jit.md` with JIT standards
1. Update `dsl/ml_training.md` header and framing
1. Update `dsl/consensus.md` header and framing
1. Verify `dsl/proof_boundary.md` unchanged

### Wave 2: Engineering Core (High Priority)

1. Create `engineering/boundary_model.md`
1. Create `engineering/language_architecture.md`
1. Create `engineering/verification_contract.md`
1. Create `engineering/runner_pattern.md`
1. Update `engineering/architecture.md`
1. Update `engineering/code_quality.md`

### Wave 3: Engineering Extended (Medium Priority)

1. Create `engineering/byzantine_security_model.md`
1. Create `engineering/generated_code_validation.md`
1. Create `engineering/standard_effects.md`
1. Update `engineering/total_pure_modelling.md`
1. Update `engineering/effect_patterns.md`
1. Update `engineering/development_workflow.md`

### Wave 4: Engineering Support (Lower Priority)

1. Update `engineering/testing.md`
1. Update `engineering/testing_architecture.md`
1. Update `engineering/command_reference.md`
1. Update `engineering/README.md`

### Wave 5: Legacy Documentation (Parallel)

1. Add legacy notices to all `tutorials/` files
1. Add legacy notices to all `api/` files
1. Update `demo/healthhub/` context
1. Update `product/` context

### Wave 6: Validation (Final)

1. Run `poetry run check-code`
1. Verify Functional Catalogue discovers new diagrams
1. Verify all cross-references
1. Final review of proof_boundary.md unchanged

______________________________________________________________________

## Validation Checklist

### DSL Documents

- [ ] `dsl/intro.md` has `**Status**: Authoritative source`
- [ ] `dsl/intro.md` has SSoT Link Map
- [ ] `dsl/intro.md` has Document Navigation Table
- [ ] `dsl/intro.md` has consolidated References section
- [ ] `dsl/intro.md` has Cross-References section
- [ ] `dsl/intro.md` does NOT contain TPM doctrine or 5-tier taxonomy
- [ ] `dsl/intro.md` has BoundaryModel canonical diagram
- [ ] `dsl/jit.md` has `**Status**: Authoritative source`
- [ ] `dsl/jit.md` has unsafe Rust policy documented
- [ ] `dsl/jit.md` has JitError and JitCodeLifecycle canonical diagrams
- [ ] `dsl/ml_training.md` has `**Status**: Reference only`
- [ ] `dsl/ml_training.md` has Authoritative Reference line
- [ ] `dsl/ml_training.md` has NO standalone References section
- [ ] `dsl/consensus.md` has `**Status**: Reference only`
- [ ] `dsl/consensus.md` has Authoritative Reference line
- [ ] `dsl/consensus.md` has NO standalone References or Source URLs
- [ ] `dsl/proof_boundary.md` is COMPLETELY UNCHANGED

### Engineering Documents

- [ ] `engineering/boundary_model.md` created with proper header
- [ ] `engineering/language_architecture.md` created with proper header
- [ ] `engineering/verification_contract.md` created with proper header
- [ ] `engineering/runner_pattern.md` created with proper header
- [ ] `engineering/byzantine_security_model.md` created with proper header
- [ ] `engineering/generated_code_validation.md` created with proper header
- [ ] `engineering/standard_effects.md` created with proper header
- [ ] `engineering/architecture.md` references boundary model
- [ ] `engineering/code_quality.md` has Doctrines 9-11
- [ ] `engineering/total_pure_modelling.md` contextualized within boundary model
- [ ] `engineering/README.md` updated with new SSoT links

### Legacy Documents

- [ ] All `tutorials/` files have legacy notice
- [ ] All `api/` files have legacy notice
- [ ] `demo/healthhub/` has transition context

### Validation

- [ ] All `Referenced by` lists are bidirectionally consistent
- [ ] `poetry run check-code` exits 0
- [ ] Functional Catalogue discovers new canonical diagrams

______________________________________________________________________

## Critical Files Summary

| File                                                 | Action                  | Wave |
| ---------------------------------------------------- | ----------------------- | ---- |
| `documents/dsl/intro.md`                             | Complete rewrite        | 1    |
| `documents/dsl/jit.md`                               | Create new              | 1    |
| `documents/dsl/ml_training.md`                       | Update header + framing | 1    |
| `documents/dsl/consensus.md`                         | Update header + framing | 1    |
| `documents/dsl/proof_boundary.md`                    | NO CHANGES              | 1    |
| `documents/engineering/boundary_model.md`            | Create new              | 2    |
| `documents/engineering/language_architecture.md`     | Create new              | 2    |
| `documents/engineering/verification_contract.md`     | Create new              | 2    |
| `documents/engineering/runner_pattern.md`            | Create new              | 2    |
| `documents/engineering/architecture.md`              | Major update            | 2    |
| `documents/engineering/code_quality.md`              | Significant update      | 2    |
| `documents/engineering/byzantine_security_model.md`  | Create new              | 3    |
| `documents/engineering/generated_code_validation.md` | Create new              | 3    |
| `documents/engineering/standard_effects.md`          | Create new              | 3    |
| `documents/engineering/total_pure_modelling.md`      | Contextualize           | 3    |
| `documents/engineering/effect_patterns.md`           | Expand                  | 3    |
| `documents/engineering/development_workflow.md`      | Update                  | 3    |
| `documents/engineering/testing.md`                   | Expand                  | 4    |
| `documents/engineering/testing_architecture.md`      | Update                  | 4    |
| `documents/engineering/command_reference.md`         | Expand                  | 4    |
| `documents/engineering/README.md`                    | Update                  | 4    |
| `documents/tutorials/*.md` (29 files)                | Add legacy notice       | 5    |
| `documents/api/*.md` (10 files)                      | Add legacy notice       | 5    |

______________________________________________________________________

## Estimated Scope

- **New documents**: 7 (engineering)
- **Major rewrites**: 2 (dsl/intro.md, dsl/jit.md)
- **Significant updates**: 8 (engineering core)
- **Minor updates**: 6 (engineering support)
- **Legacy notices**: 39 (tutorials + api)
- **Unchanged**: 1 (dsl/proof_boundary.md) + 3 (domain/) + others

**Total files affected**: ~60 of 84 markdown files

______________________________________________________________________

## Phase 6: Unified Node Model and Infrastructure Deployment

### 6.1 NEW DOCUMENT: `dsl/infrastructure_deployment.md`

**Title**: `Infrastructure Deployment: Nodes, Messages, and Pure Effects`

**Header:**

```markdown
# Infrastructure Deployment: Nodes, Messages, and Pure Effects

**Status**: Reference only
**Supersedes**: none
**Referenced by**: intro.md

> **Purpose**: Define Effectful's unified model for distributed systems where nodes (UI or server) communicate via Paxos messages, with infrastructure deployment as just another effect in the pure language.
```

**Structure:**

#### Section 1: The Effectful Model: One Language, One Distributed System

**Content:**

- Effectful is a high-level application language for UI and server logic
- Everything is modeled as an abstract distributed system
- Global interpreter of pure effects runs on "nodes"
- **A node is either a user-facing UI or a server**—both are internally-safe, trusted zones
- All communication into/out of nodes is modeled abstractly as Paxos messages
- This is the same language for:
  - User interfaces (via peripheral I/O effects)
  - Server logic
  - Event-driven infrastructure deployment rules

#### Section 2: Nodes: The Abstract Device Representation

**Content:**

- A node is an abstract representation of a device
- Two types: UI-facing or server
- Internally safe and trusted zone
- Transport topology differs (DNS, ingress, certificates, cookies) but behind the purity boundary all nodes are uniform
- The sole requirement to run an Effectful node:
  - a) Can deploy a binary built in Haskell/Rust
  - b) Rust can talk to device drivers for hardware and/or platform-native APIs

#### Section 3: The Whitelist Security Model

**Content:**

- Robust, expressive whitelist-based security runs compositionally throughout pure logic
- Each time a pure function returns a pure type, that type must be an instance of a whitelist monad
- The whitelist monad contains a new whitelist (itself a monadic functor representing security logic)
- Empty lists are valid and the default (monadic unit)
- Empty list = data may not be sent outside the node
- Non-empty whitelist = names of other nodes in an abstract namespace type (TBD)
- Each effect interpreter has a security contract: which messages may be sent to which node namespaces

#### Section 4: Haskell's Role: Thunk Performance Optimizer

**Content:**

- **Haskell's main job is thunk performance optimization** according to rules in Dhall config
- Dhall config modeled as a pure type (in Python for current implementation)
- Config addresses questions like: is a compiler assumed when none is available?
  - No compiler available → immediate `Error(E)`
  - No compiler → locked into explicit, finite list of Rust effects
- Haskell passes thunks that are async bundles of abstract effects
- Monads heavily utilized for:
  - Expressing arbitrary pure compute graphs
  - Security whitelist monad
  - Effect timeout wrappers (explicit timeout behavior, can optionally return `Success(T)`)
- **Every thunk is a pure representation of effects**, assembled by Haskell

#### Section 5: The Purity Boundary: Memory Semantics and Foreign Call Contract

**Content:**

**Purity extends through generated Rust:**

- Because Rust code is Haskell-generated using a TLA+-verified transpiler, the purity boundary continues through the shared immutable memory contract
- This is not a "break" in purity—it's a verified extension of it

**The Foreign Call Interface:**

- Explicit call function in Rust invoked via Haskell foreign call
- **Input**: Thunk type (referencing memory locations for thunk-scoped immutable store)
- **Output**: `Result[Future[T], E]` returned "immediately"
  - The Future may eventually point to memory Rust allocated
  - Rust surrenders ownership of this memory when/if `T` becomes available
  - Haskell's GC can then manage it

**Memory ownership model:**

- Haskell manages memory monadically via GC: allocates for effects, frees after Rust utilizes
- Rust ingests "instances": named immutable dicts (best Rust idiom)
- Rust may return arbitrary data shapes using memory it allocates
- TLA+ formally proves representation is sufficient for our class of Haskell types
- Static `Result[T,E]` shapes: Haskell preallocates memory, Rust's borrowing manages it
- **Completely clean purity chain** runs through Haskell and Rust EI, up until side effects run
- **Purity means correctness is self-verifying**: a Haskell binary created via GHC is a self-verified effect system

**The Cancel Effect Monad:**

- Every effect must implement a monadic "cancel effect" command
- **Unit**: Provides a function that can be used to "interrupt" something we are awaiting on
- **Bind**: Represents the logic for composing cancellation—chains forward monadically
- Enables modelling of both hard cancels (immediate termination) and soft cancels (graceful shutdown)
- Parent effect cancellation propagates to child effects via bind

#### Section 6: The Two-Stage Effect Interpreter Architecture

**Content:**

- Haskell EI: parses Dhall config, launches effect interpreter, packages thunks
- Rust EI: processes effects concurrently, subscribes to FIFO-style effect queue from Haskell
- Can be built inside other binaries (WASM in browser, edge devices)
- **The thunk pipeline flowing out of Haskell is Effectful's formal purity boundary**
- The thunk pipeline is safe and trusted

#### Section 7: Transport Layer and Network Interface

**Content:**

- Transport layer not explicitly modeled
- Network interface is at the proof boundary
- Rust interacts with network driver in course of interpreting its own effects
- Abstract message types map to real-world transport (TCP/UDP, REST/WebSockets)
- Generalized Paxos handles multiple message types (async, partially sync, sync)

#### Section 8: JIT and the Filesystem Model

**Content:**

- On nodes with compilers (servers), Haskell may write Rust implementations of thunks with additional logic
- Pure type representing filesystem: immutable but extendable (immutable hash table or similar)
- Rust responsible for JITs and caching them
- Between executing thunks, Rust essentially updates itself
- Shared immutable hash table as option for JIT cache
- **Server node definition**: can do JIT compilations

#### Section 9: Effects and Timeouts

**Content:**

- Effects are the pure language which crosses the purity boundary (but not necessarily proof boundary)
- All effects must have a "guaranteed finish time" at which point they logically return bottom
- If they return a timeout `Error(E)` result, they don't return bottom—this is explicit error handling
- This ensures liveness properties can be proven

#### Section 10: Browser and WASM Deployment

**Content:**

- Browser deployments don't use DOM or JS except thin boilerplate to download/install WASM SPA
- All rendering occurs in Rust as modeled effects (thunks from Haskell)
- If necessary: DOM harness receiving regular stream of immutable frames
- JS I/O modeled as events→effects via oracle pattern

#### Section 11: Domain-Specific Frameworks

**Content:**

- Domain-specific frameworks are Haskell libraries installed optionally
- Pure functional libraries translate higher-level abstractions for domain types
- Examples: web service abstractions, UI I/O abstractions
- Behaves collectively as distributed system based on Paxos consensus
- New APIs, device drivers, edge devices, or domain-specific UI frameworks extend via this pattern

#### Section 12: Infrastructure as Effects

**Content (conceptual, no code examples):**

- Infrastructure deployment is just another set of effects in the pure language
- SSH-based remote configurations modeled as effects
- REST API calls to cloud providers modeled as effects
- Security rules and secrets management as pure effects
- State tracking modeled as pure effects
- No third-party IAC tools (Terraform, Pulumi)—Effectful is self-sufficient

#### SSoT Link Map

````markdown
| Need | Link |
|------|------|
| Effectful overview | [Effectful DSL Hub](intro.md) |
| Boundary model | [Boundary Model](../engineering/boundary_model.md) |
| Consensus protocols | [Consensus](consensus.md) |
| JIT compilation | [JIT Compilation](jit.md) |
```mermaid

---

## Phase 7: Effect Interpreter Architecture

### 7.1 EXTEND `engineering/boundary_model.md` — New Section 8

**Title of New Section**: `Effect Interpreter Architecture and Language Boundaries`

Insert after Section 7 (Common Patterns), before Cross-References.

#### 8.1 The Purity Boundary is Always an Effect Interpreter

**Content:**
- In Effectful, the purity boundary is always an effect interpreter
- The reference effect interpreter implemented in Haskell is always available
- All (installed) effects can be interpreted there
- The main Haskell EI is a do statement that parses Dhall config and launches accordingly
- **Purity means correctness is self-verifying**: a Haskell binary created via GHC is a self-verified effect system

#### 8.2 Haskell's Role: Thunk Performance Optimizer

**Content:**
- **Haskell's main job is thunk performance optimization** according to Dhall config rules
- Dhall config modeled as pure type (Python for current implementation)
- Config addresses: is compiler assumed when none available?
  - No compiler → immediate `Error(E)`
  - No compiler → locked into explicit, finite list of Rust effects
- Haskell passes thunks as async bundles of abstract effects
- Monads heavily utilized for:
  - Arbitrary pure compute graphs
  - Security whitelist monad
  - Effect timeout wrappers (explicit timeout, can return `Success(T)`)
- **Every thunk is a pure representation of effects**

#### 8.3 The Purity Boundary: Memory Semantics and Foreign Call Contract

**Content:**

**Purity extends through generated Rust:**
- Because Rust code is Haskell-generated using a TLA+-verified transpiler, the purity boundary continues through the shared immutable memory contract
- This is not a "break" in purity—it's a verified extension of it

**The Foreign Call Interface:**
- Explicit call function in Rust invoked via Haskell foreign call
- **Input**: Thunk type (referencing memory locations for thunk-scoped immutable store)
- **Output**: `Result[Future[T], E]` returned "immediately"
  - The Future may eventually point to memory Rust allocated
  - Rust surrenders ownership of this memory when/if `T` becomes available
  - Haskell's GC can then manage it

**Memory ownership model:**
- Haskell manages memory monadically via GC: allocates for effects, frees after Rust utilizes
- Rust ingests "instances": named immutable dicts (best Rust idiom)
- Rust may return arbitrary data shapes using memory it allocates
- TLA+ formally proves representation is sufficient for our class of Haskell types
- Static `Result[T,E]` shapes: Haskell preallocates memory, Rust's borrowing manages it
- **Completely clean purity chain** through Haskell and Rust EI until side effects run

#### 8.3.1 The Cancel Effect Monad

**Content:**

Every effect must implement a monadic "cancel effect" command:

**Structure:**
- **Unit**: Provides a function that can be used to "interrupt" something we are awaiting on
- **Bind**: Represents the logic for composing cancellation—chains forward monadically
- This enables modelling of both hard and soft cancels

**Cancellation composition:**
- Hard cancel: Immediate termination, resources released
- Soft cancel: Graceful shutdown, allows cleanup
- The monadic structure allows these to compose naturally
- Parent effect cancellation propagates to child effects via bind

#### 8.4 The Two-Stage Effect Interpreter Architecture

**Content:**
- **Haskell EI**: Packages thunks, gives them to Rust as references to pure immutable types
- **Rust EI**: Processes effects concurrently, subscribes to FIFO-style effect queue
- Safe memory sharing: Rust can traverse Haskell's immutable data structures using its own model
- Immutability from the perspective of the thunk's lifetime
- **The thunk pipeline flowing out of Haskell is Effectful's formal purity boundary**

#### 8.5 Haskell and Rust Effect Interpreter Composition

**Content:**
- Effects can be marked for the Rust EI
- The Haskell EI can outsource effect running to other EIs
- A provably correct resource ownership contract between Haskell and Rust
- Rust's ownership model composes well with the Haskell EI

#### 8.6 Rust as Hardware Interface

**Content:**
- Rust's EI is the preferred way to interact with hardware (network adapters, all network I/O)
- Rust interacts with network driver in course of interpreting its own effects
- Rust is outside the purity boundary but inside the proof boundary

#### 8.7 Pure Work in Both Languages

**Content:**
- Both Haskell and Rust can do pure work on pure types using their respective idioms
- Haskell: lazy evaluation, algebraic data types, pattern matching
- Rust: zero-cost abstractions, ownership, iterators

#### 8.8 Haskell Compute Graph Optimizer and JIT

**Content:**
- On nodes with compilers, Haskell may write Rust implementations of thunks with additional logic
- Pure type representing filesystem: immutable but extendable
- Rust responsible for JITs and caching
- Between executing thunks, Rust essentially updates itself
- **Server node definition**: can do JIT compilations of generated Rust code

#### 8.9 Rust Code Generation Rules

**Content:**
- All Rust code that handles pure logic is to be generated by Haskell
- This is true for both static and JIT-compiled code
- Human-written Rust reserved for: driver interfaces, unsafe code, performance-critical optimized paths

#### 8.10 TLA+ Verification of Haskell-to-Rust Semantics

**Content:**
- Core Haskell semantics for generating Rust proven correct by TLA+
- Ensures semantic preservation across the purity boundary
- Generated code conforms to specifications

#### 8.11 Rust Compiler and the Proof Boundary

**Content:**
- Rust-built binaries technically fall outside the proof boundary (rustc not developed with formal methods)
- This is explicitly stated and accepted as an assumption
- The proof boundary is not punctured—documented assumption about rustc correctness

#### 8.12 Purity Wormholes: Compositional Trust (PRIMARY TREATMENT)

**Content:**

This is the authoritative section for purity wormholes.

- The proof boundary doesn't permit "punctures" but does permit compositional "wormholes"
- Pure-to-pure communication between nodes is valid (purity bubble to purity bubble)
- TLA+ proofs are only as good as their assumptions
- OS crashes, hardware failures, network/service outages are raw effects from the wild
- **Trust via purity wormhole**: pure compositions are valid between purity bubbles so long as node failures can be proven to be made eventually consistent by Paxos
- Byzantine Paxos is a sufficient model for handling nodes with unknowable failure states
- General theme: technology tools outside the purity boundary can be trusted via purity wormhole

**Mermaid diagram:**
```mermaid
flowchart TB
  subgraph Node1["Node 1 (Purity Bubble)"]
    H1["Haskell EI"] --> R1["Rust EI"]
    R1 --> Thunks1["Thunk Pipeline"]
  end
  subgraph Node2["Node 2 (Purity Bubble)"]
    H2["Haskell EI"] --> R2["Rust EI"]
    R2 --> Thunks2["Thunk Pipeline"]
  end
  subgraph Outside["Outside Proof Boundary"]
    Net["Network (may fail)"]
    OS["OS (may crash)"]
    HW["Hardware (may fail)"]
  end
  Thunks1 <-->|"Paxos Messages (Wormhole)"| Net
  Net <-->|"Paxos Messages (Wormhole)"| Thunks2
  R1 --> OS
  R2 --> OS
  OS --> HW
````

______________________________________________________________________

### 7.2 UPDATE `dsl/intro.md` — Add Infrastructure Reference

**Changes:**

1. Add `infrastructure_deployment.md` to Document Navigation table

1. Add to SSoT Link Map:

   ```markdown
   | Infrastructure deployment | [Infrastructure Deployment](infrastructure_deployment.md) |
   ```

______________________________________________________________________

### 7.3 Cross-Reference Updates Summary

| File                               | Change                                                  |
| ---------------------------------- | ------------------------------------------------------- |
| `dsl/intro.md`                     | Add infrastructure_deployment.md to navigation and SSoT |
| `dsl/infrastructure_deployment.md` | CREATE (12 sections)                                    |
| `engineering/boundary_model.md`    | ADD Section 8 (12 subsections)                          |

______________________________________________________________________

## Updated Implementation Sequence

### Updated Wave 1: DSL Foundation (Blocking)

1. Rewrite `dsl/intro.md` as boundary model hub
1. Create `dsl/jit.md` with JIT standards
1. Update `dsl/ml_training.md` header and framing
1. Update `dsl/consensus.md` header and framing
1. Verify `dsl/proof_boundary.md` unchanged

### Updated Wave 2: Engineering Core (High Priority)

1. Create `engineering/boundary_model.md`
1. Create `engineering/language_architecture.md`
1. Create `engineering/verification_contract.md`
1. Create `engineering/runner_pattern.md`
1. Update `engineering/architecture.md`
1. Update `engineering/code_quality.md`

### Updated Wave 3: Engineering Extended (Medium Priority)

1. Create `engineering/byzantine_security_model.md`
1. Create `engineering/generated_code_validation.md`
1. Create `engineering/standard_effects.md`
1. Update `engineering/total_pure_modelling.md`
1. Update `engineering/effect_patterns.md`
1. Update `engineering/development_workflow.md`

### Updated Wave 4: Engineering Support (Lower Priority)

1. Update `engineering/testing.md`
1. Update `engineering/testing_architecture.md`
1. Update `engineering/command_reference.md`
1. Update `engineering/README.md`

### Updated Wave 5: Legacy Documentation (Parallel)

1. Add legacy notices to all `tutorials/` files
1. Add legacy notices to all `api/` files
1. Update `demo/healthhub/` context
1. Update `product/` context

### Updated Wave 6: Unified Node Model (NEW)

1. Create `dsl/infrastructure_deployment.md` (12 sections)
1. Extend `engineering/boundary_model.md` with Section 8 (12 subsections)
1. Update `dsl/intro.md` with infrastructure references

### Updated Wave 7: Validation (Final)

1. Run `poetry run check-code`
1. Verify Functional Catalogue discovers new diagrams
1. Verify all cross-references
1. Final review of proof_boundary.md unchanged

______________________________________________________________________

## Updated Validation Checklist

### Checklist: DSL Documents

- [ ] `dsl/intro.md` has `**Status**: Authoritative source`
- [ ] `dsl/intro.md` has SSoT Link Map
- [ ] `dsl/intro.md` has Document Navigation Table
- [ ] `dsl/intro.md` has consolidated References section
- [ ] `dsl/intro.md` has Cross-References section
- [ ] `dsl/intro.md` does NOT contain TPM doctrine or 5-tier taxonomy
- [ ] `dsl/intro.md` has BoundaryModel canonical diagram
- [ ] `dsl/intro.md` references infrastructure_deployment.md
- [ ] `dsl/jit.md` has `**Status**: Authoritative source`
- [ ] `dsl/jit.md` has unsafe Rust policy documented
- [ ] `dsl/jit.md` has JitError and JitCodeLifecycle canonical diagrams
- [ ] `dsl/ml_training.md` has `**Status**: Reference only`
- [ ] `dsl/ml_training.md` has Authoritative Reference line
- [ ] `dsl/ml_training.md` has NO standalone References section
- [ ] `dsl/consensus.md` has `**Status**: Reference only`
- [ ] `dsl/consensus.md` has Authoritative Reference line
- [ ] `dsl/consensus.md` has NO standalone References or Source URLs
- [ ] `dsl/infrastructure_deployment.md` has `**Status**: Reference only`
- [ ] `dsl/infrastructure_deployment.md` has 12 sections as specified
- [ ] `dsl/infrastructure_deployment.md` covers whitelist security model
- [ ] `dsl/infrastructure_deployment.md` covers two-stage EI architecture
- [ ] `dsl/infrastructure_deployment.md` covers memory semantics
- [ ] `dsl/proof_boundary.md` is COMPLETELY UNCHANGED

### Checklist: Engineering Documents

- [ ] `engineering/boundary_model.md` created with proper header
- [ ] `engineering/boundary_model.md` has Section 8 with 12 subsections
- [ ] `engineering/boundary_model.md` covers thunk performance optimizer
- [ ] `engineering/boundary_model.md` covers memory semantics (Haskell GC, Rust borrowing)
- [ ] `engineering/boundary_model.md` covers purity wormholes (PRIMARY treatment)
- [ ] `engineering/boundary_model.md` has purity wormhole mermaid diagram
- [ ] `engineering/language_architecture.md` created with proper header
- [ ] `engineering/verification_contract.md` created with proper header
- [ ] `engineering/runner_pattern.md` created with proper header
- [ ] `engineering/byzantine_security_model.md` created with proper header
- [ ] `engineering/generated_code_validation.md` created with proper header
- [ ] `engineering/standard_effects.md` created with proper header
- [ ] `engineering/architecture.md` references boundary model
- [ ] `engineering/code_quality.md` has Doctrines 9-11
- [ ] `engineering/total_pure_modelling.md` contextualized within boundary model
- [ ] `engineering/README.md` updated with new SSoT links

### Checklist: Legacy Documents

- [ ] All `tutorials/` files have legacy notice
- [ ] All `api/` files have legacy notice
- [ ] `demo/healthhub/` has transition context

### Checklist: Validation

- [ ] All `Referenced by` lists are bidirectionally consistent
- [ ] `poetry run check-code` exits 0
- [ ] Functional Catalogue discovers new canonical diagrams

______________________________________________________________________

## Key Themes Summary

1. **One language**: UI, server logic, infrastructure deployment—all pure effects
1. **Nodes are uniform**: UI or server, both are trusted zones, differ only at transport
1. **Whitelist security monad**: Compositional security throughout pure logic
1. **Haskell = Thunk performance optimizer**: Main job is optimization per Dhall config rules
1. **Two-stage EI**: Haskell→Rust thunk pipeline is the purity boundary
1. **Purity extends through generated Rust**: TLA+-verified transpiler means purity continues through shared immutable memory contract
1. **Foreign call contract**: Thunk in → `Result[Future[T], E]` out immediately; Rust surrenders ownership when T available
1. **Memory semantics**: Rust accesses Haskell memory directly with agreed immutability; Haskell GC manages lifecycle
1. **TLA+ proves type representation**: Rust "instances" (named immutable dicts) sufficient for Haskell types
1. **Cancel effect monad**: Unit provides interrupt function, bind composes cancellation (hard/soft cancels)
1. **Multi-language EI**: Effect interpreters in Python/TypeScript/Swift/Kotlin to leverage native frameworks; isomorphism proven via TLA+
1. **Concurrent thunks**: Multiple thunks/interpreters run simultaneously; purity guarantees safe concurrent execution
1. **Paxos everywhere**: All inter-node communication modeled as Paxos messages
1. **JIT = Server**: Server nodes defined by JIT capability; no compiler = finite effect list
1. **Purity wormholes**: Trust between purity bubbles via Paxos eventual consistency
1. **Effects have timeouts**: Guaranteed finish time ensures liveness
1. **Self-verifying correctness**: GHC-built Haskell binary is a self-verified effect system

______________________________________________________________________

## Updated Critical Files Summary

| File                                                 | Action                       | Wave |
| ---------------------------------------------------- | ---------------------------- | ---- |
| `documents/dsl/intro.md`                             | Complete rewrite             | 1    |
| `documents/dsl/jit.md`                               | Create new                   | 1    |
| `documents/dsl/ml_training.md`                       | Update header + framing      | 1    |
| `documents/dsl/consensus.md`                         | Update header + framing      | 1    |
| `documents/dsl/proof_boundary.md`                    | NO CHANGES                   | 1    |
| `documents/engineering/boundary_model.md`            | Create new + Section 8       | 2, 6 |
| `documents/engineering/language_architecture.md`     | Create new                   | 2    |
| `documents/engineering/verification_contract.md`     | Create new                   | 2    |
| `documents/engineering/runner_pattern.md`            | Create new                   | 2    |
| `documents/engineering/architecture.md`              | Major update                 | 2    |
| `documents/engineering/code_quality.md`              | Significant update           | 2    |
| `documents/engineering/byzantine_security_model.md`  | Create new                   | 3    |
| `documents/engineering/generated_code_validation.md` | Create new                   | 3    |
| `documents/engineering/standard_effects.md`          | Create new                   | 3    |
| `documents/engineering/total_pure_modelling.md`      | Contextualize                | 3    |
| `documents/engineering/effect_patterns.md`           | Expand                       | 3    |
| `documents/engineering/development_workflow.md`      | Update                       | 3    |
| `documents/engineering/testing.md`                   | Expand                       | 4    |
| `documents/engineering/testing_architecture.md`      | Update                       | 4    |
| `documents/engineering/command_reference.md`         | Expand                       | 4    |
| `documents/engineering/README.md`                    | Update                       | 4    |
| `documents/tutorials/*.md` (29 files)                | Add legacy notice            | 5    |
| `documents/api/*.md` (10 files)                      | Add legacy notice            | 5    |
| `documents/dsl/infrastructure_deployment.md`         | **CREATE NEW** (12 sections) | 6    |

______________________________________________________________________

## Updated Estimated Scope

- **New documents**: 8 (7 engineering + 1 DSL infrastructure_deployment.md)
- **Major rewrites**: 2 (dsl/intro.md, dsl/jit.md)
- **Significant updates**: 9 (engineering core + boundary_model.md Section 8)
- **Minor updates**: 6 (engineering support)
- **Legacy notices**: 39 (tutorials + api)
- **Unchanged**: 1 (dsl/proof_boundary.md) + 3 (domain/) + others

**Total files affected**: ~62 of 84 markdown files
