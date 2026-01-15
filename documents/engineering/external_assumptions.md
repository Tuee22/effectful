# External Assumptions Management

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: boundary_model.md, verification_contract.md

> **Purpose**: Define the framework for documenting and managing assumptions about external systems that lie outside the proof boundary.

______________________________________________________________________

## SSoT Link Map

| Need                 | Link                                              |
| -------------------- | ------------------------------------------------- |
| Boundary model       | [Boundary Model](boundary_model.md)               |
| Verification         | [Verification Contract](verification_contract.md) |
| Proof boundary essay | [Proof Boundary](../dsl/proof_boundary.md)        |

______________________________________________________________________

## 1. What Are External Assumptions?

External assumptions document our expectations about systems we cannot formally verify:

| Category     | Examples                              |
| ------------ | ------------------------------------- |
| Hardware     | CPU arithmetic, memory behavior       |
| Operating    | Kernel correctness, syscall semantics |
| Runtime      | Python/Rust/Haskell compiler          |
| Network      | TCP delivery semantics                |
| Storage      | Filesystem durability guarantees      |
| Dependencies | Third-party library behavior          |

## 2. Assumption Documentation Format

Each external assumption should include:

1. **Component** - What external system is involved
1. **Assumption** - What behavior we expect
1. **Failure mode** - What happens if assumption is violated
1. **Mitigation** - How we detect or recover from violations

## 3. Integration with Proof Boundary

External assumptions define where the proof boundary ends:

- Inside the boundary: Formally verified or type-checked
- At the boundary: Documented assumptions
- Outside the boundary: Trust through testing and monitoring

______________________________________________________________________

## Cross-References

- [boundary_model.md](boundary_model.md) — Boundary definitions
- [verification_contract.md](verification_contract.md) — TLA+ verification workflow
- [../dsl/proof_boundary.md](../dsl/proof_boundary.md) — Proof boundary philosophy
