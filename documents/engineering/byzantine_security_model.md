# Byzantine Security Model: Distributed Trust

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: architecture.md, dsl/intro.md, boundary_model.md

> **Purpose**: Document the pure security model for distributed systems, based on Byzantine fault tolerance principles. Security is modeled as types within the purity boundary, making unsafe states unrepresentable.

______________________________________________________________________

## SSoT Link Map

| Need                      | Link                                             |
| ------------------------- | ------------------------------------------------ |
| Effectful overview        | [Effectful DSL Hub](../dsl/intro.md)             |
| Proof boundary philosophy | [Proof Boundary Essay](../dsl/proof_boundary.md) |
| Boundary model            | [Boundary Model](boundary_model.md)              |
| Consensus protocols       | [Consensus](../dsl/consensus.md)                 |

______________________________________________________________________

## 1. The Byzantine Problem

### 1.1 Leslie Lamport's Insight

In 1982, Lamport posed the Byzantine Generals problem: how can distributed nodes reach agreement when some may be faulty or malicious?

The key insight: **you cannot rely on any single message being truthful**. Any node may:

- Send conflicting messages to different recipients
- Fail to send messages
- Send messages at unexpected times
- Lie about its state

### 1.2 Why This Matters for Effectful

Traditional security relies on network boundaries:

- Firewalls block unauthorized traffic
- VPNs create trusted tunnels
- Internal networks are assumed safe

These defenses live **outside the proof boundary**. We cannot formally verify them.

Effectful's approach: model security **inside the purity boundary** as types. If a state is insecure, it cannot be represented.

______________________________________________________________________

## 2. Security Within the Purity Boundary

### 2.1 Two Node Types

Effectful's security model recognizes two kinds of nodes:

| Node Type        | Characteristics                                            |
| ---------------- | ---------------------------------------------------------- |
| **Edge Devices** | User-controlled, potentially hostile, limited trust        |
| **Servers**      | Operator-controlled, high trust, reachable via public APIs |

### 2.2 Message-Based Security

All security is modeled through messages:

```haskell
-- Every message carries its origin and credentials
data Message = Message
  { origin     :: NodeId
  , signature  :: Signature
  , payload    :: Payload
  , timestamp  :: Timestamp
  }

-- Message validation is pure
validateMessage :: PublicKey -> Message -> Either ValidationError ValidatedMessage
```

Security properties are checked at the type level:

- A function requiring `ValidatedMessage` cannot receive unvalidated input
- A function requiring `AuthorizedRequest` cannot bypass authorization

### 2.3 Trust as Types

Trust levels are explicit in the type system:

````haskell
-- Different levels of trust
data Untrusted a    -- From unknown source
data Authenticated a -- Origin verified (signature valid)
data Authorized a   -- Permission checked

-- Functions require appropriate trust level
processUserRequest :: Authorized Request -> Effect Response
accessSensitiveData :: Authorized (Permission Read Data) -> Effect Data
```text

---

## 3. Threat Modeling as Types

### 3.1 Making Threats Explicit

Every threat becomes a type:

```haskell
data ThreatModel
  = Eavesdropping      -- Message contents exposed
  | Tampering          -- Message contents modified
  | Spoofing           -- False identity claimed
  | Replay             -- Old message resubmitted
  | DoS                -- Excessive requests
  | MaliciousNode      -- Node actively hostile
````

### 3.2 Defenses as Type Constraints

Defenses are expressed as type requirements:

| Threat         | Defense             | Type Constraint        |
| -------------- | ------------------- | ---------------------- |
| Eavesdropping  | Encryption          | `Encrypted payload`    |
| Tampering      | Signatures          | `Signed message`       |
| Spoofing       | Authentication      | `Authenticated sender` |
| Replay         | Nonces              | `Fresh nonce`          |
| DoS            | Rate limiting       | `RateLimited request`  |
| Malicious node | Byzantine tolerance | `Quorum response`      |

### 3.3 Unrepresentable Insecure States

The goal is to make insecure states impossible to construct:

````haskell
-- This function CANNOT be called with an unauthenticated request
-- because the type system prevents it
processPayment :: Authorized (Permission Admin Finance) -> PaymentRequest -> Effect PaymentResult

-- Attempting to bypass:
-- processPayment (Untrusted request)  -- TYPE ERROR: Expected Authorized, got Untrusted
```text

---

## 4. Relationship to Industry-Standard Security

### 4.1 Complement, Not Replace

Effectful's Byzantine model **complements** industry-standard security:

| Layer | Industry Standard | Effectful Model |
|-------|-------------------|-----------------|
| Transport | TLS/SSL | Assumed (outside proof boundary) |
| Network | Firewalls, ingress controllers | Assumed (outside proof boundary) |
| Identity | OAuth, JWT, certificates | Mapped to pure types |
| Authorization | RBAC, ABAC | Pure permission checking |
| Application | Business rules | Type-safe constraints |

### 4.2 Assumption Documentation

We document what we assume about lower layers:

````

ASSUMPTION: TLS provides confidentiality and integrity
DEPENDS ON: Valid certificates, modern cipher suites
TLA+ PROPERTY: MessageConfidentiality, MessageIntegrity
FAILURE MODE: Man-in-the-middle attack
MITIGATION: Certificate pinning, HSTS

````python

---

## 5. Byzantine Fault Tolerance Patterns

### 5.1 Quorum-Based Decisions

For critical operations, require agreement from multiple nodes:

```haskell
-- Require 2f+1 agreeing responses for f Byzantine faults
data QuorumResponse = QuorumResponse
  { responses :: NonEmpty ValidatedResponse
  , agreement :: QuorumAgreement
  }

-- Only proceed if quorum is satisfied
executeWithQuorum :: QuorumResponse -> Effect Result
````

### 5.2 Cryptographic Verification

All identity claims are cryptographically verified:

```haskell
-- Signature verification is pure
verifySignature :: PublicKey -> Message -> Signature -> Bool

-- Verified messages carry proof
data VerifiedMessage = VerifiedMessage
  { message :: Message
  , proof   :: SignatureProof  -- Cannot be constructed without valid signature
  }
```

### 5.3 State Machine Replication

Critical state uses replicated state machines with Byzantine agreement:

````haskell
-- State machine with Byzantine consensus
data ConsensusState = ConsensusState
  { value      :: Value
  , epoch      :: Epoch
  , signatures :: Map NodeId Signature  -- Proof of agreement
  }
```text

---

## 6. ADT-Based Failure Modes

### 6.1 Security Failures as Types

All security failures are typed:

```haskell
data SecurityError
  = AuthenticationFailed AuthFailure
  | AuthorizationDenied Permission
  | SignatureInvalid SignatureError
  | NonceReplay NonceId
  | QuorumNotReached Int Int  -- got, needed
  | CertificateExpired Timestamp
  | RateLimitExceeded Rate
````

### 6.2 No Silent Failures

Every security check produces a result:

```haskell
-- example code
authenticate :: Credentials -> Either AuthenticationError AuthenticatedUser
authorize :: AuthenticatedUser -> Permission -> Either AuthorizationError Authorized
validate :: Message -> Either ValidationError ValidatedMessage
```

### 6.3 Exhaustive Handling

Pattern matching ensures all cases are handled:

````haskell
-- example code
case authenticate credentials of
  Left (InvalidPassword _) -> respondUnauthorized
  Left (UserNotFound _) -> respondUnauthorized  -- Same response to prevent enumeration
  Left (AccountLocked reason) -> respondLocked reason
  Left (MFARequired) -> promptMFA
  Right user -> proceed user
```text

---

## 7. Implementation Guidelines

### 7.1 Within Purity Boundary

Security logic is pure:

```haskell
-- Pure authorization check
checkPermission :: User -> Resource -> Action -> Either PermissionError ()
checkPermission user resource action =
  if hasPermission user resource action
    then Right ()
    else Left (PermissionDenied user resource action)
````

### 7.2 At Proof Boundary

Cryptographic operations are Rust runners:

```rust
// Runner for signature verification
fn verify_signature(effect: VerifySignature) -> Result<SignatureProof, CryptoError> {
    // ASSUMPTION: libsodium correctly implements Ed25519
    let valid = sodium::sign::verify_detached(
        &effect.signature,
        &effect.message,
        &effect.public_key,
    );
    if valid {
        Ok(SignatureProof::new())
    } else {
        Err(CryptoError::InvalidSignature)
    }
}
```

### 7.3 Outside Proof Boundary

Network security is assumed and documented:

````
## Transport Security Assumptions

ASSUMPTION: TLS 1.3 provides secure channel
DEPENDS ON: System certificate store, cipher suite configuration
TLA+ PROPERTY: ChannelSecurity
FAILURE MODE: Downgrade attack, certificate compromise
MITIGATION: TLS 1.3 only, certificate pinning, HSTS preload
```text

---

## 8. Testing Security

### 8.1 Property-Based Testing

Security properties are tested exhaustively:

```haskell
-- Property: unauthorized requests are always rejected
prop_unauthorized_rejected :: UnauthorizedRequest -> Property
prop_unauthorized_rejected req =
  processRequest req === Left AuthorizationDenied

-- Property: valid signatures always verify
prop_valid_signature :: KeyPair -> Message -> Property
prop_valid_signature (pub, priv) msg =
  let sig = sign priv msg
  in verify pub msg sig === True
````

### 8.2 Attack Simulation

Known attack patterns are tested:

| Attack               | Test                       |
| -------------------- | -------------------------- |
| Replay               | Submit same nonce twice    |
| Spoofing             | Invalid signature          |
| Privilege escalation | Request higher permissions |
| Timing               | Measure response times     |
| Injection            | Malformed inputs           |

### 8.3 Conformance Testing

Security protocols are TLA+ verified:

```tla
\* Safety: No unauthorized access
NoUnauthorizedAccess == \A req \in Requests:
    processed[req] => authorized[req.user, req.resource]

\* Safety: Nonces are never reused
NoNonceReuse == \A n1, n2 \in UsedNonces:
    n1 = n2 => n1.id = n2.id
```

______________________________________________________________________

## Cross-References

- [dsl/intro.md](../dsl/intro.md) — Effectful language overview
- [dsl/proof_boundary.md](../dsl/proof_boundary.md) — Philosophical foundation
- [dsl/consensus.md](../dsl/consensus.md) — Consensus protocols
- [boundary_model.md](boundary_model.md) — Where security fits in architecture
- [verification_contract.md](verification_contract.md) — TLA+ verification of security properties
