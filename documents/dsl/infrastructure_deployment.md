# Infrastructure Deployment: Nodes, Messages, and Pure Effects

**Status**: Reference only
**Supersedes**: none
**Referenced by**: intro.md

> **Purpose**: Define Effectful's unified model for distributed systems where nodes (UI or server) communicate via Paxos messages, with infrastructure deployment as just another effect in the pure language.
> **Authoritative Reference**: [DSL Intro](intro.md)

______________________________________________________________________

## SSoT Link Map

| Need                | Link                                               |
| ------------------- | -------------------------------------------------- |
| Effectful overview  | [Effectful DSL Hub](intro.md)                      |
| Boundary model      | [Boundary Model](../engineering/boundary_model.md) |
| Consensus protocols | [Consensus](consensus.md)                          |
| JIT compilation     | [JIT Compilation](jit.md)                          |

______________________________________________________________________

## 1. The Effectful Model: One Language, One Distributed System

**Effectful is a high-level application language for writing high-quality UX and software, where everything is modeled as an abstract distributed system with a global interpreter of pure effects.**

This single unifying idea drives the entire system:

- **Effects are pure types**; effect interpreters run them on "nodes"
- **A node is either a user-facing UI or a server**—both are internally safe and trusted
- **All communication into/out of nodes is modeled as Paxos messages**
- **One language** for UI, server logic, and infrastructure deployment
- The **two-stage Haskell→Rust effect interpreter** is the purity boundary

### What This Means in Practice

Effectful is the same language for:

- **User interfaces** (via peripheral I/O effects)
- **Server logic** (business rules, data processing)
- **Event-driven infrastructure deployment rules** (provisioning, configuration)

The distinction between "frontend" and "backend" becomes obsolete. Logic is freely optimized to execute where it is safe and permissioned to do so.

______________________________________________________________________

## 2. Nodes: The Abstract Device Representation

A **node** is an abstract representation of a device in Effectful's distributed system model.

### Two Node Types

| Type          | Description                               | Examples                                      |
| ------------- | ----------------------------------------- | --------------------------------------------- |
| **UI-facing** | User-facing interface with peripheral I/O | Phone, tablet, desktop, browser, smart device |
| **Server**    | Backend processing with JIT capability    | Cloud VM, container, bare metal server        |

### Node Properties

- **Internally safe and trusted zone**: Within a node, code is verified and trusted
- **Transport topology differs**: DNS, ingress rules, certificates, session cookies vary by deployment
- **Behind the purity boundary, all nodes are uniform**: Effectful sees no difference between node types

### Requirements to Run an Effectful Node

A device or machine can run one or more Effectful nodes if:

1. **Can deploy a binary built in Haskell/Rust** (native or WASM)
1. **Rust can talk to device drivers** for hardware and/or platform-native APIs

This completely decouples the server/client relationship from where code actually runs. There is still a global compute DAG, meaning arbitrary amounts of compute can happen on any node if there is reason to do so:

- Better UX (responsive local interactions)
- Lower latency (compute near data)
- Reducing server loads (distribute work)

______________________________________________________________________

## 3. The Whitelist Security Model

A robust, expressive **whitelist-based security model** runs compositionally throughout pure logic.

### The Whitelist Monad

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

## 4. Haskell's Role: Thunk Performance Optimizer

**Haskell's main job is thunk performance optimization** according to rules in the Dhall config.

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

Monads are heavily utilized for:

- Expressing arbitrary pure compute graphs
- **Security whitelist monad** (compositional security)
- **Effect timeout wrappers** (explicit timeout behavior, can optionally return `Success(T)`)

**Every thunk is a pure representation of effects**, assembled by Haskell.

______________________________________________________________________

## 5. The Purity Boundary: Memory Semantics and Foreign Call Contract

### Purity Extends Through Generated Rust

Because Rust code is **Haskell-generated using a TLA+-verified transpiler**, the purity boundary continues through the shared immutable memory contract. This is not a "break" in purity—it's a **verified extension** of it.

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
- **Completely clean purity chain** runs through Haskell and Rust EI, up until side effects run
- **Purity means correctness is self-verifying**: a Haskell binary created via GHC is a self-verified effect system

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

**The thunk pipeline flowing out of Haskell is Effectful's formal purity boundary.** The thunk pipeline is safe and trusted.

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
- EI must behave purely up to the purity boundary

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

The transport layer is **not explicitly modeled** in Effectful. Instead:

- Network interface is at the **proof boundary**
- Rust interacts with network driver in the course of interpreting its own effects
- Abstract message types map to real-world transport

### Message Type Mapping

| Abstract Message Type | Real-World Transport                |
| --------------------- | ----------------------------------- |
| Asynchronous          | UDP packets, fire-and-forget HTTP   |
| Partially synchronous | TCP with timeouts, WebSocket        |
| Synchronous           | Request-response REST, blocking RPC |

### Generalized Paxos

Effectful's generalized Paxos handles multiple message types:

- **Asynchronous** messages
- **Partially synchronous** messages
- **Synchronous** messages

This allows the appropriate abstractions at the transport layer while maintaining uniform semantics at the purity boundary.

______________________________________________________________________

## 8. JIT and the Filesystem Model

### Server Node Definition

**A server node is defined exclusively by its JIT capability**: it can do JIT compilations of generated Rust code in order to leverage Haskell's compute graph optimizer as a JIT-time performance operator for implementations of specific Rust effects.

### JIT Compilation

On nodes with compilers (servers), Haskell may write Rust implementations of thunks with additional logic:

- Haskell's compute graph optimizer analyzes the thunk
- Generates optimized Rust code
- Rust compiles and caches the result

### The Filesystem Model

A pure type representing the filesystem:

- **Immutable but extendable** (immutable hash table or similar)
- Rust is responsible for JITs and caching them
- Between executing thunks, Rust essentially updates itself
- Shared immutable hash table as option for JIT cache

______________________________________________________________________

## 9. Effects and Timeouts

### Effect Semantics

Effects are the pure language which crosses the purity boundary (but not necessarily the proof boundary).

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

Browser deployments **don't use DOM or JS** except for thin boilerplate to download and install the WASM SPA.

- All rendering occurs in Rust as modeled effects (thunks from Haskell)
- No framework dependencies (React, Vue, etc.)
- Pure effect-based rendering model

### Optional DOM Harness

If absolutely necessary, a DOM harness can receive a regular stream of immutable frames:

- Creates an oracle for all JS I/O
- Models JS I/O as events → effects
- Maintains purity boundary while interfacing with DOM

______________________________________________________________________

## 11. Domain-Specific Frameworks

### Framework Architecture

Domain-specific frameworks are **Haskell libraries installed optionally**.

These pure functional libraries translate higher-level abstractions for domain types:

- Web service abstractions
- UI I/O abstractions
- Database query builders
- API client generators

### Collective Behavior

The system behaves collectively as a distributed system based on:

- Paxos consensus
- Well-defined purity and proof boundaries

### Extension Pattern

New capabilities extend via this pattern:

- New APIs
- Device drivers
- Edge devices
- Domain-specific UI frameworks

______________________________________________________________________

## 12. Infrastructure as Effects

Infrastructure deployment is **just another set of effects** in the pure language.

### Deployment Mechanisms

| Mechanism                                           | Modeled As   |
| --------------------------------------------------- | ------------ |
| SSH-based remote configurations                     | Pure effects |
| REST API calls to cloud providers (AWS, GCP, Azure) | Pure effects |
| Security rules                                      | Pure effects |
| Secrets management                                  | Pure effects |
| State tracking systems                              | Pure effects |

### Self-Sufficient IAC

Effectful is a **full-fledged Infrastructure-as-Code system**:

- No third-party tools (Terraform, Pulumi, Ansible)
- Leverages the Haskell effect interpreter every Effectful node holds
- All infrastructure state modeled as pure types

### OS Kernels and the Proof Boundary

OS kernels generally fall **outside the proof boundary**. However, software running on them may be behind the purity and proof boundary anyway.

**Why?** Unmodeled failures caused by impure/unproven behavior at the OS level can be resolved in the pure, provable distributed system at the **consensus level**. Byzantine Paxos is the sufficient model for handling unknown failure states.

______________________________________________________________________

## Cross-References

- [intro.md](intro.md) — Effectful language overview and consolidated references
- [jit.md](jit.md) — JIT compilation from Haskell to Rust
- [consensus.md](consensus.md) — Formal methods for distributed consensus
- [proof_boundary.md](proof_boundary.md) — Philosophical foundation for verification limits
- [boundary_model.md](../engineering/boundary_model.md) — Detailed boundary model architecture
