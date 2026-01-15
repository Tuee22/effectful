# Formal Verification: TLA+ Model Checking and Conformance

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: architecture.md, dsl/intro.md, dsl/jit.md

> **Purpose**: Document how TLA+ integrates with the development workflow, including proof boundary definitions, model checking, conformance tests, and determinism gates.

______________________________________________________________________

## SSoT Link Map

| Need                      | Link                                                      |
| ------------------------- | --------------------------------------------------------- |
| Effectful overview        | [Effectful DSL Hub](../dsl/intro.md)                      |
| Proof boundary philosophy | [Proof Boundary Essay](../dsl/proof_boundary.md)          |
| Boundary model            | [Boundary Model](boundary_model.md)                       |
| JIT verification          | [JIT Compilation](../dsl/jit.md)                          |
| Code generation           | [Generated Code Validation](generated_code_validation.md) |

______________________________________________________________________

## 1. Verification Scope

### 1.1 What We Verify

TLA+ verification applies to the **proof boundary**:

| Component               | Verification Level             |
| ----------------------- | ------------------------------ |
| Protocol state machines | Full TLA+ model checking       |
| Effect runner contracts | Conformance tests against TLA+ |
| Distributed consensus   | Safety and liveness properties |
| Checkpoint protocols    | Atomicity and durability       |
| Resource management     | Bounded allocation invariants  |

### 1.2 What We Cannot Verify

Things **outside the proof boundary**:

| Component          | Why Unverifiable  | Mitigation           |
| ------------------ | ----------------- | -------------------- |
| Hardware behavior  | No formal model   | Document assumptions |
| Driver correctness | Proprietary code  | Integration tests    |
| OS scheduler       | Non-deterministic | Timeout enforcement  |
| Network timing     | Physical reality  | Model as async       |
| Rust compiler      | Assumed correct   | Use stable releases  |

______________________________________________________________________

## 2. TLA+ Properties

### 2.1 Property Categories

Every TLA+ specification defines:

| Property     | Purpose                   | Example                                 |
| ------------ | ------------------------- | --------------------------------------- |
| **Init**     | Initial state predicate   | `Init == state = "idle"`                |
| **Next**     | State transition relation | `Next == Submit \/ Process \/ Complete` |
| **TypeOK**   | Type invariant            | `TypeOK == state \in States`            |
| **Safety**   | Nothing bad happens       | `NoDoubleSpend == ...`                  |
| **Liveness** | Something good happens    | `EventuallyProcessed == <>[] processed` |

### 2.2 Standard Property Patterns

**Safety Invariants**:

```tla
\* No two nodes commit different values
NoConflictingCommits == \A n1, n2 \in Nodes:
    committed[n1] # {} /\ committed[n2] # {} =>
    committed[n1] = committed[n2]

\* Resources never exceed limits
ResourceBounded == \A r \in Resources:
    allocated[r] <= limit[r]
```

**Liveness Properties**:

````tla
\* Every submitted request is eventually processed
EventuallyProcessed == \A r \in Requests:
    submitted[r] ~> processed[r]

\* System eventually makes progress
MakesProgress == []<>(state # state')
```text

---

## 3. Model Checking Workflow

### 3.1 Development Cycle

````

┌─────────────┐
│ Design │
│ Protocol │
└──────┬──────┘
│
▼
┌─────────────┐ ┌─────────────┐
│ Write │───►│ Run TLC │
│ TLA+ Spec │ │ Model Check │
└─────────────┘ └──────┬──────┘
▲ │
│ ▼
│ ┌─────────────┐
│ │ Counterex? │
│ └──────┬──────┘
│ │
│ ┌────────────┴────────────┐
│ │ │
│ ▼ ▼
│ ┌─────────┐ ┌─────────────┐
└─│ Fix Spec│ │ Implement │
└─────────┘ │ in Rust │
└──────┬──────┘
│
▼
┌─────────────┐
│ Conformance │
│ Tests │
└─────────────┘

````

### 3.2 TLC Configuration

Standard model checking configuration:

```tla
SPECIFICATION Spec
INVARIANTS
    TypeOK
    SafetyInvariant
    ResourceBounded
PROPERTIES
    Liveness
CONSTANTS
    Nodes <- {n1, n2, n3}
    MaxRequests <- 10
````

### 3.3 State Space Management

| Technique              | When to Use                     |
| ---------------------- | ------------------------------- |
| Symmetry reduction     | Nodes are interchangeable       |
| State abstraction      | Infinite domains                |
| Bounded model checking | Liveness with large state space |
| Inductive invariants   | Unbounded verification          |

______________________________________________________________________

## 4. Conformance Tests

### 4.1 Purpose

Conformance tests bridge TLA+ specifications and Rust implementations:

```text
# diagram
TLA+ Spec ─────────────────► Expected Behavior
                                    │
                                    ▼
                              ┌───────────┐
                              │ Compare   │
                              └─────┬─────┘
                                    │
Rust Implementation ──────────► Actual Behavior
```

### 4.2 Test Generation

Conformance tests are generated from TLA+ traces:

1. **TLC exploration** produces state/action traces
1. **Test generator** converts traces to test cases
1. **Test runner** executes against Rust implementation
1. **Comparator** checks actual matches expected

### 4.3 Test Structure

````rust
#[test]
fn conformance_submit_then_process() {
    // Generated from TLA+ trace
    let initial = State::idle();

    // Action: Submit
    let after_submit = initial.submit(request_1);
    assert_eq!(after_submit.state, "pending");

    // Action: Process
    let after_process = after_submit.process(request_1);
    assert_eq!(after_process.state, "processed");

    // Invariant checks
    assert!(after_process.satisfies_type_ok());
    assert!(after_process.satisfies_safety());
}
```text

---

## 5. Determinism Gates

### 5.1 The Gate Stack

Every code path must pass all gates:

````

┌─────────────┐
│ TLA+ Spec │
└──────┬──────┘
│ TLC passes
▼
┌─────────────┐
│ Code Gen │
└──────┬──────┘
│ Deterministic
▼
┌─────────────┐
│ No Diff │
└──────┬──────┘
│ Fingerprint matches
▼
┌─────────────┐
│ Type Check │
└──────┬──────┘
│ Rust compiles
▼
┌─────────────┐
│ Conformance │
└──────┬──────┘
│ Tests pass
▼
┌─────────────┐
│ Ship │
└─────────────┘

````

### 5.2 Gate Definitions

| Gate | Input | Output | Failure Mode |
|------|-------|--------|--------------|
| **TLC** | TLA+ spec | Pass/counterexample | Spec redesign |
| **Code Gen** | Haskell IR | Rust source | Compiler bug |
| **No Diff** | Generated code | Same/different | Regenerate |
| **Type Check** | Rust source | Success/errors | Fix code |
| **Conformance** | Rust binary + traces | Pass/fail | Fix implementation |

### 5.3 Determinism Enforcement

Code generation must be deterministic:

```text
# deterministic code generation
Same Input ────────► Same Output

ComputeGraph_v1 ────► RustCode_abc123
ComputeGraph_v1 ────► RustCode_abc123 (identical)
ComputeGraph_v2 ────► RustCode_def456 (different input, different output)

````

If regeneration produces different output for the same input, the build fails.

______________________________________________________________________

## 6. Assumption Management

### 6.1 Assumption Inventory

Every TLA+ specification has an assumption inventory:

```markdown
## Assumption Inventory

### Network Assumptions
1. Messages may be delayed, reordered, or lost
2. Delivery is not guaranteed but is eventually possible (partial sync)
3. No message corruption (TCP handles this)

### Node Assumptions
1. Nodes may crash and recover
2. Recovered nodes can read their durable state
3. No Byzantine behavior (nodes don't lie)

### Timing Assumptions
1. Local clocks may drift but don't jump backwards
2. Timeouts are finite but unbounded
3. Eventually synchrony holds for liveness
```

### 6.2 Assumption Validation

Assumptions cannot be proven but can be validated:

| Technique         | What It Validates                       |
| ----------------- | --------------------------------------- |
| Integration tests | Normal behavior matches assumptions     |
| Chaos engineering | Failure behavior matches assumptions    |
| Monitoring        | Production behavior matches assumptions |
| Incident analysis | Assumption violations are detected      |

______________________________________________________________________

## 7. Cost/Benefit Analysis

### 7.1 When to Use TLA+

| Scenario             | TLA+ Value | Recommendation         |
| -------------------- | ---------- | ---------------------- |
| Distributed protocol | Very high  | Always specify         |
| Consensus algorithm  | Very high  | Always specify         |
| State machine        | High       | Usually specify        |
| CRUD operations      | Low        | Skip TLA+              |
| Pure computations    | Low        | Type system sufficient |

### 7.2 Verification Investment

| Component           | Specification Time | Model Check Time | ROI       |
| ------------------- | ------------------ | ---------------- | --------- |
| Core consensus      | Weeks              | Hours            | Very high |
| Checkpoint protocol | Days               | Minutes          | High      |
| Effect runner       | Hours              | Seconds          | Medium    |
| Utility function    | Minutes            | N/A              | Skip      |

______________________________________________________________________

## 8. Integration with CI/CD

### 8.1 CI Pipeline

```yaml
# CI pipeline for verification
verification:
  steps:
    - name: Run TLC
      run: tlc -config $SPEC.cfg $SPEC.tla

    - name: Generate Conformance Tests
      run: generate-conformance $SPEC.tla > tests/conformance_$SPEC.rs

    - name: Check Determinism
      run: diff -q generated/ expected/

    - name: Build Rust
      run: cargo build --release

    - name: Run Conformance
      run: cargo test --test conformance
```

### 8.2 Artifact Management

| Artifact          | Storage        | Retention   |
| ----------------- | -------------- | ----------- |
| TLA+ specs        | Git            | Forever     |
| TLC output        | CI logs        | 90 days     |
| Counterexamples   | Git (if found) | Forever     |
| Conformance tests | Generated      | Per build   |
| Fingerprints      | Build cache    | Per version |

______________________________________________________________________

## 9. Troubleshooting

### 9.1 Common Issues

| Issue               | Symptom                 | Resolution                     |
| ------------------- | ----------------------- | ------------------------------ |
| State explosion     | TLC runs forever        | Add symmetry, reduce constants |
| Counterexample      | TLC finds violation     | Fix spec or design             |
| Conformance failure | Rust doesn't match spec | Fix implementation             |
| Non-determinism     | Different outputs       | Fix code generator             |
| Timeout             | TLC killed              | Bound model, add abstraction   |

### 9.2 Debugging Counterexamples

1. **Read the trace**: TLC shows state sequence
1. **Identify the violation**: Which invariant failed?
1. **Find the action**: Which transition caused it?
1. **Analyze**: Is the spec wrong or the design wrong?
1. **Fix and re-run**: Iterate until TLC passes

______________________________________________________________________

## Cross-References

- [dsl/intro.md](../dsl/intro.md) — Effectful language overview
- [dsl/proof_boundary.md](../dsl/proof_boundary.md) — Verification philosophy
- [dsl/jit.md](../dsl/jit.md) — JIT verification requirements
- [boundary_model.md](boundary_model.md) — Boundary definitions
- [generated_code_validation.md](generated_code_validation.md) — Code generation pipeline
- [testing.md](testing.md) — Testing strategy
