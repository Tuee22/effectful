Leslie: Architectural Guide

Leslie is a library and toolchain for building distributed, effectful applications whose
consensus-critical behavior is formally validated using TLA+-style specifications, while
allowing high-performance local computation (including ML workflows and custom CUDA kernels)
via a compute-graph + JIT architecture.

This document is a downloadable architectural guide describing the design, layers, trust
boundaries, and evolution path of Leslie.

⸻

1. Design Goals

Leslie is designed to satisfy the following goals simultaneously:
	1.	Arbitrary expressiveness at the surface
	•	Users can write rich application logic using Haskell types, monads, effects, and composition.
	2.	Strong formal guarantees for distributed correctness
	•	Consensus, replication, and fault-tolerance logic is formally validated using a TLA+-style toolchain.
	3.	High-performance execution
	•	Local computation can be compiled into optimized compute graphs and JIT-compiled Rust/CUDA code.
	4.	Small trusted core
	•	The amount of code that must be trusted without proof is minimized and clearly identified.
	5.	Proof-carrying deployment
	•	It is impossible to deploy a consensus-critical application unless it has been formally checked.

⸻

2. High-Level Architecture

Leslie is structured as a set of layers, each with a clear responsibility and trust boundary:

+---------------------------------------------------+
| Leslie.App        (User EDSL, effects, monads)    |
+-------------------+-------------------------------+
| Leslie.Compute    | Leslie.Protocol               |
| (Graphs, ML, JIT) | (Consensus kernel DSL)        |
+-------------------+-------------------------------+
| Leslie.Model      (Finitary core, projections)    |
+---------------------------------------------------+
| Leslie.Extract    (Formal spec + obligations)     |
+---------------------------------------------------+
| Leslie.Check      (TLA+/SMT backends)              |
+---------------------------------------------------+
| Leslie.Verify     (Verified phantom types)         |
+---------------------------------------------------+
| Leslie.Runtime    (Distributed effect interpreter)|
+---------------------------------------------------+


⸻

3. Leslie.App — Surface Application Language

Purpose

Leslie.App is the user-facing EDSL where applications are written.

Characteristics:
	•	Pure, effectful programming style
	•	Rich Haskell types and abstractions
	•	Explicit effects (send, receive, storage, crypto, compute, etc.)

Key Principle

Not all application code is verified.

Only the consensus-critical portion of the program must be projected into the verified core.
Other logic may remain outside the formal model.

Status Typing

Applications are indexed by a phantom status:

data Status = Unverified | Verified

data App (s :: Status) a

Only App 'Verified can be deployed in production.

⸻

4. Leslie.Protocol — Consensus Kernel DSL

Purpose

Leslie.Protocol defines the verified distributed semantics of the system.

This is the heart of Leslie’s formal guarantees.

Core Model

Protocols are modeled as explicit state machines:
	•	Node-local state
	•	Typed messages
	•	Step relation
	•	Explicit scheduler/adversary interface

step :: Assumptions
     -> NodeId
     -> State
     -> Input
     -> (State, [OutMsg], [SysEff])

Assumptions as First-Class Parameters

All fault, timing, and trust assumptions are explicit:
	•	Byzantine fault bounds
	•	Network model (async / partial sync / sync)
	•	Message authentication and crypto assumptions
	•	Trust graphs / quorum systems

This allows arbitrary customization without changing the verification machinery.

Protocol Composition

Protocols are composable by layering:
	•	authentication ∘ transport ∘ quorum ∘ decision

Composition preserves formal semantics and proof obligations.

⸻

5. Leslie.Model — Finitary Verification Core

Purpose

Defines the subset of values and computations that can be reasoned about formally.

Projection Boundary

Any value that influences protocol behavior must be projected into the model core:

class Model a where
  type Core a
  project :: a -> Core a

Restrictions
	•	Finite or finitely-approximable domains
	•	Bounded data structures
	•	No hidden recursion or unbounded allocation

Values that cannot be projected are rejected during extraction.

⸻

6. Leslie.Compute — Compute Graph & ML Subsystem

Purpose

Provides a high-performance, optimizable execution path for local computation:
	•	ML workflows
	•	Data-parallel pipelines
	•	Custom CUDA kernels

Compute Graph IR
	•	Typed dataflow graph
	•	Explicit tensor shapes, dtypes, layouts
	•	Explicit device placement (CPU/GPU)
	•	Explicit purity/determinism annotations

Custom CUDA Operations

Custom kernels are defined as graph ops, not arbitrary side effects.

Each op declares:
	•	Type signature
	•	Shape function
	•	Workspace bounds
	•	Determinism guarantees

This enables:
	•	Static memory planning
	•	Safe execution
	•	Fixed memory footprint enforcement

Optimization Pipeline
	1.	Graph construction (Haskell)
	2.	Rewrite passes (fusion, CSE, layout)
	3.	Scheduling and memory planning
	4.	Lowering to a stable IR
	5.	Rust JIT execution (CPU + CUDA)

⸻

7. Leslie.Extract — Formal Artifact Generation

Purpose

Transforms protocol definitions into formal verification artifacts.

Generated artifacts include:
	•	TLA+ modules encoding protocol semantics
	•	Model-checking configurations
	•	Proof obligations (invariants, refinement mappings)
	•	Provenance metadata

Provenance Mapping

Every generated variable and transition is mapped back to source-level constructs,
enabling meaningful counterexample diagnostics.

⸻

8. Leslie.Check — Verification Backends

Purpose

Integrates external formal tools.

Supported backends:
	•	TLC (explicit-state model checking)
	•	Apalache (symbolic/SMT-based checking)
	•	TLAPS (proof checking, optional)

API

check :: Backend -> Bundle -> IO (Either Report CheckedBundle)

Reports include:
	•	Pass/fail
	•	Counterexample traces
	•	Source-mapped diagnostics

⸻

9. Leslie.Verify — Proof-Carrying Deployment

Purpose

Ensures that only verified programs can run.

verify :: Backend
       -> App 'Unverified a
       -> IO (Either Report (App 'Verified a))

This gate is non-bypassable without unsafe operations.

⸻

10. Leslie.Runtime — Distributed Effect Interpreter

Purpose

Executes verified applications in a distributed setting.

Characteristics
	•	Deterministic, replayable execution
	•	Single-writer per node
	•	Fixed-capacity immutable effect log
	•	Explicit scheduler/adversary interface

Storage Model
	•	Preallocated append-only log
	•	Persistent snapshots
	•	Typed OutOfSpace handling

The runtime semantics matches the protocol model by construction.

⸻

11. Trust Model

Phase 1 (Practical)

Trusted:
	•	Leslie extractor
	•	External TLA+/SMT tools
	•	Runtime kernel

Phase 2 (Stronger)
	•	Trace validation between runtime and model
	•	Differential checking

Phase 3 (Foundational, optional)
	•	Proof certificates
	•	Small proof-checking kernel
	•	Kernel proven sound in a proof assistant

⸻

12. Why Refinement is Central

Leslie prioritizes refinement proofs:
	•	Abstract specs define correctness
	•	Protocols prove they refine the abstract spec
	•	Customizations preserve correctness automatically

This scales far better than ad-hoc invariant proofs.

⸻

13. Summary

Leslie enables:
	•	Expressive distributed applications
	•	Formal validation of consensus correctness
	•	High-performance local computation
	•	Clear trust boundaries
	•	Incremental strengthening of guarantees

It combines the strengths of:
	•	Haskell (abstraction, DSLs, compilation)
	•	TLA+ (distributed system correctness)
	•	Rust (safe, fast runtime)
	•	CUDA (specialized performance)

without forcing any single tool to do what it is not good at.

⸻

End of leslie.md