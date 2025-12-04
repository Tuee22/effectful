# Authentication (HealthHub delta)

> Extends base [Authentication](../../../../documents/engineering/authentication.md). HealthHub-specific deltas only; base rules apply.

---

## Scope (HealthHub)
- Uses dual-token approach (short-lived access + refresh in HttpOnly cookie) per product/authentication.
- ADT guard decisions flow into authorization and audit pipelines; correlate with `correlation_id` for PHI audit trails.
- Apply HIPAA constraints: MFA for privileged actions when available; enforce UTC/NTP discipline for token timestamps.

---

## HealthHub-specific additions
- Rotate refresh token on use; link audit entries to token `jti`.
- Require `purpose_of_use` tagging on auth events for audit logging.
- Break-glass flows must still return explicit guard decisions and emit enriched audit.

---

## Related Documentation
- Base: [Authentication](../../../../documents/engineering/authentication.md)
- Product: [authentication.md](../product/authentication.md), [authorization_system.md](../product/authorization_system.md)
- Engineering: [authorization.md](authorization.md), [code_quality.md](code_quality.md)
