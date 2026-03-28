# Infrastructure Deployment Under the Compiler Morphology

**Status**: Reference only
**Supersedes**: none
**Referenced by**: intro.md

> **Purpose**: Explain how infrastructure deployment, node topology, and runtime orchestration fit into the Effectful compiler morphology: infrastructure actions can be represented as pure workflow descriptions and effect families inside the purity boundary, then realized by interpreters and native runtimes beyond it.
> **📖 Authoritative Reference**: [DSL Intro](intro.md)

______________________________________________________________________

## SSoT Link Map

| Need                | Link                                                            |
| ------------------- | --------------------------------------------------------------- |
| Effectful overview  | [DSL Intro](intro.md)                                           |
| Boundary model      | [Boundary Model](../engineering/boundary_model.md)              |
| Consensus protocols | [Consensus](consensus.md)                                       |
| JIT compilation     | [JIT and Staged Lowering](jit.md)                               |
| Pure compute DAGs   | [Pure Compute DAGs in Haskell](pure_compute_dags_in_haskell.md) |

______________________________________________________________________

## 1. Deployment in the Compiler Morphology

**In the current docs, infrastructure deployment is not a separate product and not a separate
language. It is one application of the Effectful compiler morphology, where deployment logic is
described as pure workflow data and later interpreted by runtime-specific adapters.**

This single unifying idea drives the entire system:

- **Effects are pure types**; effect interpreters run them on "nodes"
- **A node is an abstract execution site** such as a UI host, server, worker, or control-plane process
- **Communication is modeled as typed message flow**; Paxos-style or other consensus protocols enter
  when the workload requires them, rather than being the only possible transport story
- **One pure representation layer** can describe UI logic, server logic, and infrastructure
  orchestration even when their realized runtimes differ
- The **pure core and pure effect descriptions** live inside the purity boundary; interpreters in
  Rust or other imperative languages live outside the purity boundary and may still sit inside the
  proof boundary when their contracts are modeled and verified

### What This Means in Practice

The same pure workflow model can describe:

- **User interfaces** (via peripheral I/O effects)
- **Server logic** (business rules, data processing)
- **Event-driven infrastructure deployment rules** (provisioning, configuration)

The distinction between "frontend", "backend", and "infrastructure" becomes less about separate
authoring stacks and more about which runtime realizes which part of the topology.

______________________________________________________________________

## 2. Nodes: The Abstract Device Representation

A **node** is an abstract execution site in the Effectful distributed-system model.

### Two Node Types

| Type          | Description                               | Examples                                      |
| ------------- | ----------------------------------------- | --------------------------------------------- |
| **UI-facing** | User-facing interface with peripheral I/O | Phone, tablet, desktop, browser, smart device |
| **Server**    | Backend processing with JIT capability    | Cloud VM, container, bare metal server        |

### Node Properties

- **Internally safe and trusted zone**: Within a node, code is verified and trusted
- **Transport topology differs**: DNS, ingress rules, certificates, session cookies vary by deployment
- **At the pure representation level, nodes are uniform**: the compiler morphology sees no
  difference between node types until lowering crosses the purity boundary and binds to concrete
  runtimes

### Requirements to Run an Effectful Node

A device or machine can run one or more Effectful nodes if:

1. **It can host a runtime artifact** built in Rust or another supported target language (native or WASM)
1. **Some interpreter or adapter can talk to the required drivers** for hardware and/or platform-native APIs

This completely decouples the server/client relationship from where code actually runs. There is still a global compute DAG, meaning arbitrary amounts of compute can happen on any node if there is reason to do so:

- Better UX (responsive local interactions)
- Lower latency (compute near data)
- Reducing server loads (distribute work)

______________________________________________________________________

## 3. The Whitelist Security Model

A robust, expressive **whitelist-based security model** runs compositionally throughout pure logic.

### The Whitelist Monad

The categorical vocabulary here follows
[Pure Compute DAGs in Haskell](pure_compute_dags_in_haskell.md). The point is not OOP-style
inheritance, but compositional structure for pure descriptions.

Each time a pure function returns a pure type, that type must be an instance of a **whitelist monad**:

- The whitelist monad contains a new whitelist
- The whitelist itself is a monadic functor representing security logic
- **Empty lists are valid** and the default (monadic unit)

### Security Semantics

| Whitelist State | Meaning                                                                             |
| --------------- | ----------------------------------------------------------------------------------- |
| Empty list      | Data may **not** be sent outside the node                                           |
| Non-empty list  | Names of other nodes in an abstract namespace type (TBD) that may receive this data |

### Effect Interpreter Security Contract

Each effect interpreter has a security contract specifying:

- Which messages may be sent
- To which node namespaces

This ensures security is not an afterthought but is woven into the type system itself. Invalid security states are unrepresentable.

______________________________________________________________________

## 4. Pure Workflow Assembly and Optimization

**Haskell is the preferred language today for assembling and optimizing pure workflow
descriptions**, according to rules in the Dhall config, then emitting lowered thunks for downstream
interpreters.

For the FP concepts that make this possible, especially the functor, applicative, selective,
traversable, and monadic hierarchy, see
[pure_compute_dags_in_haskell.md](pure_compute_dags_in_haskell.md).

### Configuration-Driven Behavior

- Dhall config is modeled as a pure type (in Python for current implementation)
- Config addresses questions like: is a compiler assumed when none is available?

| Compiler Available? | Behavior                                          |
| ------------------- | ------------------------------------------------- |
| No                  | Immediate `Error(E)` if compiler assumed          |
| No                  | Locked into explicit, finite list of Rust effects |
| Yes                 | Full JIT capabilities available                   |

### Thunk Assembly

Haskell passes **thunks** that are async bundles of abstract effects.

The broader functor, applicative, selective, traversable, and monadic toolkit is heavily utilized
for:

- Expressing inspectable pure compute DAGs
- Preserving visible independence via applicative or traversable structure
- Representing visible conditional branches and genuine dependency barriers
- **Security whitelist monad** (compositional security)
- **Effect timeout wrappers** (explicit timeout behavior, can optionally return `Success(T)`)

**Every thunk is a pure representation of effects**, assembled by Haskell.

______________________________________________________________________

## 5. Crossing the Purity Boundary: Memory Semantics and Foreign Call Contract

### Lowered IR Crosses; Purity Does Not Extend Through Rust

In Effectful's canonical boundary model, the purity boundary contains the pure Haskell workflow,
pure effect descriptions, and analyzable compute-DAG structure. Generated Rust or other imperative
interpreters do **not** become part of the purity boundary merely because they are generated from a
pure source.

What can happen instead is narrower and more useful:

- the lowered IR crosses the purity boundary as a pure description
- the interpreter consuming that IR lives outside the purity boundary
- that interpreter may still remain inside the proof boundary when its lowering rules, shared-memory
  contract, and runtime behavior are modeled and verified

### The Foreign Call Interface

An explicit call function in Rust is invoked via Haskell foreign call:

- **Input**: Thunk type (referencing memory locations for thunk-scoped immutable store)
- **Output**: `Result[Future[T], E]` returned "immediately"
  - The Future may eventually point to memory Rust allocated
  - Rust **surrenders ownership** of this memory when/if `T` becomes available
  - Haskell's GC can then manage it

### Memory Ownership Model

| Responsibility                | Owner                                          |
| ----------------------------- | ---------------------------------------------- |
| Memory allocation for effects | Haskell (monadic via GC)                       |
| Memory freeing after use      | Haskell GC                                     |
| Traversing immutable data     | Rust (using its own model for Haskell types)   |
| Arbitrary return data shapes  | Rust (allocates, then surrenders ownership)    |
| Static `Result[T,E]` shapes   | Haskell preallocates; Rust's borrowing manages |

- TLA+ formally proves this representation is sufficient for our class of Haskell types
- A verified shared-memory contract can help keep this handoff inside the proof boundary
- Purity ends at the Haskell-side pure representation; correctness of generated runtimes still
  depends on lowering proofs and explicit assumptions

### The Cancel Effect Monad

Every effect must implement a monadic "cancel effect" command:

- **Unit**: Provides a function that can be used to "interrupt" something we are awaiting on
- **Bind**: Represents the logic for composing cancellation—chains forward monadically

This enables modeling of:

- **Hard cancels**: Immediate termination, resources released
- **Soft cancels**: Graceful shutdown, allows cleanup
- Parent effect cancellation propagates to child effects via bind

______________________________________________________________________

## 6. The Two-Stage Effect Interpreter Architecture

### Haskell Effect Interpreter

- Parses Dhall config
- Launches effect interpreter
- Packages thunks as pure effect descriptions
- Gives thunks to Rust as references to pure immutable types

### Rust Effect Interpreter

- Processes effects concurrently
- Subscribes to FIFO-style effect queue from Haskell
- Can traverse Haskell's immutable data structures using its own model
- Immutability from the perspective of the thunk's lifetime

### Deployment Flexibility

The two-stage EI can be built inside other binaries:

- WASM running in a browser
- Edge devices with limited resources
- Server containers with full JIT capability

The thunk pipeline flowing out of Haskell is one concrete **crossing of the purity boundary**. It
is the handoff from pure descriptions to imperative interpreters. Whether the receiving interpreter
remains inside the proof boundary depends on what has been modeled and verified.

### Effect Interpreters in Other Languages

Effect interpreters can be implemented in **other imperative languages** to leverage their frameworks:

| Language   | Framework Access                                          |
| ---------- | --------------------------------------------------------- |
| Python     | ML frameworks (PyTorch, TensorFlow), scientific computing |
| TypeScript | Browser APIs, Node.js ecosystem                           |
| Swift      | iOS/macOS native (UIKit, SwiftUI, ARKit)                  |
| Kotlin     | Android native, JVM ecosystem                             |

**Implementation requirements:**

- Specific class of pure types/functions from Haskell represented idiomatically
- **Isomorphism proven via TLA+**
- Shared memory model for immutable references tied to thunk lifespan
- EI must preserve the semantics of the pure effect IR after the purity-boundary crossing, and any
  unmodeled behavior must be treated as an assumption outside the proof boundary

### Concurrent Thunks and Interpreters

**Multiple thunks/interpreters can run simultaneously:**

- Each thunk maintains its own immutable reference scope
- Interpreters run in parallel across threads/processes
- Shared memory model ensures no interference
- Purity guarantees make concurrent execution safe by construction

This enables leveraging native frameworks while maintaining the unified purity model.

______________________________________________________________________

## 7. Transport Layer and Network Interface

### Abstract Transport Model

The transport layer is **not fixed by the morphology**. Instead:

- Rust or another runtime sits at the **proof-boundary edge**
- Network drivers, operating-system services, and transport implementations remain outside the proof boundary
- The runtime interacts with those external components in the course of interpreting effects
- Abstract message types map to real-world transport

### Message Type Mapping

| Abstract Message Type | Real-World Transport                |
| --------------------- | ----------------------------------- |
| Asynchronous          | UDP packets, fire-and-forget HTTP   |
| Partially synchronous | TCP with timeouts, WebSocket        |
| Synchronous           | Request-response REST, blocking RPC |

### Generalized Paxos

Consensus-sensitive deployments may use generalized Paxos or related protocols to handle multiple
message types:

- **Asynchronous** messages
- **Partially synchronous** messages
- **Synchronous** messages

This allows the appropriate abstractions at the transport layer while maintaining uniform pure
semantics on the inside of the purity boundary.

______________________________________________________________________

## 8. JIT and the Filesystem Model

### JIT-Capable Server Nodes

**One common server posture is a JIT-capable node**: it can compile generated Rust or other
lowered artifacts in order to leverage the optimizer as a late performance operator for specific
effects or compute regions.

### JIT Compilation

On nodes with compilers, the pure workflow layer may emit lowered implementations of thunks with
additional logic:

- the optimizer analyzes the thunk
- generates optimized Rust or target-native code
- the local toolchain compiles and caches the result

### The Filesystem Model

A pure type representing the filesystem:

- **Immutable but extendable** (immutable hash table or similar)
- Rust is responsible for JITs and caching them
- Between executing thunks, Rust essentially updates itself
- Shared immutable hash table as option for JIT cache

______________________________________________________________________

## 9. Effects and Timeouts

### Effect Semantics

Lowered effect descriptions are the pure representation that crosses the purity boundary. The
imperative runtimes that consume them may still remain inside the proof boundary when their
contracts are modeled and verified, but they are no longer inside the purity boundary.

### Guaranteed Finish Time

**All effects must have a "guaranteed finish time"** at which point they logically return bottom.

| Outcome                        | Behavior                                    |
| ------------------------------ | ------------------------------------------- |
| Success before timeout         | Returns `Success(T)`                        |
| Timeout with explicit handling | Returns `Error(E)` (does NOT return bottom) |
| Timeout without handling       | Logically returns bottom                    |

This ensures **liveness properties can be proven**: no effect can block indefinitely without explicit modeling.

______________________________________________________________________

## 10. Browser and WASM Deployment

### Browser Runtime

Browser deployments may be WASM-first with a thin JS harness, or they may rely on more substantial
JS or TS glue when the platform requires it.

- Rendering can occur in Rust, WASM, JS, or a hybrid arrangement
- Framework use is a backend choice, not something ruled out by the morphology
- The key boundary question is which parts remain pure descriptions and which browser behaviors are
  treated as runtime assumptions

### Optional DOM Harness

If absolutely necessary, a DOM harness can receive a regular stream of immutable frames:

- Creates an oracle for all JS I/O
- Models JS I/O as events → effects
- Maintains a pure model on the inside while DOM and JS integration remain outside the purity
  boundary and usually outside the proof boundary

______________________________________________________________________

## 11. Domain-Specific Frameworks

### Framework Architecture

Domain-specific frameworks are often **libraries over the pure representation layer**, commonly in
Haskell today but not conceptually limited to it.

These pure functional libraries translate higher-level abstractions for domain types:

- Web service abstractions
- UI I/O abstractions
- Database query builders
- API client generators

### Collective Behavior

The system behaves collectively as a distributed system based on:

- typed message protocols, including Paxos-style consensus when agreement semantics require it
- Well-defined purity and proof boundaries

### Extension Pattern

New capabilities extend via this pattern:

- New APIs
- Device drivers
- Edge devices
- Domain-specific UI frameworks

______________________________________________________________________

## 12. Infrastructure as Effects

Infrastructure deployment can be modeled as **one effect family** in the pure representation layer.

### Deployment Mechanisms

| Mechanism                                           | Modeled As   |
| --------------------------------------------------- | ------------ |
| SSH-based remote configurations                     | Pure effects |
| REST API calls to cloud providers (AWS, GCP, Azure) | Pure effects |
| Security rules                                      | Pure effects |
| Secrets management                                  | Pure effects |
| State tracking systems                              | Pure effects |

### IaC Scope

The morphology can support an Infrastructure-as-Code posture when the relevant provider effects,
runtime contracts, and deployment assumptions are defined clearly enough.

- It may replace third-party tools for some environments
- It may also coexist with them when that is the more practical boundary choice
- The important point is that infrastructure state and deployment intent can still be modeled as
  pure types before crossing into imperative adapters

### OS Kernels and the Proof Boundary

OS kernels generally fall **outside the proof boundary**. Pure workflow logic can still live inside
the purity boundary while running on such systems, and runtimes may remain inside the proof
boundary only insofar as their contracts are modeled and verified.

**Why?** Unmodeled failures caused by impure or unproved behavior at the OS level must be handled
by the surrounding distributed protocol. In some systems that may mean Byzantine Paxos or another
fault-tolerant consensus model; in others it may mean a different recovery or containment strategy.

______________________________________________________________________

## Cross-References

- [intro.md](intro.md) — Effectful compiler morphology overview and consolidated references
- [jit.md](jit.md) — JIT and staged lowering in the compiler morphology
- [consensus.md](consensus.md) — Formal methods for distributed consensus
- [proof_boundary.md](proof_boundary.md) — Philosophical foundation for verification limits
- [boundary_model.md](../engineering/boundary_model.md) — Detailed boundary model architecture
