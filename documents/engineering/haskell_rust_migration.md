# Haskell/Rust Migration Strategy

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: language_architecture.md, boundary_model.md

> **Purpose**: Define the migration path from Python prototype to the full Effectful language with Haskell frontend and Rust backend.

______________________________________________________________________

## SSoT Link Map

| Need                  | Link                                              |
| --------------------- | ------------------------------------------------- |
| Language architecture | [Language Architecture](language_architecture.md) |
| Boundary model        | [Boundary Model](boundary_model.md)               |
| JIT compilation       | [JIT Compilation](../dsl/jit.md)                  |

______________________________________________________________________

## 1. Migration Overview

The Effectful language uses a two-stage architecture:

| Stage   | Language | Purpose                         |
| ------- | -------- | ------------------------------- |
| Stage 1 | Haskell  | Type checking, optimization, IR |
| Stage 2 | Rust     | Code generation, runtime        |

## 2. Current State: Python Prototype

The Python effectful library serves as:

- Reference implementation for effect semantics
- Demonstration of pure functional patterns in Python
- Playground for exploring API design

## 3. Target State: Full Language

The full Effectful language provides:

- Haskell-based type checking and effect analysis
- Compile-time guarantees via GHC
- Rust runtime for performance
- WASM/native compilation targets

## 4. Migration Path

1. **Phase 1**: Python prototype (current)
1. **Phase 2**: Effect DSL embedded in Haskell
1. **Phase 3**: Rust code generation
1. **Phase 4**: Full toolchain integration

______________________________________________________________________

## Cross-References

- [language_architecture.md](language_architecture.md) — Language design
- [boundary_model.md](boundary_model.md) — Boundary definitions
- [../dsl/jit.md](../dsl/jit.md) — JIT compilation standards
