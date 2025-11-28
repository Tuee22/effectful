# Mermaid Diagram Standards for HealthHub

> **Healthcare-specific diagram standards** ensuring universal compatibility and accessibility for medical workflows.

---

## Table of Contents

1. [Overview](#overview)
2. [Diagram Types](#diagram-types)
3. [Healthcare Patterns](#healthcare-patterns)
4. [Style Guide](#style-guide)
5. [Accessibility](#accessibility)
6. [Safe Subset](#safe-subset)
7. [Cross-References](#cross-references)

---

## Overview

### Purpose

Define Mermaid diagram standards for HealthHub documentation that:
- Render identically in **GitHub** and **VSCode**
- Follow healthcare accessibility guidelines (WCAG AA)
- Clearly visualize medical workflows and state machines

### Compatibility Principle

**Problem**: GitHub (Mermaid v10.8.0) and VSCode extensions (Mermaid v11+) have syntax differences.

**Solution**: Use only the safe subset documented here.

**Priority**: Universal compatibility > Visual features

### Orientation Guidelines

**Core Principle**: Always orient the largest axis vertically (TB direction) for readability.

**Rule of Thumb**: If your longest chain has more than 3 elements, use `flowchart TB`.

---

## Diagram Types

### 1. State Diagrams (Appointment Status)

**Use Case**: Visualize appointment state machine transitions.

```mermaid
flowchart TB
  Requested[Requested]
  Confirmed[Confirmed]
  InProgress[In Progress]
  Completed[Completed]
  Cancelled[Cancelled]

  Requested --> Confirmed
  Requested --> Cancelled
  Confirmed --> InProgress
  Confirmed --> Cancelled
  InProgress --> Completed
  InProgress --> Cancelled
```

**Why it works**: Clear top-to-bottom flow, solid arrows only.

### 2. Sequence Diagrams (Effect Program Execution)

**Use Case**: Show effect program flow with interpreter interactions.

```mermaid
sequenceDiagram
  participant Program as Effect Program
  participant Interpreter as Composite Interpreter
  participant DB as PostgreSQL

  Program->>Interpreter: yield GetPatientById
  Interpreter->>DB: SELECT patient
  DB-->>Interpreter: Patient row
  Interpreter-->>Program: send Patient
  Program->>Interpreter: yield CreateAppointment
  Interpreter->>DB: INSERT appointment
  DB-->>Interpreter: Appointment row
  Interpreter-->>Program: send Appointment
```

**Why it works**: Simple participants, solid/dashed arrows only, no complex blocks.

### 3. Flowcharts (Authorization Decision Trees)

**Use Case**: Visualize ADT pattern matching for authorization.

```mermaid
flowchart TB
  Start[Authorization State]
  CheckType{Check Type}
  Patient[PatientAuthorized]
  Doctor[DoctorAuthorized]
  Admin[AdminAuthorized]
  Unauthorized[Unauthorized - 403]

  Start --> CheckType
  CheckType -->|Patient| Patient
  CheckType -->|Doctor| Doctor
  CheckType -->|Admin| Admin
  CheckType -->|None| Unauthorized
```

**Why it works**: Diamond shapes for decisions, solid arrows, clear flow.

---

## Healthcare Patterns

### Pattern 1: Appointment State Machine

```mermaid
flowchart TB
  Requested[Requested - Patient submits request]
  Confirmed[Confirmed - Doctor approves]
  InProgress[In Progress - Appointment started]
  Completed[Completed - Visit finished]
  Cancelled[Cancelled - By patient or doctor]

  Requested -->|Doctor confirms| Confirmed
  Requested -->|Patient cancels| Cancelled
  Confirmed -->|Doctor starts visit| InProgress
  Confirmed -->|Patient cancels| Cancelled
  InProgress -->|Doctor completes| Completed
  InProgress -->|Emergency cancel| Cancelled

  style Requested fill:#e3f2fd
  style Confirmed fill:#c8e6c9
  style InProgress fill:#fff9c4
  style Completed fill:#a5d6a7
  style Cancelled fill:#ffcdd2
```

**Healthcare Context**: Appointment status transitions with color-coded states (blue → green → yellow → green, red for cancelled).

### Pattern 2: Prescription Creation with Interaction Checking

```mermaid
flowchart TB
  Start[Doctor creates prescription]
  CheckDoctor{Can Prescribe?}
  GetMeds[Get patient medications]
  CheckInteractions[Check drug interactions]
  HasInteractions{Interactions Found?}
  ReviewInteractions[Review interaction warnings]
  DoctorConfirms{Doctor Confirms?}
  CreatePrescription[Create prescription record]
  NotifyPatient[Notify patient via WebSocket]
  Denied[Deny - Doctor cannot prescribe]

  Start --> CheckDoctor
  CheckDoctor -->|can_prescribe=true| GetMeds
  CheckDoctor -->|can_prescribe=false| Denied
  GetMeds --> CheckInteractions
  CheckInteractions --> HasInteractions
  HasInteractions -->|No| CreatePrescription
  HasInteractions -->|Yes| ReviewInteractions
  ReviewInteractions --> DoctorConfirms
  DoctorConfirms -->|Yes| CreatePrescription
  DoctorConfirms -->|No| Denied
  CreatePrescription --> NotifyPatient
```

**Healthcare Context**: Medication interaction checking with doctor override capability.

### Pattern 3: Lab Result Critical Value Alert

```mermaid
sequenceDiagram
  participant Lab as Lab System
  participant API as HealthHub API
  participant DB as PostgreSQL
  participant Redis as Redis Pub/Sub
  participant Patient as Patient Portal

  Lab->>API: POST /lab-results (critical value)
  API->>DB: Insert lab result
  DB-->>API: Lab result created
  API->>DB: Mark critical flag
  API->>Redis: PUBLISH patient channel
  Redis->>Patient: WebSocket notification (CRITICAL)
  Patient->>Patient: Show audio alert
  Patient->>API: Acknowledge receipt
  API->>DB: Log acknowledgment
```

**Healthcare Context**: Critical lab result with guaranteed delivery and acknowledgment.

### Pattern 4: ADT Authorization Pattern Matching

```mermaid
flowchart TB
  Request[HTTP Request]
  GetToken[Extract JWT token]
  ValidateToken{Token Valid?}
  GetRole[Get user role from token]
  MatchRole{Match Role}
  LoadPatient[Load patient profile]
  LoadDoctor[Load doctor profile]
  ReturnPatient[Return PatientAuthorized]
  ReturnDoctor[Return DoctorAuthorized]
  ReturnAdmin[Return AdminAuthorized]
  Unauthorized[Return Unauthorized]

  Request --> GetToken
  GetToken --> ValidateToken
  ValidateToken -->|No| Unauthorized
  ValidateToken -->|Yes| GetRole
  GetRole --> MatchRole
  MatchRole -->|patient| LoadPatient
  MatchRole -->|doctor| LoadDoctor
  MatchRole -->|admin| ReturnAdmin
  MatchRole -->|unknown| Unauthorized
  LoadPatient -->|Found| ReturnPatient
  LoadPatient -->|Not found| Unauthorized
  LoadDoctor -->|Found| ReturnDoctor
  LoadDoctor -->|Not found| Unauthorized
```

**Healthcare Context**: JWT authentication → ADT authorization state resolution.

---

## Style Guide

### Color Coding

**Appointment States**:
- **Requested**: Light blue (#e3f2fd) - Initial state
- **Confirmed**: Light green (#c8e6c9) - Doctor approved
- **InProgress**: Light yellow (#fff9c4) - Active visit
- **Completed**: Green (#a5d6a7) - Successful completion
- **Cancelled**: Light red (#ffcdd2) - Terminal failure state

**Authorization States**:
- **PatientAuthorized**: Light blue (#e3f2fd)
- **DoctorAuthorized**: Light green (#c8e6c9)
- **AdminAuthorized**: Light purple (#e1bee7)
- **Unauthorized**: Light red (#ffcdd2)

### Node Shapes

| Shape | Use Case | Syntax |
|-------|----------|--------|
| **Rectangle** | Action, process step | `[Label]` |
| **Rounded** | Start/end state | `(Label)` |
| **Diamond** | Decision point | `{Label?}` |
| **Database** | Data store | `[(Label)]` |

### Arrow Types

**Only use these arrow types** (universal compatibility):

- `-->` Solid arrow (actions, transitions)
- `-->|label|` Solid arrow with label (conditions)

**NEVER use** (incompatible):
- ❌ `-.->` Dotted arrow
- ❌ `==>` Thick arrow
- ❌ `..` Dotted line

### Layout Direction

**Preferred**: `flowchart TB` (top-to-bottom)

**Acceptable**: `flowchart LR` (left-to-right) only for 3 or fewer sequential elements

---

## Accessibility

### WCAG AA Compliance

**Color Contrast**: All colors meet WCAG AA contrast ratios (4.5:1 for text).

**Color Independence**: Never rely solely on color to convey meaning.

**Good** (color + label):
```mermaid
flowchart TB
  Completed[Completed - Visit finished]
  style Completed fill:#a5d6a7
```

**Bad** (color only):
```mermaid
flowchart TB
  Completed
  style Completed fill:#a5d6a7
```

### Descriptive Labels

**Good**: `Confirmed[Confirmed - Doctor approved]`

**Bad**: `C[Conf.]` (abbreviation, unclear)

### Maximum Diagram Complexity

**Limit**: 15 nodes per diagram maximum

**Rationale**: Cognitive load, screen reader navigation, visual clarity for patients.

---

## Safe Subset

### ✅ ALWAYS SAFE

**Flowcharts**:
- Keyword: `flowchart TB` or `flowchart LR`
- Nodes: `[Box]`, `(Rounded)`, `{Diamond}` only
- Arrows: `-->` solid only
- Labels: `A -->|label| B`

**Sequence Diagrams**:
- Keyword: `sequenceDiagram`
- Arrows: `->>` solid, `-->>` dashed response
- Participants: Simple alphanumeric names

### ❌ ALWAYS AVOID

- ❌ Dotted lines (`-.->`)
- ❌ Subgraphs (`subgraph`)
- ❌ Note over (`Note over Participant`)
- ❌ Special characters in labels (`:`, `()`, `{}`)
- ❌ Mixed arrow types

### Testing Checklist

Before committing diagrams:

- [ ] Uses only safe patterns
- [ ] No dotted lines
- [ ] No subgraphs
- [ ] Labels are descriptive (not abbreviations)
- [ ] Colors meet WCAG AA contrast (if used)
- [ ] Fewer than 15 nodes
- [ ] Tested in GitHub preview
- [ ] Tested in VSCode (Markdown Preview Mermaid Support extension)

---

## Cross-References

### HealthHub Documents

**State Machines**:
- [State Machine Patterns](state_machine_patterns.md) - Appointment status transitions
- [../product/appointment_state_machine.md](../product/appointment_state_machine.md) - Complete state machine reference

**Authorization**:
- [Authorization Patterns](authorization_patterns.md) - ADT pattern matching diagrams
- [../product/authorization_system.md](../product/authorization_system.md) - Authorization flow

**Architecture**:
- [../product/architecture_overview.md](../product/architecture_overview.md) - 5-layer architecture diagrams

**WebSocket**:
- [WebSocket Security](websocket_security.md) - Real-time notification flows

---

**Last Updated**: November 2025
**Version**: 1.0
