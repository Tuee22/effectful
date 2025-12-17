<!-- AUTO-GENERATED FILE. DO NOT EDIT BY HAND. -->

# Functional Catalogue

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: engineering/architecture.md, engineering/code_quality.md

> **Purpose**: Generated index of all ADTs and state machines defined in the codebase and documented via Mermaid.

## Index

| Kind         | ID                                                  | Name                  | Module                            | Doc                                                                       |
| ------------ | --------------------------------------------------- | --------------------- | --------------------------------- | ------------------------------------------------------------------------- |
| ADT          | effectful.core.Result                               | Result                | effectful.core                    | [intro.md](../dsl/intro.md)                                               |
| ADT          | effectful.domain.cache_result.CacheLookupResult     | CacheLookupResult     | effectful.domain.cache_result     | [adts_and_results.md](../tutorials/adts_and_results.md)                   |
| ADT          | effectful.domain.message_envelope.AcknowledgeResult | AcknowledgeResult     | effectful.domain.message_envelope | [messaging.md](../api/messaging.md)                                       |
| ADT          | effectful.domain.message_envelope.ConsumeResult     | ConsumeResult         | effectful.domain.message_envelope | [messaging.md](../api/messaging.md)                                       |
| ADT          | effectful.domain.message_envelope.NackResult        | NackResult            | effectful.domain.message_envelope | [messaging.md](../api/messaging.md)                                       |
| ADT          | effectful.domain.message_envelope.PublishResult     | PublishResult         | effectful.domain.message_envelope | [messaging.md](../api/messaging.md)                                       |
| ADT          | effectful.domain.metrics_result.MetricQueryResult   | MetricQueryResult     | effectful.domain.metrics_result   | [metrics.md](../api/metrics.md)                                           |
| ADT          | effectful.domain.metrics_result.MetricResult        | MetricResult          | effectful.domain.metrics_result   | [metrics.md](../api/metrics.md)                                           |
| ADT          | effectful.domain.optional_value.OptionalValue       | OptionalValue         | effectful.domain.optional_value   | [optional_value.md](../api/optional_value.md)                             |
| ADT          | effectful.domain.profile.ProfileLookupResult        | ProfileLookupResult   | effectful.domain.profile          | [adts_and_results.md](../tutorials/adts_and_results.md)                   |
| ADT          | effectful.domain.s3_object.GetObjectResult          | GetObjectResult       | effectful.domain.s3_object        | [storage.md](../api/storage.md)                                           |
| ADT          | effectful.domain.s3_object.PutResult                | PutResult             | effectful.domain.s3_object        | [storage.md](../api/storage.md)                                           |
| ADT          | effectful.domain.token_result.TokenRefreshResult    | TokenRefreshResult    | effectful.domain.token_result     | [auth.md](../api/auth.md)                                                 |
| ADT          | effectful.domain.token_result.TokenValidationResult | TokenValidationResult | effectful.domain.token_result     | [auth.md](../api/auth.md)                                                 |
| ADT          | effectful.domain.user.UserLookupResult              | UserLookupResult      | effectful.domain.user             | [adts_and_results.md](../tutorials/adts_and_results.md)                   |
| ADT          | effectful.std.Effect                                | Effect                | effectful.std                     | [intro.md](../dsl/intro.md)                                               |
| ADT          | effectful.std.db.DbFailure                          | DbFailure             | effectful.std.db                  | [intro.md](../dsl/intro.md)                                               |
| ADT          | effectful.std.db.DbMode                             | DbMode                | effectful.std.db                  | [intro.md](../dsl/intro.md)                                               |
| StateMachine | healthhub.auth.AuthFlow                             | AuthFlow              | healthhub.auth                    | [intro.md](../dsl/intro.md)                                               |
| StateMachine | product.appointments.Lifecycle                      | Lifecycle             | product.appointments              | [appointment_lifecycle.md](../product/workflows/appointment_lifecycle.md) |

## Cross-References

- [Documentation Standards](../documentation_standards.md)
- [Architecture](architecture.md#cross-references)
- [Code Quality](code_quality.md#cross-references)
