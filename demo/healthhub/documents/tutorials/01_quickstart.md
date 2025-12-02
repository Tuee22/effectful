# Tutorial 01: Getting Started with HealthHub (Deltas Only)

> Extends base [Tutorial 01: Quickstart](../../../../documents/tutorials/01_quickstart.md). Follow the base steps; this doc lists only HealthHub-specific adjustments to stay DRY.

---

## What changes from the base quickstart
- **Compose file**: Use `demo/healthhub/docker/docker-compose.yml` instead of the root compose.
- **Service name**: Commands run inside the `healthhub` container (not `effectful`).
- **Ports**: API + frontend served on `http://localhost:8850` (single origin).
- **Stack**: Includes PostgreSQL `5433`, Redis `6380`, Pulsar `6651`, MinIO `9001` seeded for demo data.
- **Commands**:
  - Start: `docker compose -f demo/healthhub/docker/docker-compose.yml up -d`
  - Tests: `docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run test-all`
  - Lint/type check: `docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run check-code`
- **Data**: Demo fixtures are anonymized; never use production PHI. See [HIPAA Compliance](../domain/hipaa_compliance.md).

## See also
- Base: [Tutorial 01: Quickstart](../../../../documents/tutorials/01_quickstart.md)
- Navigation: [HealthHub docs index](../README.md)
- Architecture deltas: [Architecture Overview](../product/architecture_overview.md)
- Testing deltas: [Testing](../engineering/testing.md)

---

**Last Updated**: 2025-11-28  
**Supersedes**: none  
**Referenced by**: ../README.md, ../engineering/README.md
