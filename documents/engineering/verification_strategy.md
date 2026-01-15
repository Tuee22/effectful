# Verification Strategy

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: verification_contract.md, boundary_model.md

> **Purpose**: Define the overall verification strategy for Effectful applications, covering the spectrum from formal methods to testing.

______________________________________________________________________

## SSoT Link Map

| Need                  | Link                                              |
| --------------------- | ------------------------------------------------- |
| Verification contract | [Verification Contract](verification_contract.md) |
| Boundary model        | [Boundary Model](boundary_model.md)               |
| Testing standards     | [Testing](testing.md)                             |

______________________________________________________________________

## 1. Verification Layers

| Layer          | Method                      | Scope                 |
| -------------- | --------------------------- | --------------------- |
| Formal methods | TLA+ model checking         | Distributed protocols |
| Type system    | Static typing               | Program correctness   |
| Property tests | Randomized testing          | Edge cases            |
| Unit tests     | Example-based testing       | Specific behaviors    |
| Integration    | Real infrastructure testing | External assumptions  |

## 2. Verification by Boundary

### Purity Boundary

- Type checking (MyPy strict)
- Pure function testing
- ADT exhaustiveness

### Proof Boundary

- TLA+ model checking
- Conformance tests
- State machine verification

### Outside Proof Boundary

- Integration tests
- Chaos engineering
- Monitoring and observability

## 3. Verification Workflow

1. Write/modify code
1. Run type checker (static verification)
1. Run unit tests (purity boundary)
1. Run integration tests (external systems)
1. Model check TLA+ specs (protocol changes)

______________________________________________________________________

## Cross-References

- [verification_contract.md](verification_contract.md) — TLA+ verification workflow
- [boundary_model.md](boundary_model.md) — Boundary definitions
- [testing.md](testing.md) — Testing standards
