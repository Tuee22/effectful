# Tutorial 10: Auth Effects

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: documents/readme.md, documents/api/auth.md, documents/engineering/authentication.md, documents/tutorials/effect_types.md, documents/tutorials/adts_and_results.md, documents/tutorials/storage_effects.md, documents/tutorials/testing_guide.md, documents/tutorials/metrics_quickstart.md

> **Purpose**: Tutorial covering authentication effects for JWT token management and password operations.

## SSoT Link Map

| Need                     | Link                                                            |
| ------------------------ | --------------------------------------------------------------- |
| Auth API reference       | [Auth API](../api/auth.md)                                      |
| Authentication standards | [Authentication](../engineering/authentication.md)              |
| Architecture data flow   | [Architecture](../engineering/architecture.md#visual-data-flow) |
| Effect Types             | [Effect Types](effect_types.md)                                 |
| ADTs and Results         | [ADTs and Results](adts_and_results.md)                         |
| Testing guide            | [Testing Guide](testing_guide.md)                               |

## Prerequisites

- Docker workflow running; commands executed via `docker compose ... exec effectful`.
- Completed [Tutorial 02: Effect Types](effect_types.md) and [Tutorial 03: ADTs and Result Types](adts_and_results.md).
- Reviewed auth interpreter contracts in [Auth API](../api/auth.md) and architecture boundaries in [architecture.md](../engineering/architecture.md#visual-data-flow).

## Learning Objectives

- Understand auth effect types (issue/verify tokens, hash/verify passwords) and their guarantees.
- Compose authentication flows that keep secrets isolated in interpreters.
- Test auth programs by stepping generators and mocking interpreters for verification paths.

## Step 1: Overview

- Effects: `ValidateToken`, `GenerateToken`, `InvalidateToken`, `HashPassword`, `ValidatePassword`, `GetUserByEmail`.
- Use this tutorial for workflow intent; the SSoT for fields, return types, and error domains is the [Auth API reference](../api/auth.md).
- Modelling doctrine and guard semantics: [Authentication](../engineering/authentication.md) and [Total Pure Modelling](../engineering/total_pure_modelling.md).

## Step 2: Auth flow (conceptual)

```mermaid
flowchart TB
    Validate[ValidateToken(jwt)] -->|TokenValid| Authorized[Authorize request]
    Validate -->|TokenExpired| Refresh[Refresh or reauthenticate]
    Validate -->|TokenInvalid| Reject[Reject request]
    Authorized --> Hash[HashPassword for new credential]
    Authorized --> Lookup[GetUserByEmail for user context]
```

**Key properties:**

- Token validation returns ADTs; no boolean flags.
- Password handling is effectful; never inline hash/compare in programs.
- Guard decisions must be explicit (token expired vs invalid vs revoked).

## Step 3: Minimal usage

```python
# file: examples/10_auth_effects.py
from collections.abc import Generator
from uuid import UUID

from effectful.effects.auth import ValidateToken, HashPassword, ValidatePassword
from effectful.domain.auth import TokenValid, TokenExpired, TokenInvalid
from effectful.programs.types import AllEffects, EffectResult

def authenticate(token: str) -> Generator[AllEffects, EffectResult, UUID | None]:
    result = yield ValidateToken(token=token)

    match result:
        case TokenValid(user_id=uid, claims=_):
            return uid
        case TokenExpired():
            return None  # trigger refresh flow upstream
        case TokenInvalid():
            return None  # reject immediately

def manage_passwords(password: str, candidate: str) -> Generator[AllEffects, EffectResult, bool]:
    hashed = yield HashPassword(password=password)
    return bool((yield ValidatePassword(password=candidate, hashed=hashed)))
```

> **📖 See**: [Auth API reference](../api/auth.md) for signatures, ADTs, and error handling guarantees.

## Step 4: Testing pointers

- Assert ADT matching: tests should verify TokenValid/TokenExpired/TokenInvalid exhaustiveness.
- Use `mocker.AsyncMock` for adapter fakes and assert password verification paths.
- Coverage rules and timeouts: [Testing](../engineering/testing.md) and [Testing Guide](testing_guide.md).

## Summary

- Reviewed the core auth effects and their security boundaries.
- Authored generator-based login/verification flows that delegate secrets to interpreters.
- Captured testing patterns for hashing/token verification without exposing secrets in tests.

## Next Steps

- Harden observability and alerting around auth in [Monitoring & Alerting](../engineering/monitoring_and_alerting.md).
- Continue to metrics-focused docs with [Tutorial 11: Metrics Quickstart](metrics_quickstart.md).
- Consult full effect signatures in the [Auth API Reference](../api/auth.md).

## Cross-References

- [Auth API Reference](../api/auth.md)
- [Authentication](../engineering/authentication.md)
- [Total Pure Modelling](../engineering/total_pure_modelling.md)
- [Testing](../engineering/testing.md)
- [Documentation Standards](../documentation_standards.md)
