# Storage Effects

**Status**: Authoritative source\
**Supersedes**: none\
**Referenced by**: documents/readme.md

> **Purpose**: Tutorial covering storage effects for S3-compatible object storage operations in effectful.

## Prerequisites

- Docker workflow running; commands executed via `docker compose ... exec effectful`.
- Completed [Tutorial 02: Effect Types](effect_types.md) and [Tutorial 03: ADTs and Result Types](adts_and_results.md).
- Familiar with storage interpreter policies in [Storage API](../api/storage.md) and architecture boundaries in [architecture.md](../engineering/architecture.md#visual-data-flow).

## Learning Objectives

- Understand storage effect types (`PutObject`, `GetObject`, `DeleteObject`, `ListObjects`) and their semantics.
- Build generator workflows for uploads, fetches, and cleanups with explicit idempotency.
- Test storage programs via generator stepping and interpreter-level mocks.

## Step 1: Overview

- Effects: `PutObject`, `GetObject`, `DeleteObject`, `ListObjects`.
- Use this tutorial for workflow intent; the SSoT for fields, return types, and error domains is the [Storage API reference](../api/storage.md).
- Architecture flows and boundaries: [Architecture](../engineering/architecture.md#visual-data-flow) and [Effect Patterns](../engineering/effect_patterns.md#state-machines).

## Step 2: Storage workflow (conceptual)

```mermaid
flowchart TB
    Upload[PutObject(bucket,key,bytes)] --> Stored[Object stored with metadata]
    Stored --> Fetch[GetObject(bucket,key)]
    Fetch --> ObjectReturned[S3Object]
    ObjectReturned --> Cleanup{Cleanup needed?}
    Cleanup -->|Yes| Delete[DeleteObject(bucket,key)]
    Cleanup -->|No| Done[Workflow complete]
```

**Key properties:**

- Immutable uploads: write new versions instead of mutating in place.
- Idempotent deletes: deleting a missing key is not an error.
- Metadata-first: use content type and metadata to drive downstream routing.

## Step 3: Minimal usage

Keep programs orchestration-only; let interpreters own I/O and retries.

```python
# snippet
from collections.abc import Generator

from effectful.effects.storage import GetObject, PutObject, DeleteObject
from effectful.programs.types import AllEffects, EffectResult

def put_document(key: str, content: bytes) -> Generator[AllEffects, EffectResult, str]:
    etag = yield PutObject(bucket="docs", key=key, content=content, content_type="text/plain")
    return f"stored:{key}:{etag}"

def fetch_document(key: str) -> Generator[AllEffects, EffectResult, bytes | None]:
    obj = yield GetObject(bucket="docs", key=key)
    return None if obj is None else obj.content

def delete_document(key: str) -> Generator[AllEffects, EffectResult, str]:
    yield DeleteObject(bucket="docs", key=key)
    return f"deleted:{key}"
```

> **📖 See**: [Storage API reference](../api/storage.md) for signatures, return shapes, and error guarantees.

## Step 4: Testing pointers

## Summary

- Learned the storage effect set and mapped them to S3-style workflows with idempotent deletes.
- Built minimal generator orchestration for upload, fetch, and cleanup while keeping interpreters responsible for I/O.
- Captured testing approaches using generator stepping and interpreter fakes.

## Next Steps

- Review metrics and alerting for storage paths in [Monitoring & Alerting](../engineering/monitoring_and_alerting.md).

- Explore messaging workflows next in [Tutorial 10: Auth Effects](auth_effects.md).

- See full API shapes in [Storage API Reference](../api/storage.md).

- Unit-level: drive generators and assert yielded effects.

- Interpreter-level: mock storage adapters with `mocker.AsyncMock` and assert error propagation/backoff.

- Coverage rules and timeouts: [Testing](../engineering/testing.md) and [Testing Guide](testing_guide.md).

## Cross-References

- [Storage API Reference](../api/storage.md)
- [Architecture](../engineering/architecture.md#visual-data-flow)
- [Effect Patterns](../engineering/effect_patterns.md#state-machines)
- [Testing](../engineering/testing.md)
- [Documentation Standards](../documentation_standards.md)
