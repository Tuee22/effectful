# Authentication

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: engineering/README.md, engineering/code_quality.md, engineering/effect_patterns.md, engineering/total_pure_modelling.md, tutorials/auth_effects.md

> **Purpose**: Single Source of Truth for authentication flows and modelling across frontend and backend. Based on the pure ADT workflow from `engineering/total_pure_modelling.md`. Applies to all services and clients unless a delta overrides with additional, system-specific constraints.

---

## Scope

- Token/session lifecycle (acquire, refresh, expire) for web/native clients
- Frontend readiness, guard decisions, and redirect/deny semantics
- Backend authenticate → authorize pipeline and response mapping
- Time/clock considerations, error handling, and resiliency
- Anti-patterns and verification guidance

Non-goals:
- Business-role definitions (see domain/product authZ docs)
- Secrets management and infra hardening (see configuration/ops docs)

---

## Core Model (from Total Pure Modelling)

### Frontend ADTs
- `AuthReadiness`: `Initializing | Hydrating | Ready(AuthenticatedOrNot) | Failed`
- `AuthenticatedOrNot`: `Authenticated | Unauthenticated | SessionRestoring | SessionExpired`
- `GuardDecision` (pure): `AwaitAuth | RedirectToLogin(reason) | Denied(userId) | Authorized(userId, roles)`

### Backend ADTs
- Auth outcome: `Authenticated(user) | AuthFailure(reason)`
- Guard: `AwaitAuth | RedirectToLogin | Denied | Authorized`

### Principles
- Make illegal states impossible; every variant must reach a decision (no endless hydrations).
- Compute pure decisions first; then perform effects (redirects, renders, WS connects).
- Keep frontend/backends in lockstep on meanings (401 redirect vs 403 deny).
- No timing hacks or environment flags; solve with explicit states instead.

---

## Lifecycle: Frontend

1) **Boot**: Start at `Initializing`; UI does not imply auth.
2) **Hydrate**: If no persisted session, jump to `Ready(Unauthenticated)`. If something is stored, go to `Ready(SessionRestoring)` and immediately refresh.
3) **Refresh**: Success → `Authenticated`. Expired/missing → `SessionExpired` and redirect. Network failures end deterministically (redirect to login) instead of spinning.
4) **Guard**: `computeGuardDecision(readiness, requiredRoles)` drives: loading gate, redirect, deny, or authorize (then render and connect sockets).

### Guard Decision Template

```python
# file: examples/authentication.py
def compute_guard_decision(
    readiness: AuthReadiness,
    required_roles: set[str] | None = None,
) -> GuardDecision:
    if isinstance(readiness, Initializing | Hydrating):
        return AwaitAuth
    if isinstance(readiness, Failed):
        return RedirectToLogin("auth_init_failed")
    if isinstance(readiness, Ready):
        match readiness.value:
            case Unauthenticated():
                return RedirectToLogin("unauthenticated")
            case SessionRestoring():
                return AwaitAuth
            case SessionExpired():
                return RedirectToLogin("session_expired")
            case Authenticated(user=user):
                if required_roles and not required_roles.issubset(user.roles):
                    return Denied(user.id)
                return Authorized(user.id, roles=user.roles)
    # MyPy enforces exhaustiveness - no assert_never needed
```

---

## Lifecycle: Backend Request

1) **Authenticate**: Validate or refresh tokens; return `Authenticated(user)` with roles or typed `AuthFailure` (expired, invalid, redirect).
2) **Authorize**: `authorize(user, required_roles)` returns guard decision matching frontend semantics (401 vs 403 vs success).
3) **Respond**: Map `RedirectToLogin` → 401 with hint, `Denied` → 403, `Authorized` → domain work (optionally rotate tokens). `AwaitAuth` should be transient and resolved before responding.

### Backend Mapping Template

```python
# file: examples/authentication.py
def authenticate_and_authorize(
    request: Request,
    required_roles: set[str] | None,
) -> GuardDecision:
    auth_result = authenticate(request)
    match auth_result:
        case AuthFailure(reason="expired"):
            return RedirectToLogin("expired")
        case AuthFailure():
            return RedirectToLogin("unauthenticated")
        case Authenticated(user):
            if required_roles and not required_roles.issubset(user.roles):
                return Denied(user.id)
            return Authorized(user.id, roles=user.roles)
```

---

## Time & Resilience

- Use deterministic time sources; account for skew between client and server.
- Refresh near expiry proactively; treat `SessionExpired` as terminal until re-authentication.
- On network failure during restore, fail fast to login with a clear state.
- All branches must be idempotent and retry-safe (e.g., refresh).

---

## Anti-Patterns

- Silent downgrade from expired to unauthenticated without signalling `SessionExpired`.
- UI rendering protected content before guard decision completes.
- Mixing redirect vs deny semantics (401 vs 403) between tiers.
- Implicit timing flags or “loading forever” states instead of explicit ADTs.

---

## Verification

- Property tests: every `(readiness, requiredRoles)` pair produces a guard decision; no stuck states.
- Integration tests: refresh flows (success, expired, network fail) and matching 401/403 mappings.
- Contract tests: frontend and backend guard decisions align on the same inputs.
- Clock skew tests: near-expiry handling produces deterministic outcomes.

---

## Related Documentation

- Modelling foundation: [total_pure_modelling.md](total_pure_modelling.md)
- Architecture: [architecture.md](architecture.md)
- Code quality/purity: [code_quality.md](code_quality.md)
- Effect patterns: [effect_patterns.md](effect_patterns.md)

---

## Maintenance

- Review on auth library or token format changes.
- Keep frontend/backends synced on guard ADT definitions and reasons.
- Update anti-patterns as new failure modes are discovered.

## Cross-References
- [Total Pure Modelling](total_pure_modelling.md)
- [Code Quality](code_quality.md)
- [Effect Patterns](effect_patterns.md)
- [Documentation Standards](../documentation_standards.md)