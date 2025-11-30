# Documentation Guidelines

> **SSoT** for all documentation practices in the effectful project.

## Documentation Philosophy

### Single Source of Truth (SSoT)
- Each piece of knowledge has exactly ONE authoritative location
- All other references LINK to the SSoT, never duplicate
- Mark SSoT documents explicitly: "**SSoT** for [topic]"
- Update SSoT first, links follow automatically

### DRY (Don't Repeat Yourself)
- Duplicate content creates maintenance burden
- Liberal linking instead of copy-paste
- Acceptable repetition: navigation breadcrumbs, quick reference tables
- Forbidden duplication: examples, procedures, explanations

### Separation of Concerns
- **Engineering standards** (documents/engineering/): HOW to build effectful code
- **Tutorials** (documents/tutorials/): Step-by-step learning guides
- **API reference** (documents/api/): Function signatures and usage

## File Organization Standards

### Naming Conventions
- Lowercase with hyphens: `type-safety.md`, not `TypeSafety.md`
- Descriptive names: `docker-workflow.md`, not `docker.md`
- Avoid abbreviations: `configuration.md`, not `config.md`
- No version numbers in filenames: use git for versioning

### Directory Structure
```
documents/
├── engineering/        # Standards for contributors
├── tutorials/         # Learning guides for users
└── api/              # Technical reference
```

### Document Size Guidelines
- Target: 300-800 lines per document
- Minimum: 100 lines (otherwise merge with related doc)
- Maximum: 1000 lines (consider splitting if larger)
- Exception: testing.md (~3600 lines) due to 22 anti-patterns

## Writing Style Guidelines

### Imperative Mood for Standards
- ✅ "Use frozen dataclasses"
- ❌ "You should use frozen dataclasses"
- ✅ "Avoid mutable state"
- ❌ "It's better to avoid mutable state"

### Code Examples
- Include explanations AFTER code blocks
- Show both WRONG and CORRECT examples for anti-patterns
- Use real effectful types, not generic placeholders

**Example format:**
```python
# ❌ WRONG - Mutable domain model
@dataclass
class User:
    name: str
    email: str

# ✅ CORRECT - Frozen for immutability
@dataclass(frozen=True)
class User:
    name: str
    email: str
```

### Tables for Reference Material
Use tables for:
- Command reference
- Environment variables
- Metric types
- Test statistics

### Lists for Procedures
Use numbered lists for sequential steps:
1. Create directory
2. Write file
3. Verify links

Use bullet lists for unordered items:
- Type safety
- Purity
- Testing

### Active Voice Preferred
- ✅ "The interpreter handles effects"
- ❌ "Effects are handled by the interpreter"

## Mermaid Diagram Best Practices

### Core Principle
**Use only the "safe subset" that renders in both GitHub and VSCode.**

**Problem**: GitHub (Mermaid v10.8.0) and VSCode (Mermaid v11+) have compatibility differences. Diagrams that work on GitHub may fail in VSCode.

**Solution**: Restrict to universally compatible patterns documented here.

**Priority**: Universal compatibility > Visual features

### Orientation Guidelines

**Always orient the largest axis vertically (TB direction).**

Diagrams that are wider than they are tall appear very small when rendered, making them hard to read.

**Use TB (Top-Bottom) - Preferred:**
- Sequential workflows with more than 3 steps
- State machines showing status transitions
- Decision trees with multiple branches
- Any diagram where the longest chain of elements would run horizontally

**LR (Left-Right) acceptable only for:**
- Diagrams with 3 or fewer sequential elements
- Diagrams showing parallel/concurrent relationships (not sequential)
- Simple input → output flows with minimal intermediate steps

**Rule of Thumb**: Count the elements in your longest chain. If more than 3, use TB.

**Example:**
```mermaid
# ❌ BAD - LR with many elements (appears tiny)
flowchart LR
  A --> B --> C --> D --> E --> F

# ✅ GOOD - TB with same elements (readable)
flowchart TB
  A --> B
  B --> C
  C --> D
  D --> E
  E --> F
```

### Safe Patterns

#### Pattern 1: Simple Flowchart

**Use Case**: Process flows, decision trees, system architecture

```mermaid
flowchart TB
  Start[Start Process]
  ValidateInput{Valid Input?}
  Process[Process Data]
  SaveDB[Save to Database]
  Error[Show Error]
  End[Complete]

  Start --> ValidateInput
  ValidateInput -->|Yes| Process
  ValidateInput -->|No| Error
  Process --> SaveDB
  SaveDB --> End
  Error --> End
```

**Why it works**: Simple nodes, solid arrows only, clear flow direction.

#### Pattern 2: Simple Sequence Diagram

**Use Case**: API calls, authentication flows, message passing

```mermaid
sequenceDiagram
  participant Client
  participant Server
  participant Database

  Client->>Server: POST /login
  Server->>Database: Query user credentials
  Database-->>Server: Return user data
  Server-->>Client: Return JWT token
```

**Why it works**: Simple participants, solid arrows only, no complex blocks.

#### Pattern 3: Architecture Diagram (Flat Structure)

**Use Case**: System components, service topology

```mermaid
flowchart TB
  BrowserClient[Browser - React SPA]
  APIGateway[API Gateway]
  AuthService[Auth Service]
  DataService[Data Service]
  Database[(Database)]

  BrowserClient --> APIGateway
  APIGateway --> AuthService
  APIGateway --> DataService
  DataService --> Database
```

**Why it works**: No subgraphs, uses prefixed node names for grouping. TB orientation ensures readability.

### Forbidden Patterns

❌ **Never use:**
- Dotted lines: `-.->`, `-.-`, `..`
- Subgraphs: `subgraph` keyword
- Thick arrows: `==>`
- Note over: `Note over Participant`
- Special characters in labels: `:`, `()`, `{}`
- Mixed arrow types in same diagram
- Comments inside diagrams: `%%`

### Fixes for Common Problems

#### Problem 1: Dotted Lines for "Blocked" Connections

**❌ WRONG** (fails in VSCode):
```mermaid
flowchart TB
  Browser[Browser]
  AllowedAPI[Allowed API]
  BlockedSite[Evil Site]

  Browser --> AllowedAPI
  Browser -.-> BlockedSite
```

**✅ CORRECT** (works everywhere):
```mermaid
flowchart TB
  Browser[Browser]
  AllowedAPI[Allowed API]
  BlockedSite[BLOCKED - Evil Site]

  Browser --> AllowedAPI
  Browser --> BlockedSite
```

**Fix Strategy**: Use solid arrows, add "BLOCKED" prefix to node label.

#### Problem 2: Subgraphs for Grouping

**❌ WRONG** (fails in VSCode):
```mermaid
flowchart LR
  subgraph Client
    SPA[React SPA]
    Store[State Store]
  end

  subgraph API
    REST[REST Routes]
    WS[WebSocket]
  end

  SPA --> REST
  SPA --> WS
```

**✅ CORRECT** (works everywhere):
```mermaid
flowchart TB
  ClientSPA[Client - React SPA]
  ClientStore[Client - State Store]
  APIRest[API - REST Routes]
  APIWebSocket[API - WebSocket]

  ClientStore --> ClientSPA
  ClientSPA --> APIRest
  ClientSPA --> APIWebSocket
```

**Fix Strategy**: Flatten hierarchy, use prefixed node names (e.g., "Client - ", "API - "). Use TB for better readability.

#### Problem 3: Note Over in Sequence Diagrams

**❌ WRONG** (fails in some VSCode):
```mermaid
sequenceDiagram
  User->>Server: POST /login
  Server-->>User: Return access token
  Note over User: Token expires after 15 minutes
```

**✅ CORRECT** (works everywhere):
```mermaid
sequenceDiagram
  User->>Server: POST /login
  Server-->>User: Return access token (expires 15m)
```

**Fix Strategy**: Move note text into arrow label or participant message.

#### Problem 4: Complex Alt Blocks

**❌ WRONG** (fails in some VSCode):
```mermaid
sequenceDiagram
  Client->>Server: Request
  alt Success
    Server-->>Client: 200 OK
  else Unauthorized
    Server-->>Client: 401 Unauthorized
  else Server Error
    Server-->>Client: 500 Error
  end
```

**✅ CORRECT** (works everywhere):
```mermaid
sequenceDiagram
  Client->>Server: Request
  alt Success
    Server-->>Client: 200 OK
  else Error
    Server-->>Client: 401 or 500 Error
  end
```

**Fix Strategy**: Limit to one `else` clause, combine similar cases.

#### Problem 5: Special Characters in Labels

**❌ WRONG** (may fail parsing):
```mermaid
flowchart TB
  A[User: Alice (admin)]
  B[Function: process_data()]
  C[Result: {status: ok}]
```

**✅ CORRECT** (works everywhere):
```mermaid
flowchart TB
  A[User Alice - admin role]
  B[Function process_data]
  C[Result status ok]
```

**Fix Strategy**: Remove colons, parentheses, quotes, braces from labels.

### Testing Checklist

Before committing mermaid diagrams, verify:

- [ ] Diagram uses only safe patterns from this guide
- [ ] No dotted lines (`-.->`)
- [ ] No subgraphs (`subgraph`)
- [ ] No `Note over` in sequences
- [ ] Labels use simple text (no `:`, `()`, `{}`)
- [ ] Arrow types are consistent (don't mix styles)
- [ ] Tested in GitHub preview
- [ ] Tested in VSCode with recommended extension
- [ ] Tested in Mermaid Live Editor (https://mermaid.live/)

### VSCode Setup

**Recommended Extension:**
- **Name**: Markdown Preview Mermaid Support
- **Author**: Matt Bierner
- **ID**: `bierner.markdown-mermaid`
- **Why**: Most compatible with GitHub's Mermaid version

**Installation**:
```bash
code --install-extension bierner.markdown-mermaid
```

### Alternatives When Safe Subset Isn't Enough

If your diagram requires features not in the safe subset:

#### Alternative 1: ASCII Art

**Pros**: Universal, no rendering needed, works everywhere
**Cons**: Limited visual appeal, harder to create

```
┌─────────────┐       ┌─────────────┐
│   Client    │──────>│   Server    │
└─────────────┘       └─────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │  Database   │
                      └─────────────┘
```

#### Alternative 2: Static Images

**Pros**: Full visual control, guaranteed rendering
**Cons**: Harder to update, version control issues

**Process**:
1. Create diagram in Mermaid Live Editor: https://mermaid.live/
2. Export as SVG or PNG
3. Commit image to repo
4. Reference in markdown: `![Architecture](./diagrams/architecture.svg)`

#### Alternative 3: PlantUML

**Pros**: Better VSCode support, more mature, richer feature set
**Cons**: Different syntax, requires separate setup

#### Alternative 4: External Links

**Pros**: No compatibility issues
**Cons**: User must leave document

```markdown
[View Architecture Diagram](https://mermaid.live/edit#pako:eNpVjk...)
```

## Cross-Reference Management

### Link Format

**Relative paths preferred:**
```markdown
# From documents/tutorials/01_quickstart.md
See [Type Safety](../engineering/type_safety.md)

# From documents/engineering/purity.md
See [Purity Patterns](purity_patterns.md)
```

**Absolute paths from root:**
```markdown
# From anywhere
See [Architecture](documents/engineering/architecture.md)
```

### Link Verification

**Required after refactors:**
```bash
# Run link verification script
python tools/verify_links.py

# Manually check for broken paths
grep -r "documents/core/" .
```

**Forbidden:**
- Dead links (target doesn't exist)
- Links to deprecated docs
- Circular references (doc A → doc B → doc A)

### Updating Links After Refactors

**When moving files:**
1. Use `git mv` to preserve history
2. Create link update script (sed patterns)
3. Run automated updates
4. Manually verify all references
5. Run verification script
6. Update any external references

## SSoT Enforcement

### How to Mark Documents as Authoritative

Add explicit SSoT marker:
```markdown
# Type Safety Standards

> **SSoT** for all type safety rules in effectful.

Referenced by: purity.md, architecture.md, CLAUDE.md, tutorials/03_adts_and_results.md
```

### When to Duplicate vs Link

**Always link:**
- Detailed explanations
- Code examples
- Procedures
- Standards and rules

**Acceptable duplication:**
- Navigation breadcrumbs
- Table of contents
- Quick reference tables (with "See [X] for details")
- Context-specific summaries (3-5 lines max)

**Example of acceptable duplication:**
```markdown
## Type Safety (Summary)

**Quick reminder**: Zero `Any`, `cast()`, or `type: ignore` allowed.

**See [Type Safety Standards](../engineering/type_safety.md) for complete rules.**
```

### Forbidden Duplication

❌ Never duplicate:
- Full code examples (link to canonical example)
- Step-by-step procedures (link to procedure doc)
- Explanations longer than 5 lines

## Document Templates

### Engineering Standard Template
```markdown
# [Topic] Standards

> **SSoT** for all [topic] practices in effectful.

## Overview

[1-2 sentence description]

## Core Principles

[3-5 principles as bullet list]

## Standards

### Standard 1: [Name]

[Detailed explanation]

**Example:**
[Code example]

**Rationale:** [Why this standard exists]

## Anti-Patterns

### Anti-Pattern 1: [Name]

**❌ WRONG:**
[Bad example]

**✅ CORRECT:**
[Good example]

## See Also

- [Related Standard](./related.md)
- [Tutorial](../tutorials/example.md)

---

**Last Updated**: YYYY-MM-DD
**Referenced by**: [List of docs that reference this SSoT]
```

### Tutorial Template
```markdown
# Tutorial: [Topic]

> Learn [skill] in [timeframe]

## Prerequisites

- [Prerequisite 1]
- [Prerequisite 2]

## What You'll Learn

- [Learning objective 1]
- [Learning objective 2]

## Step 1: [Action]

[Explanation]

[Code example]

## Step 2: [Action]

[Continue pattern]

## Summary

[Recap of what was learned]

## Next Steps

- [Tutorial 2](./02_next_topic.md)
- [Related Standard](../engineering/standard.md)

---

**Previous**: [Tutorial 1](./01_previous.md) | **Next**: [Tutorial 3](./03_next.md)
```

### API Reference Template
```markdown
# [Component] API Reference

## Overview

[Brief description of component]

## Types

### [TypeName]

[Type definition]

**Fields:**
- `field_name` (Type): Description

**Example:**
[Usage example]

## Functions

### [function_name]

[Function signature]

**Parameters:**
- `param` (Type): Description

**Returns:**
- Type: Description

**Raises:**
- ErrorType: When [condition]

**Example:**
[Usage example]

## See Also

- [Related API](./related.md)
- [Tutorial](../tutorials/example.md)
- [Standard](../engineering/standard.md)
```

## File Headers

**All engineering documents should include:**
```markdown
# Document Title

> **SSoT** for [topic] (if applicable)

[1-2 sentence overview]

---

**Last Updated**: YYYY-MM-DD
**Referenced by**: [List of documents]
```

## Markdown Formatting

### Code Blocks
- Always specify language: \`\`\`python, \`\`\`bash, \`\`\`markdown
- Use \`\`\`markdown for showing markdown examples
- Use comments to explain code: `# Explanation`

### Headings
- h1 (`#`) - Document title only
- h2 (`##`) - Major sections
- h3 (`###`) - Subsections
- h4 (`####`) - Rare, only if needed
- Never skip levels (h2 → h4)

### Emphasis
- **Bold** for important terms, emphasis
- *Italic* for introducing terms
- `Code` for inline code, filenames, commands

### Lists
- Use `-` for unordered lists (not `*` or `+`)
- Use `1.` for numbered lists
- Indent nested lists with 2 spaces

## Version Control

### Git Commit Messages for Docs
```
docs: add documentation guidelines

- Add SSoT and DRY principles
- Include mermaid best practices
- Define file organization standards
```

### When to Update Documentation
- Immediately when code changes affect docs
- When new features are added
- When anti-patterns are discovered
- After refactors

## See Also

- [Architecture](architecture.md) - Overall system design
- [Testing](testing.md) - Test documentation practices
- [Contributing](../CONTRIBUTING.md) - How to contribute

---

**Last Updated**: 2025-11-29
**SSoT** for all documentation practices in effectful
**Referenced by**: engineering/README.md, CONTRIBUTING.md
