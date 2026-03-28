# Distributed ML Workflows Under the Compiler Morphology

**Status**: Reference only
**Supersedes**: none
**Referenced by**: intro.md, jit.md, proof_engine.md, consensus.md

> **Purpose**: Map distributed ML training onto the compiler-stack morphology, with emphasis on IR shape, purity-boundary and proof-boundary placement, reproducibility targets, and backend assumptions. The document leans on the pure-compute-DAG view of workflows as pure data with explicit independence and dependency structure.
> **📖 Authoritative Reference**: [DSL Intro](intro.md), [DSL Compiler Morphology](dsl_compiler_morphology.md), [Pure Compute DAGs in Haskell](pure_compute_dags_in_haskell.md), [Proof Boundary](proof_boundary.md), and [Proof Engine](proof_engine.md)

______________________________________________________________________

## SSoT Link Map

| Need                           | Link                                                            |
| ------------------------------ | --------------------------------------------------------------- |
| DSL overview                   | [DSL Intro](intro.md)                                           |
| Morphology of compiler choices | [DSL Compiler Morphology](dsl_compiler_morphology.md)           |
| Pure compute DAG semantics     | [Pure Compute DAGs in Haskell](pure_compute_dags_in_haskell.md) |
| Proof-boundary philosophy      | [Proof Boundary](proof_boundary.md)                             |
| Formal verification pipeline   | [Proof Engine](proof_engine.md)                                 |
| JIT and lowering context       | [JIT Compilation](jit.md)                                       |

______________________________________________________________________

## 1. Why ML Is a Useful Stress Case

Distributed ML training is a demanding workload because it combines:

- repeated numeric computation
- long-lived resource lifetimes
- distributed coordination
- checkpoint and recovery protocols
- stochastic data generation
- backend-specific performance constraints

That makes ML a useful stress case for the compiler morphology, but it does **not** force a single
architectural answer. Different ML workloads can justify different points in the morphology:

- different source languages
- different compiler implementation languages
- different IR families
- different proof tools
- different runtime and backend strategies

This document therefore treats ML as a design space, not as evidence that one fixed stack is
already correct.

______________________________________________________________________

## 2. Boundary Model for ML Workflows

ML workflows still fit the boundary model, but the exact placement of the boundaries depends on the
guarantees being sought.

| Boundary                         | Typical ML Content                                                                                                          |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Purity Boundary**              | training-step structure, dataflow, manifests, replay policy, declared dependencies, selected optimizer rewrites             |
| **Possible Proof Boundary**      | scheduler protocol, buffer and region discipline, checkpoint protocol, collective coordination, retry and cleanup semantics |
| **Often Outside Proof Boundary** | vendor kernels, GPU drivers, firmware, undocumented runtime behavior, hardware-specific performance claims                  |

The important point is that these are **not** fixed categories. A project may choose to:

- prove only orchestration and recovery properties
- prove selected rewrite families
- model-check distributed coordination
- formalize only a minimal semantic kernel
- rely on tests and runtime assertions for the rest

The proof boundary should therefore be described as an explicit engineering choice tied to the
required guarantee level.

In Effectful's canonical terminology, the **purity boundary** is the inner boundary around pure
Haskell workflow descriptions, pure effect descriptions, and analyzable compute-DAG structure.
Generated Rust, C++, CUDA, JS, Swift, Kotlin, or other imperative interpreters live outside the
purity boundary even when parts of them remain inside the **proof boundary** because their
lowerings and runtime contracts are modeled and verified. Drivers, firmware, and undocumented
vendor behavior usually remain outside the proof boundary.

### 2.1 Guarantee Levels

ML workflows often mix several kinds of guarantees. They should not be collapsed into one word such
as "correctness".

| Guarantee                       | Typical Meaning                                                             |
| ------------------------------- | --------------------------------------------------------------------------- |
| **Protocol safety**             | no illegal scheduler, buffer, checkpoint, or coordination state             |
| **Replay determinism**          | the same manifest and failure history produce the same observable execution |
| **Bit-for-bit reproducibility** | the same pinned environment yields byte-identical checkpoints or parameters |
| **Numerical equivalence**       | outputs match within stated tolerances                                      |
| **Statistical reproducibility** | distributions or metrics remain stable under a stochastic workflow          |

Different morphology choices may be appropriate for different targets. Bit-for-bit reproducibility
is one possible requirement, not the only legitimate one.

______________________________________________________________________

## 3. Morphology Axes That Matter Most for ML

The general compiler morphology becomes more concrete when applied to training systems.

| Axis                      | ML Pressure                                                                                                          |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Surface language**      | how naturally one can express training steps, stochastic programs, and reproducibility metadata                      |
| **Compiler core**         | how well the implementation supports rapid semantic iteration versus production integration                          |
| **Core IR**               | whether the system can represent step bodies, distributed effects, resource lifetimes, and stochastic state together |
| **Proof tooling**         | whether the focus is metatheory, rewrite correctness, protocol correctness, or mixed evidence                        |
| **Runtime strategy**      | interpreted, staged, or mostly compiled execution of training workflows                                              |
| **Verification boundary** | which parts are modeled, proved, assumed, or merely tested                                                           |

### 3.1 Source and Implementation Language

ML does not uniquely determine the source or implementation language.

- A proof-oriented language may be attractive when intrinsically typed representations or verified
  fragments are the priority.
- A language optimized for compiler engineering may be attractive when IR exploration and optimizer
  iteration are the priority.
- A systems language may be attractive when runtime integration, backend control, or deployment
  constraints dominate.
- A custom DSL may still be desirable once the user-facing model stabilizes.

The right choice depends less on "ML" as a category and more on which part of the stack is meant to
be the center of gravity.

### 3.2 IR Shape

ML workflows are unlikely to be well served by a single IR form used uniformly for every concern.
Several IR families can be useful together.

| IR shape                                 | Likely role in ML workflows                                                                                                              | Main limitation                                                                  |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Free modeling spectrum**               | pure workflow description, analyzable syntax, applicative and traversable parallel regions, selective visible branches, monadic barriers | becomes overly sequential only if everything is forced into the monadic end      |
| **ANF / SSA-like**                       | local step bodies, lowering, code generation, scalarized scheduling details                                                              | weak as the sole representation of long-range effect topology                    |
| **Effect graph**                         | training DAGs, data movement, collectives, checkpoint dependencies, host/device orchestration                                            | rewrite legality depends on explicit law tracking                                |
| **Region / capability graph**            | buffer lifetimes, device placement, RNG streams, trust zones, native escape hatches                                                      | more semantic overhead and design complexity                                     |
| **E-graph / equality saturation hybrid** | rewrite-dense pure subregions, algebraic optimization, local loop-body normalization                                                     | saturation and cost control become difficult outside carefully bounded fragments |

Here "free" should be understood in the sense used by
[Pure Compute DAGs in Haskell](pure_compute_dags_in_haskell.md): a hierarchy rather than shorthand
for "free monad only." That hierarchy matters:

- functorial structure preserves uniform transformation over a described computation
- applicative structure preserves statically known independent composition
- selective structure preserves visible conditional branches better than a fully monadic encoding
- monadic structure introduces genuinely data-dependent continuation
- traversable structure captures collection-parallel regions such as batch shards, path families,
  and parameter sweeps

This makes free modeling a robust front-end or staging technique for ML workflows. Applicative
or traversable regions can encode highly parallelizable fan-out, while selective or monadic regions
can mark true barriers such as adaptive control flow, checkpoint decisions, or data-dependent
coordination. The important practical benefit is that the workflow remains **data** that planners,
memoizers, and interpreters can inspect before execution.

For ML, the most plausible pattern is usually **compositional**:

- an outer IR that keeps effects, coordination, and resource boundaries explicit
- a free-modeling layer that preserves which parts are independent versus dependent
- one or more local IRs for numeric or rewrite-heavy fragments
- staged lowering between them

### 3.3 Competing IR Choices in ML Practice

The important question is usually not "which IR wins globally?" but "which IR should own which part
of the workflow?"

#### Free Modeling Spectrum

Best fit:

- keeping workflow structure as data for planning, dry runs, and memo analysis
- describing workflow structure before committing to execution
- preserving independent fan-out via applicative or traversable composition
- representing visible conditional refinements with selective structure
- marking genuinely dependent barriers with monadic structure
- supporting multiple interpreters for planning, simulation, testing, and execution

Less ideal when used alone for:

- low-level placement and memory layout
- whole-graph optimization across many backend-specific constraints
- final code generation for numeric hot paths

#### ANF / SSA-like IR

Best fit:

- step-local tensor computation
- explicit data dependencies
- classic compiler analyses such as liveness, CSE, dead-code elimination, and register or buffer
  planning
- lowering toward LLVM, Rust, C++, CUDA, or other target-specific codegen paths

Less ideal when used alone for:

- distributed coordination semantics
- checkpoint and replay policy
- rich effect topology across devices, stores, and control planes

#### Effect Graph IR

Best fit:

- host-device transfers
- collectives and synchronization
- checkpoint dependencies
- orchestration across workers, services, and storage
- making concurrency and hazard edges explicit

Less ideal when used alone for:

- expressing the full richness of local algebraic simplification
- serving as the only representation for low-level kernel codegen

#### Region / Capability Graph

Best fit:

- buffer and handle lifetime discipline
- device placement and memory region tracking
- RNG stream ownership
- trust boundaries between portable, domain, and native zones

Less ideal when used alone for:

- front-end workflow ergonomics
- pure algebraic optimization

#### E-Graph / Equality Saturation Hybrid

Best fit:

- pure tensor algebra
- optimizer update equations
- discretization identities for SDE kernels
- Monte Carlo estimator rewrites
- dead-node removal after algebraic simplification exposes unreachable or unused subgraphs

Less ideal when used alone for:

- checkpoint protocols
- retry semantics
- distributed coordination
- effectful or stochastic regions whose legality depends on more than equality

#### Working Decomposition

For many ML systems, the strongest arrangement is layered:

- a free-modeling surface for pure description and independence structure
- an effect graph for orchestration and distributed dependencies
- region or capability structure for resources, devices, and trust boundaries
- ANF, SSA-like, or backend-specific IRs for numeric kernels
- optional e-graph passes over pure extracted subregions

That decomposition keeps the competing IRs in productive tension rather than forcing one of them to
over-explain the whole system.

______________________________________________________________________

## 4. Representing Training Loops and Stochastic Workloads

Training is repetitive, but the repetition itself can be modeled in several ways.

Possible representations include:

- a finite staged plan produced from bounded loop constructs
- a loop skeleton with explicit state-transition semantics
- a recurrent subgraph whose iteration policy is handled by the runtime
- a free applicative region for independent work inside a larger monadic or graph-oriented shell
- partial unrolling for optimization or verification of hot fragments

No single choice should be treated as mandatory across all ML workloads.

### 4.1 Training Loops

Specific training loops often have a stable per-step shape:

- read batch or shard
- run forward computation
- run backward computation
- communicate gradients or activations
- update parameters and optimizer state
- checkpoint or emit metrics at selected boundaries

This structure argues for an IR that can express both:

- a repeated local kernel pattern
- an outer effectful protocol for coordination and recovery

One useful way to characterize that split is category-theoretic:

- applicative or traversable structure for independent shard-local, device-local, or batch-local work
- selective structure for visible conditional refinements that should remain analyzable before execution
- monadic structure for step-to-step dependence, adaptive branching, or failure-driven control flow

On that view, free modeling is not opposed to parallel training. It is often one of the cleanest
ways to preserve parallelizable structure in the representation while still allowing genuine
dependency barriers where they are needed.

That does **not** require the whole system to collapse into a single finite DAG early. Some
workflows may benefit from early graph materialization; others may keep loop structure explicit
until later lowering.

### 4.2 Monte Carlo and SDE-Based Data Generation

ML workflows sometimes generate training data or supervisory signals through Monte Carlo procedures,
simulators, or SDE rollouts. Those workloads add requirements that should be explicit in the IR:

- RNG streams and seed derivation
- discretization scheme and step size policy
- path batching and worker partitioning
- checkpoint and replay semantics for stochastic state
- aggregation rules for sampled outputs

These are not merely numerical details. They affect determinism, replay, and sometimes the meaning
of the workflow itself.

They also fit naturally into the same hierarchy. Many sampled paths or shard-local simulations are
good candidates for applicative or traversable composition because they are independent once
parameters and seeds are fixed. Monadic structure can then be reserved for adaptive resampling,
stopping criteria, checkpoint-driven replay, or other places where later work genuinely depends on
earlier outcomes.

______________________________________________________________________

## 5. Is an E-Graph Hybrid Worth Including for ML?

Probably yes, but only as a **bounded subset** of the IR stack rather than as the sole semantic
center.

### 5.1 Where It Seems Worthwhile

An e-graph or equality-saturation component is appealing when the ML workflow contains subproblems
with:

- many algebraically equivalent forms
- rich local rewrite opportunities
- clear law sets
- expensive search spaces that are hard to explore with hand-written greedy passes

That can happen in:

Here, **fusion** means combining adjacent tensor operations into one larger lowered region or one
larger kernel without changing the intended semantics. It matters in ML because it can remove
temporary tensors, reduce kernel-launch overhead, reduce memory traffic, and expose larger regions
for backend-specific optimization.

- training-step algebra before lowering
- fusion, reassociation, and normalization of tensor expressions
- optimizer update equations
- symbolic manipulation of loss or regularization terms
- Monte Carlo estimators with known algebraic identities
- SDE simulation kernels with declared discretization laws or transformation identities

This is the strongest case for inclusion: not "replace the IR with an e-graph", but "give the
compiler a way to extract rewrite-heavy regions into an equality-saturation subproblem".

### 5.2 Where It Becomes Risky

The e-graph story gets weaker when the representation must carry:

- distributed protocol state
- checkpoint commit semantics
- retry and cleanup behavior
- resource lifetime and aliasing constraints
- explicit RNG ordering guarantees
- backend-specific capability or trust boundaries

Those concerns are usually better represented in an effect graph, capability graph, state-machine
model, or staged lowering artifact. Equality alone is not a sufficient organizing principle for the
whole ML workflow.

### 5.3 Practical Position

For ML, an e-graph hybrid is worth considering if the compiler can clearly separate:

- **outer effectful semantics**
- **inner law-governed rewrite regions**
- **cost control for saturation**
- **side conditions for stochastic and stateful operations**

That separation matters especially for Monte Carlo and SDE workflows. A compiler may reasonably use
equality saturation inside a pure transition kernel or estimator algebra while still keeping RNG
streams, sample ordering, checkpointability, and distributed partitioning in the outer IR.

So the answer is:

> Include an e-graph or equality-saturation subset if the aim is to optimize rewrite-heavy ML
> fragments, including specific training-loop bodies and Monte Carlo or SDE generation kernels. Do
> not make it the only semantic center unless the project is willing to encode much richer effect,
> stochastic, and protocol constraints than equality saturation usually carries on its own.

______________________________________________________________________

## 6. Backend Languages and Native Realization for ML

Rust remains attractive for ML workflows wherever it can credibly target the runtime. That includes
more situations than a narrow server-side view might suggest, especially when Rust can target WASM
or sit as the control-plane language around specialized compute regions.

These backend choices occur **after** the purity-boundary crossing. They may still remain inside
the proof boundary when their lowerings, runtime contracts, and memory disciplines are modeled and
verified. Vendor kernels, drivers, firmware, and undocumented backend behavior usually remain
outside the proof boundary and must be handled as explicit assumptions.

But ML also encounters many environments where some other language or toolchain is effectively
forced:

- JS or TS for browser or host-environment integration
- Swift or Kotlin for mobile surfaces
- C++ or CUDA for GPU runtimes
- FPGA or HDL toolchains for reconfigurable hardware
- bespoke vendor languages, SDKs, or inference toolchains for proprietary accelerators

### 6.1 Rust-First with Native Adapters

One strategy is to keep the main runtime and effect machinery in Rust, and generate only enough
native code to expose required effect surfaces:

- JS bindings for browser-hosted effects
- Swift or Kotlin wrappers for mobile integration
- C++ or CUDA interpreters that expose compute effects to a Rust orchestration layer
- vendor SDK shims for proprietary devices

This is often the right answer when the foreign layer is mainly an access boundary rather than the
main optimization domain.

### 6.2 Full Native Lowering

A second strategy is to lower selected regions, or even an entire compute subworkflow, into the
target-native language itself.

For ML that can mean:

- emitting an effect interpreter in C++ or CUDA
- emitting the full compute region in CUDA rather than calling opaque kernels indirectly
- targeting a vendor accelerator toolchain directly
- generating mobile-native compute or orchestration paths when the platform demands it

This can matter because full native lowering may expose optimizations that a thinner bridge cannot,
including:

- deeper fusion across a larger compute region
- more aggressive dead-node removal
- backend-specific scheduling and placement
- tighter control over memory movement and launch structure

The tradeoff is that proof, validation, and maintenance burdens all rise with the number of fully
native backends.

### 6.3 Working Backend Posture for ML

The most defensible posture is therefore layered:

- prefer Rust where Rust can target the runtime well
- allow thin native layers where the foreign language is mostly an interface requirement
- allow full native realization where the backend is forced or where the optimization payoff is real

That keeps Rust preferred without pretending that CUDA, JS, Swift, Kotlin, FPGA flows, or
proprietary accelerator toolchains are secondary concerns in every ML deployment.

______________________________________________________________________

## 7. Formal Methods Options for ML

The morphology document distinguishes several proof classes. ML workloads can touch more than one of
them.

| Proof concern                | Plausible tool posture                                                           |
| ---------------------------- | -------------------------------------------------------------------------------- |
| **Core IR soundness**        | theorem-prover-style formalization or a smaller typed kernel                     |
| **Rewrite correctness**      | theorem proving, law-checked rewrites, or tightly constrained local validation   |
| **Distributed coordination** | temporal or state-machine modeling, possibly with model checking                 |
| **Lowering correctness**     | refinement arguments for selected fragments plus testing or assertions elsewhere |
| **Runtime contracts**        | mixed evidence: tests, assertions, differential checks, fuzzing, selected models |

This suggests several reasonable strategies:

- a proof-oriented core with lighter-weight runtime evidence
- a model-checking-heavy approach for checkpoint and collective protocols
- a hybrid proof stack
- a minimal formal core with explicit assumption management

Again, ML does not force one answer. The right posture depends on whether the main risk is semantic
drift in rewrites, distributed failure handling, opaque backend contracts, or something else.

______________________________________________________________________

## 8. Reproducibility Choices Should Stay Explicit

The earlier version of this document leaned toward the strongest reproducibility target. That target
remains important, but it should be presented as a choice in the morphology rather than as the only
valid outcome.

### 8.1 Common Reproducibility Postures

- **Pinned-environment bit-for-bit reproducibility**:
  useful when exact replay, auditability, or scientific traceability are central
- **Deterministic control-plane behavior with backend assumptions**:
  useful when orchestration must be reproducible even if numeric kernels are trusted black boxes
- **Tolerance-based numerical reproducibility**:
  useful when hardware variation or backend diversity is expected
- **Statistical reproducibility**:
  useful when the workflow is inherently stochastic and the claim is about distributions or metrics

Each posture carries different implications for:

- scheduler design
- RNG modeling
- collective ordering
- checkpoint contents
- backend pinning
- acceptable optimization freedom

### 8.2 Backend Assumptions

GPU backends, vendor libraries, storage layers, and network stacks should be treated as explicit
assumption surfaces unless they are actually modeled or verified. Which interfaces sit outside the
proof boundary will vary by project.

That means this document should avoid claiming that one backend strategy is universally the "sweet
spot". A better standard is:

- state the assumptions
- state the guarantees that depend on them
- revalidate when the assumption inventory changes

______________________________________________________________________

## 9. Working Position

The most defensible current position is intentionally narrow:

- ML workflows are a strong argument for a **layered** compiler stack, not for one universal IR or
  one universal proof tool.
- An **effect graph** remains a plausible outer semantic center for orchestration, dependency, and
  distributed protocol structure, but it may need help from ANF/SSA-like forms, capability or
  region structure, and staged lowerings.
- An **e-graph / equality-saturation hybrid** is worth including as an optional sub-IR for
  rewrite-heavy ML fragments, especially training-step bodies and Monte Carlo or SDE generation
  kernels, provided law boundaries and cost controls are explicit.
- **Rust-first realization** is attractive where Rust can target the runtime well, but ML systems
  must also allow thin native bridges and full native lowering in languages such as CUDA, JS,
  Swift, Kotlin, or vendor-specific accelerator toolchains when the domain requires them.
- The **outer semantics** of checkpointing, retries, collectives, resource safety, and
  reproducibility policy are still better captured by effect, capability, or state-machine-oriented
  representations than by equality saturation alone.

That is a useful design direction, but it is still a direction rather than a final commitment.
