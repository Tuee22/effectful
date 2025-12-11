# Beginner Journey (HealthHub Delta)

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: HealthHub delta for beginner learning path.
> **📖 Authoritative Reference**: [Effectful Quickstart](../../../../../documents/tutorials/quickstart.md)

## Base Tutorial

Follow the base Effectful quickstart tutorial for canonical procedures, patterns, and concepts:
- [Quickstart Guide](../../../../../documents/tutorials/quickstart.md) - Complete beginner walkthrough

## HealthHub-Specific Configuration

The HealthHub demo differs from base examples in the following ways:

**Service Configuration**:
- Service name: `healthhub` (not `effectful`)
- Docker Compose location: `demo/healthhub/docker/docker-compose.yml`
- API port: 8851
- Base URL: http://localhost:8851

**Demo Credentials**:
- Patients: alice.patient@example.com, bob.patient@example.com (password: password123)
- Doctors: dr.smith@healthhub.com, dr.johnson@healthhub.com (password: password123)
- Admin: admin@healthhub.com (password: password123)

**Docker Commands** (from repository root):
```bash
# Start services
docker compose -f demo/healthhub/docker/docker-compose.yml up -d

# Run tests
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run test-all

# Check code quality
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run check-code
```

**Domain Models**:
- HealthHub uses healthcare-specific ADTs (AuthorizationState for roles, AppointmentStatus for state machine)
- See [HealthHub Domain Docs](../../domain/) for healthcare-specific patterns

## Cross-References

- [HealthHub Documentation Hub](../../readme.md)
- [Base Effectful Quickstart](../../../../../documents/tutorials/quickstart.md)
- [HealthHub Domain Patterns](../../domain/)
- [HealthHub Authentication](../../engineering/authentication.md)
