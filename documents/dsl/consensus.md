# Formal Methods for Distributed Consensus and Blockchains

**Status**: Reference only
**Supersedes**: none
**Referenced by**: intro.md

> **Purpose**: Apply the proof boundary and purity boundary framework to distributed consensus protocols, covering Paxos, PBFT, hybrid trust models, and DAG-based systems.
> **Authoritative Reference**: [Effectful DSL Hub](intro.md#7-references)

______________________________________________________________________

## Consensus in the Boundary Model

This document applies Effectful's boundary model to distributed consensus:

| Boundary                   | Consensus Components                                                              |
| -------------------------- | --------------------------------------------------------------------------------- |
| **Purity Boundary**        | State machine logic, message handling, vote aggregation (Haskell)                 |
| **Proof Boundary**         | Protocol transitions, safety/liveness properties, quorum intersection (TLA+/Rust) |
| **Outside Proof Boundary** | Network I/O, cryptographic operations, peer discovery (assumptions)               |

The key insight is that consensus protocols are ideal candidates for formal verification—their safety and liveness properties can be precisely specified and model-checked. See [intro.md](intro.md) for the full boundary model.

______________________________________________________________________

*Audience:* engineers who want **spec-first correctness** (e.g., **TLA+ / PlusCal**, model checking, and—when necessary—machine-checked proofs) and who care about **minimizing the trusted computing base (TCB)**.

______________________________________________________________________

## Table of contents

1. [What you’re trying to achieve](#what-youre-trying-to-achieve)
1. [System model: what must be specified](#system-model-what-must-be-specified)
1. [Fault models & “trust levels” across nodes](#fault-models--trust-levels-across-nodes)
1. [Consensus problem taxonomy (what you prove)](#consensus-problem-taxonomy-what-you-prove)
1. [Consensus families: Paxos, PBFT, Raft/Zab, modern BFT](#consensus-families-paxos-pbft-raftzab-modern-bft)
1. [Hybridizing trust: “Paxos ↔ PBFT” and beyond](#hybridizing-trust-paxos--pbft-and-beyond)
1. [Blockchains vs classical consensus (formal-system vs classical)](#blockchains-vs-classical-consensus-formal-system-vs-classical)
1. [DAG systems + blockchains: composition & proof boundaries](#dag-systems--blockchains-composition--proof-boundaries)
1. [Where the proof boundary falls (TCB & assumptions)](#where-the-proof-boundary-falls-tcb--assumptions)
1. [A practical TLA+ workflow for consensus systems](#a-practical-tla-workflow-for-consensus-systems)
1. [Appendices: checklists & interface contracts](#appendices-checklists--interface-contracts)
1. [References](#references)

______________________________________________________________________

## What you’re trying to achieve

When you say:

- “follow formal methods”
- “use TLA+ to prove correctness”
- “avoid third-party software not built with formal methods/proofs”
- “mixed trustworthiness across nodes”

you’re implicitly optimizing for:

1. **Safety invariants that never break** (e.g., agreement, no double-commit).
1. **Explicit liveness assumptions** (what you *must* assume about timing/fairness).
1. **Small, auditable trust base** (crypto/hardware/network assumptions clearly isolated).
1. **Compositionality** (prove layers separately, then prove the interface contract).

A system that “feels correct” operationally is not what you want—you want something you can **pin down** and **check**.

______________________________________________________________________

## System model: what must be specified

Formal methods pay off when you make the environment explicit. For consensus, you typically need to model:

### 1) Processes (replicas, leaders, clients)

- Local state (logs, ballots/terms, prepared/committed sets, views)
- Crash/restart semantics (if any)
- Byzantine behaviors (if any): equivocation, forging, replay, censorship

### 2) Network

- Asynchronous vs partially synchronous vs synchronous timing
- Message properties: loss, duplication, reordering
- Authentication model (none / MAC / signatures)
- Adversarial scheduling (can the adversary delay honest messages forever?)

### 3) Fault model

- Crash faults (fail-stop)
- Omission faults (drop send/receive)
- Byzantine faults (arbitrary deviations)
- Correlated failures (shared power/domain, compromised build pipeline, etc.)

### 4) Membership and reconfiguration

- Fixed committee vs dynamic membership
- How “who votes” is agreed upon
- What happens during reconfiguration (joint consensus, epoch transitions, etc.)

### 5) State machine / application layer

- Deterministic execution requirements
- Transaction validity rules
- Conflict model (commutative effects vs strict total order)

______________________________________________________________________

## Fault models & “trust levels” across nodes

“Some nodes are trustworthy and others are not” only becomes useful once you choose *what property is trusted*. Here’s a concrete trust ladder:

### Trust level 0: **Untrusted**

- Node may behave arbitrarily (Byzantine).
- You assume only cryptographic unforgeability (if used).

### Trust level 1: **Authenticated but still Byzantine**

- Messages can be attributed to a sender (signatures/MACs), but sender can still lie/equivocate.

### Trust level 2: **Non-equivocating**

- Node cannot send conflicting statements for the same step (e.g., via a trusted counter, attestation, or protocol-enforced non-equivocation).
- This *can* reduce quorum sizes in some designs, but shifts trust to hardware / a small trusted module.

### Trust level 3: **Crash-only (CFT)**

- Node follows the protocol or crashes (Paxos/Raft assumptions).

### Trust level 4: **Correct and available (idealized)**

- Useful for modeling “infrastructure services” (time, randomness beacons, etc.), but should be used sparingly.

**Implication:**\
Hybrid systems aren’t “Paxos + PBFT”; they’re **quorum & intersection rules that reflect this ladder**.

______________________________________________________________________

## Consensus problem taxonomy (what you prove)

Consensus terms get muddled; formal specs force clarity:

### 1) **Consensus (single-shot)**

Agree on a single value `v` (or decide `NoOp`).

**Safety properties**

- *Agreement:* no two correct processes decide different values
- *Validity:* decided value meets criteria (proposed, or well-formed, etc.)
- *Integrity:* decide at most once

### 2) **Atomic broadcast / total order broadcast**

All correct processes deliver the same sequence of messages in the same order.

### 3) **State Machine Replication (SMR)**

Replicate a deterministic state machine by agreeing on an ordered log of commands.

**Most real systems** are SMR: “multi-shot consensus” over log entries.

______________________________________________________________________

## Consensus families: Paxos, PBFT, Raft/Zab, modern BFT

### Paxos (and Multi-Paxos): the CFT baseline

**What it assumes**

- Crash faults (not arbitrary Byzantine behavior)
- Asynchronous network for safety; liveness requires additional assumptions

**Why it’s great for formal methods**

- Small core, clean invariants (“chosen value” uniqueness)
- Natural refinement path: single-decree → multi-decree
- Canonical references and formal specs exist

**Formal-methods pros**

- Minimal semantic surface area
- Strong, stable invariants
- Great “base layer” for refinement into production variants

**Formal-methods cons**

- Production additions (leadership leases, reconfiguration, log compaction) expand the proof surface
- Liveness proofs depend on explicit fairness / partial synchrony assumptions

*(Primary references: Lamport’s Paxos paper and related formal material.)*

### PBFT (and classical BFT SMR)

**What it assumes**

- Byzantine faults (replicas may lie/equivocate)
- Typically needs `n ≥ 3f+1` replicas to tolerate `f` Byzantine faults (classic quorum intersection argument)

**Formal-methods pros**

- Crisp safety goal: no two different requests can be committed at the same log position
- Authentication (MAC/signatures) provides clean “attribution” in specs

**Formal-methods cons**

- View-change logic is a major proof burden
- You must be precise about adversary power (network scheduling + Byzantine behavior)
- Crypto becomes part of the TCB unless abstracted carefully

*(Primary reference: Castro & Liskov PBFT.)*

### Raft (CFT, log replication as first-class)

Raft is often easier to *implement and audit* than Paxos and is designed for understandability.

**Formal-methods pros**

- Explicit log/term structure; clearer state machine
- Specs map well to implementations

**Formal-methods cons**

- Larger state surface than Paxos core
- Many “engineering” concerns (snapshots, membership, timeouts) are integral, not optional

*(Primary reference: Ongaro & Ousterhout.)*

### Zab (ZooKeeper Atomic Broadcast)

Zab is highly optimized for ZooKeeper’s atomic broadcast use-case.

**Formal-methods note**

- Narrower scope than “general consensus library”
- If you aren’t adopting ZooKeeper wholesale, you’ll likely be re-specifying semantics anyway.

### Modern BFT for “blockchain-style” finality (HotStuff, Tendermint, etc.)

Modern BFT protocols often:

- preserve **deterministic finality**
- improve responsiveness / communication patterns
- present consensus in a “chained” or pipelined form that resembles block production

HotStuff is notable for explicitly bridging classical BFT and blockchains. It targets partial synchrony and uses linear communication patterns under certain conditions.

*(Primary references: HotStuff; Tendermint.)*

______________________________________________________________________

## Hybridizing trust: Paxos ↔ PBFT and beyond

There are multiple legitimate “hybrid” strategies; which is right depends on your trust model.

### Strategy A: “Byzantize” a Paxos-like core by refinement (formal-friendly)

A particularly formal-methods-aligned approach is to start with a Paxos-style consensus core and refine it into a BFT protocol—capturing PBFT-like behavior as an implementation of a more abstract consensus spec.

Lamport has an explicit formalization pathway along these lines (“Byzantizing Paxos by Refinement”), including PlusCal/TLA+ specs and machine-checked proofs.

**Why this matters**

- It gives you a *systematic proof story*: Paxos-level spec → BFT refinement
- You can localize “Byzantine-ness” to specific actions and invariants
- You can reason about PBFT-like algorithms without treating them as alien artifacts

### Strategy B: Hybrid quorums / weighted trust

If some nodes are genuinely more trusted (e.g., different administrative domains, hardened builds, audited hardware), you can use **quorum systems** that reflect that:

- weighted voting
- trust-aware quorum intersection
- hybrid quorum designs

The core idea is: safety depends on *intersection containing at least one correct* (or sufficiently trusted) member—your quorum definition encodes your trust assumptions.

### Strategy C: “Mostly CFT, but tolerate Byzantine when the network behaves” (XFT-style)

Some designs try to remain close to CFT costs while gaining resilience against certain Byzantine behaviors under more constrained adversary models (e.g., avoiding worst-case combinations of network asynchrony and Byzantine behavior). This can be attractive but you must be explicit about the threat model you are (and are not) covering.

### Strategy D: Trusted non-equivocation components

If you assume a small trusted module that prevents equivocation, you can sometimes reduce the replication factor needed for BFT-style safety. This shifts the question from “do I trust all nodes?” to “do I trust a tiny component on each node?”

**Formal-methods warning:**\
This is a classic place where the proof boundary moves: your safety proof now depends on the module’s contract (“cannot sign two conflicting statements for the same counter value”), not just on protocol logic.

______________________________________________________________________

## Blockchains vs classical consensus (formal-system vs classical)

“Blockchain” is overloaded. Here are two archetypes:

### A) Formal-system blockchain (permissioned, deterministic finality)

Think:

- fixed or slowly changing committee of identified validators
- BFT consensus (PBFT/HotStuff/Tendermint-like) produces blocks
- hash-chaining + signatures provide auditability and tamper evidence

**Properties**

- Finality is deterministic once a block is committed/finalized
- Safety proofs look like SMR/atomic broadcast proofs
- Cryptographic objects (hashes/signatures) are typically *witnesses*, not the core safety engine

**Formal-methods sweet spot**

- You can specify and verify this like “SMR over blocks”
- You can keep economics/incentives out of the safety proof

### B) “Classical” public blockchain (permissionless, adversarial membership)

Think PoW/permissionless PoS families:

- open participation / Sybil resistance
- probabilistic finality (reorgs)
- safety relies on assumptions about adversary resources + network + incentives

**Properties**

- Proof statements are often probabilistic (“with high probability after k confirmations…”)
- The protocol boundary includes economics (or at least adversary resource assumptions)
- Formalizing “eventual consensus” becomes a probabilistic / adversarial scheduling problem

**Formal-methods reality check**

- You *can* formalize such systems, but the proof burden and modeling decisions explode.
- Many teams instead use: permissioned BFT finality + separate membership mechanism (e.g., a stake registry, governance chain, etc.).

______________________________________________________________________

## DAG systems + blockchains: composition & proof boundaries

You asked specifically about “where the proof boundary falls when an effectful DAG system interacts with classical blockchain, in the context of a broader consensus algorithm.”

The key is to separate **three different DAG roles**:

### Role 1: DAG as a *data availability / dissemination layer* (pre-consensus)

Example pattern: separate “get data to everyone reliably” from “agree on order.” Narwhal is explicitly a DAG-based mempool for high-throughput dissemination; it can be composed with an ordering protocol (e.g., HotStuff) or with an async ordering protocol (e.g., Tusk).

**What you prove about the DAG layer**

- Availability: if a correct node includes a payload, other correct nodes can eventually retrieve it
- Causal structure: references form a DAG (no cycles), and parents are present before children
- Non-equivocation properties (if applicable): a node can’t produce two conflicting vertices for the same round/slot (or, if it can, the protocol detects it)

**Interface contract to consensus**

- `DeliverableVertices`: a set (or stream) of vertices that are valid and retrievable
- `CertifiedPayloads`: payload digests that meet some threshold property

Consensus then proves:

- a total order (or finalized chain) over items drawn from that DAG stream
- safety does not depend on DAG liveness, only on DAG *integrity* and *availability assumptions*

### Role 2: DAG as an *ordering mechanism* (DAG-based atomic broadcast)

Some protocols build a DAG and then compute a total order (or consistent order) from it, sometimes with randomized components. DAG-Rider is in this family and emphasizes a two-layer structure: build a structured DAG, then derive ordering.

**What you prove**

- Agreement on derived order (or equivalent atomic broadcast property)
- That local DAG views lead to consistent decisions among correct nodes under the model assumptions

**Proof boundary**

- The DAG is not “just a mempool”; it *is part of consensus*. Your spec must include the DAG-building actions and the ordering/decision rule as one protocol (or as well-defined layers with a refinement relation).

### Role 3: DAG as an *execution graph* (“effectful DAG”)

Here “DAG” refers to dependency structure among state transitions (e.g., transactions that commute, or conflict graphs). This is where “effects” matter:

- If operations **commute**, you can allow concurrent execution and later linearize.
- If operations **conflict**, you must impose an order consistent with dependencies.

**Two common compositions with a blockchain**

1. **DAG execution + chain finality**
   - DAG schedules parallel execution subject to dependencies
   - The chain commits a *linearization* (or commits a canonical dependency-respecting order)
1. **DAG commitments + chain anchoring**
   - DAG produces intermediate checkpoints/state roots
   - Chain anchors these roots for auditability/finality

**Formal interface contract**

- The DAG layer must expose a deterministic function:
  - `Linearize(DAG, Policy) -> Sequence`
  - or a deterministic “conflict-resolution” policy
- The chain layer commits either:
  - the resulting sequence, or
  - a Merkle root/state root + enough witnesses to re-derive the linearization

**Where proofs often fail**

- Non-determinism at the boundary (different nodes choose different “valid” linearizations)
- Insufficiently specified conflict policy (tie-breaking, timestamps, proposer priority)
- “Effect validity” not preserved under reordering (e.g., read-write conflicts)

______________________________________________________________________

## Where the proof boundary falls (TCB & assumptions)

A formal proof is only as good as what you exclude from it. For consensus systems, draw the boundary explicitly:

### Inside the proof (you actually verify)

- Protocol state transitions
- Invariants: agreement, no double-commit, consistency of logs/chains
- Correctness of interface contracts between layers (DAG ↔ consensus ↔ execution)
- Reconfiguration logic (if included)

### Outside the proof (assumptions)

1. **Cryptography**
   - signatures unforgeable, hashes collision-resistant (usually modeled as perfect)
1. **Network model**
   - eventual delivery under partial synchrony, or fairness conditions for liveness
1. **Membership / identity**
   - key distribution, PKI, stake registry, etc.
1. **Hardware / trusted modules (if any)**
   - TEEs, monotonic counters, HSMs; these become critical assumptions
1. **Implementation & compilation chain**
   - bugs in runtime, compiler, OS, libraries
   - if you truly want “no unverified third party,” you need a plan for the whole stack (often unrealistic in full generality)

### Practical compromise (common in high-assurance systems)

- Prove the **protocol** and **critical interface boundaries**
- Keep dependencies small and auditable (tiny crypto libs, minimal OS surface, etc.)
- Add runtime checks that enforce assumptions (e.g., signature verification, monotonic counter checks)

______________________________________________________________________

## A practical TLA+ workflow for consensus systems

### Step 1: Write the *spec before the algorithm*

- Specify **safety** first (invariants)
- Decide whether you’re proving:
  - consensus, atomic broadcast, or SMR

### Step 2: Start with the smallest useful model

- Single-decree consensus
- Fixed membership
- Abstract crypto and network

### Step 3: Model check aggressively (TLC)

- Find counterexamples early
- Use small bounds to explore weird interleavings

### Step 4: Introduce refinements, one at a time

Typical refinement path:

1. abstract consensus
1. Paxos-like core
1. multi-shot log replication
1. leader optimization
1. reconfiguration
1. persistence / crash-recovery
1. performance features (batching, pipelining)

### Step 5: Prove key invariants (TLAPS or structured reasoning)

- Aim for proofs only after TLC has burned down the design bugs
- Keep proofs modular: layer invariants + interface invariants

### Step 6: Treat “DAG + chain + execution” as a contract-driven composition

You’ll usually want three specs:

- `DAGLayer`: availability + integrity + (optional) non-equivocation
- `OrderingLayer`: consensus/finality over references/digests
- `ExecutionLayer`: deterministic state transition and conflict rules

Then prove:

- `OrderingLayer` refines atomic broadcast over items provided by `DAGLayer`
- `ExecutionLayer` is deterministic given the ordered log (or deterministic linearization rule)

______________________________________________________________________

## Appendices: checklists & interface contracts

### A. Threat model checklist (write this down explicitly)

- [ ] Are faults **crash** or **Byzantine**?
- [ ] Are messages authenticated (MAC/signature)?
- [ ] Is the network asynchronous or partially synchronous for liveness?
- [ ] Can the adversary schedule the network while also corrupting nodes?
- [ ] Is membership fixed or dynamic? Who decides reconfiguration?
- [ ] What does “trustworthy node” mean: crash-only? non-equivocating? TEE-attested?

### B. Common safety invariants (templates)

**For SMR / replicated log**

- Prefix property: committed logs are prefix-related across correct replicas
- No double-commit: no two different entries committed at the same index/height
- State consistency: applying the committed log yields identical state at all correct replicas

**For BFT with quorums**

- Quorum intersection: any two commit quorums intersect in ≥ 1 correct replica (or in a set that suffices under your trust assumptions)
- Prepared/committed monotonicity under view changes

### C. Example interface contract: DAG mempool → BFT ordering

**DAG layer provides**

- `Vertex(v)` with fields `(author, round, parents, payloadDigest)`
- Validity predicate `ValidVertex(v)`:
  - parents exist
  - digest matches retrievable payload
  - (optional) author not equivocating at `(author, round)`

**Ordering layer assumes**

- If `ValidVertex(v)` is observed by one correct process, then eventually all correct processes can retrieve `v` and its payload (availability)
- `ValidVertex` is deterministic and checkable

**Ordering layer guarantees**

- A total order over payload digests that all correct replicas finalize
- Only digests that came from valid vertices can be finalized

### D. Example boundary: effectful DAG execution + chain

If execution is parallel and represented as a DAG of dependencies, then your chain layer must commit:

- either the *final linearization* (sequence), or
- enough information to deterministically derive it (policy + dependency edges + tie-breakers)

**Rule of thumb:**\
If two correct nodes can produce two different “valid” linearizations from the same committed artifact, you do **not** have a consensus system—you have “consensus plus a forkable executor.”

______________________________________________________________________

## Cross-References

- [intro.md](intro.md) — Effectful language overview and consolidated references
- [jit.md](jit.md) — JIT compilation from Haskell to Rust
- [proof_boundary.md](proof_boundary.md) — Philosophical foundation for verification limits
- [ml_training.md](ml_training.md) — Formal methods for distributed ML

> **Note**: For consensus protocol references (Byzantine Generals, Paxos, PBFT, Raft, HotStuff, etc.), see [intro.md#7-references](intro.md#7-references).
