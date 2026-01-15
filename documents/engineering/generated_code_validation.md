# Code Generation Pipeline and Validation

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: dsl/jit.md, verification_contract.md, architecture.md

> **Purpose**: Document how code is generated from TLA+ specifications and Haskell IR, including validation gates, fingerprinting, and CI/CD integration.

______________________________________________________________________

## SSoT Link Map

| Need                  | Link                                              |
| --------------------- | ------------------------------------------------- |
| Effectful overview    | [Effectful DSL Hub](../dsl/intro.md)              |
| JIT compilation       | [JIT Compilation](../dsl/jit.md)                  |
| Verification workflow | [Verification Contract](verification_contract.md) |
| Boundary model        | [Boundary Model](boundary_model.md)               |

______________________________________________________________________

## 1. Pipeline Overview

### 1.1 End-to-End Flow

```python
# diagram
┌─────────────────────────────────────────────────────────────────────┐
│                         DISCOVERY                                    │
│  Scan documents/models/**/*.tla for TLA+ specifications             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         VERIFICATION                                 │
│  Run TLC model checker on each specification                         │
│  Fail build if any counterexample found                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTRACTION                                   │
│  Parse Effectual DSL blocks from verified TLA+ files                 │
│  Build Haskell IR representation                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         GENERATION                                   │
│  Generate Rust code from Haskell IR                                  │
│  Apply deterministic formatting                                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FINGERPRINTING                               │
│  Compute content-addressed hash of generated code                    │
│  Compare with expected fingerprint                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         VALIDATION                                   │
│  Compile generated Rust                                              │
│  Run conformance tests                                               │
└─────────────────────────────────────────────────────────────────────┘
```

______________________________________________________________________

## 2. Discovery Phase

### 2.1 Model Location

TLA+ models live in a standard location:

```text
documents/
└── models/
    ├── core/
    │   ├── effect_runner.tla
    │   └── checkpoint.tla
    ├── consensus/
    │   ├── paxos.tla
    │   └── raft.tla
    └── app/
        └── payment_flow.tla
```

### 2.2 Discovery Rules

| Rule         | Description                      |
| ------------ | -------------------------------- |
| Pattern      | `documents/models/**/*.tla`      |
| Exclusions   | `*_test.tla`, `*_stub.tla`       |
| Dependencies | Follow `EXTENDS` declarations    |
| Order        | Topological sort by dependencies |

______________________________________________________________________

## 3. Verification Phase

### 3.1 TLC Model Checking

Each specification is verified with TLC:

```bash
# example
tlc -config $SPEC.cfg -workers auto $SPEC.tla
```

### 3.2 Configuration Files

Each `.tla` file has a corresponding `.cfg`:

```tla
\* payment_flow.cfg
SPECIFICATION Spec
INVARIANTS
    TypeOK
    NoDoubleCharge
    BalanceNonNegative
PROPERTIES
    EventuallyProcessed
    NoLostPayments
CONSTANTS
    Users = {u1, u2, u3}
    MaxAmount = 1000
```

### 3.3 Failure Handling

| TLC Result     | Action                      |
| -------------- | --------------------------- |
| No errors      | Proceed to extraction       |
| Counterexample | Fail build, report trace    |
| Timeout        | Fail build, suggest bounds  |
| Parse error    | Fail build, report location |

______________________________________________________________________

## 4. Extraction Phase

### 4.1 Effectual DSL Blocks

TLA+ files contain embedded Effectual DSL:

```tla
\* @effectual:begin
\* @adt PaymentState
\* @variant Pending { amount: Money, user: UserId }
\* @variant Authorized { amount: Money, user: UserId, auth: AuthCode }
\* @variant Captured { amount: Money, user: UserId, receipt: ReceiptId }
\* @variant Failed { reason: PaymentError }
\* @effectual:end
```

### 4.2 Extraction Output

The extractor produces Haskell IR:

````haskell
-- example code
PaymentStateADT
  { name = "PaymentState"
  , variants =
      [ Variant "Pending" [Field "amount" "Money", Field "user" "UserId"]
      , Variant "Authorized" [Field "amount" "Money", ...]
      , ...
      ]
  }
```python

---

## 5. Generation Phase

### 5.1 Code Generation Rules

| Rule | Description |
|------|-------------|
| Determinism | Same IR always produces identical output |
| Formatting | Apply rustfmt with standard config |
| Comments | Include source TLA+ file and line |
| Naming | Follow Rust conventions from IR |

### 5.2 Generated Artifacts

| Artifact | Purpose |
|----------|---------|
| `generated/rust/adts/*.rs` | ADT definitions |
| `generated/rust/state_machines/*.rs` | State machine implementations |
| `generated/rust/effects/*.rs` | Effect type definitions |
| `generated/rust/tests/*.rs` | Conformance test stubs |

### 5.3 Generation Example

From IR:

```haskell
PaymentStateADT { ... }
````

To Rust:

````rust
// Generated from: documents/models/app/payment_flow.tla:42
// Fingerprint: abc123def456

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PaymentState {
    Pending { amount: Money, user: UserId },
    Authorized { amount: Money, user: UserId, auth: AuthCode },
    Captured { amount: Money, user: UserId, receipt: ReceiptId },
    Failed { reason: PaymentError },
}
```text

---

## 6. Fingerprinting

### 6.1 Content-Addressed Hashing

Every generated file has a fingerprint:

```rust
// Fingerprint: sha256:abc123def456789...
````

The fingerprint is computed from:

1. Source TLA+ file content
1. Compiler version
1. Generation options

### 6.2 Fingerprint Validation

```bash
# Regenerate and compare
effectful-codegen --check

# Expected output:
# ✓ generated/rust/adts/payment_state.rs (unchanged)
# ✗ generated/rust/adts/user.rs (fingerprint mismatch)
```

### 6.3 Handling Mismatches

| Scenario            | Resolution                           |
| ------------------- | ------------------------------------ |
| Source changed      | Regenerate and commit                |
| Compiler changed    | Regenerate all and commit            |
| Manual edit         | Revert (generated code is immutable) |
| Fingerprint corrupt | Regenerate                           |

______________________________________________________________________

## 7. Validation Phase

### 7.1 Rust Compilation

```bash
# example
cargo build --release -p generated
cargo clippy -p generated -- -D warnings
```

### 7.2 Conformance Tests

Conformance tests verify generated code matches TLA+ spec:

```rust
#[test]
fn test_payment_state_transitions() {
    // From TLA+ trace: Pending -> Authorized
    let pending = PaymentState::Pending { ... };
    let authorized = pending.authorize(auth_code);
    assert!(matches!(authorized, PaymentState::Authorized { .. }));
}
```

### 7.3 Property Tests

Generated code is property-tested:

````rust
#[proptest]
fn test_state_machine_invariants(actions: Vec<Action>) {
    let mut state = initial_state();
    for action in actions {
        state = state.apply(action);
        assert!(state.satisfies_type_ok());
        assert!(state.satisfies_safety());
    }
}
```text

---

## 8. CI/CD Integration

### 8.1 CI Pipeline

```yaml
# CI pipeline for code generation validation
code-generation:
  steps:
    - name: Discover Models
      run: find documents/models -name "*.tla" > models.txt

    - name: Verify Models
      run: |
        while read model; do
          tlc -config ${model%.tla}.cfg $model
        done < models.txt

    - name: Generate Code
      run: effectful-codegen --output generated/

    - name: Check Fingerprints
      run: effectful-codegen --check

    - name: Compile Generated
      run: cargo build --release -p generated

    - name: Run Conformance
      run: cargo test -p generated
````

### 8.2 PR Checks

| Check                     | Gate     |
| ------------------------- | -------- |
| TLC passes                | Required |
| Fingerprints match        | Required |
| Rust compiles             | Required |
| Conformance passes        | Required |
| No uncommitted generation | Required |

### 8.3 Automated Regeneration

On merge to main:

````yaml
regenerate:
  if: github.ref == 'refs/heads/main'
  steps:
    - run: effectful-codegen --output generated/
    - run: |
        if git diff --quiet generated/; then
          echo "No changes"
        else
          git add generated/
          git commit -m "chore: regenerate code"
          git push
        fi
```text

---

## 9. Troubleshooting

### 9.1 Common Issues

| Issue | Symptom | Resolution |
|-------|---------|------------|
| TLC timeout | Build hangs | Reduce state space bounds |
| Fingerprint mismatch | CI fails | Regenerate and commit |
| Compile error | rustc fails | Fix generator bug |
| Conformance failure | Tests fail | Fix spec or generator |

### 9.2 Debugging Generation

```bash
# Verbose generation
effectful-codegen --verbose --output generated/

# Show IR
effectful-codegen --dump-ir payment_flow.tla

# Diff against expected
effectful-codegen --diff generated/
````

______________________________________________________________________

## 10. Checklist

Before merging generated code changes:

- [ ] TLC passes for all modified specs
- [ ] Fingerprints are up to date
- [ ] Generated Rust compiles with no warnings
- [ ] Conformance tests pass
- [ ] No manual edits to generated files
- [ ] Source TLA+ changes are committed with generated changes

______________________________________________________________________

## Cross-References

- [dsl/intro.md](../dsl/intro.md) — Effectful language overview
- [dsl/jit.md](../dsl/jit.md) — JIT compilation standards
- [verification_contract.md](verification_contract.md) — TLA+ verification workflow
- [boundary_model.md](boundary_model.md) — Where generated code fits
- [testing.md](testing.md) — Testing generated code
