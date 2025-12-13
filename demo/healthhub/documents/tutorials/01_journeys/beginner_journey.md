# Beginner Journey (HealthHub Delta)

**Status**: reference only
**Supersedes**: none
**Referenced by**: | **📖 Base Standard**: [beginner_journey.md](../../../../../documents/tutorials/01_journeys/beginner_journey.md)

> **Purpose**: HealthHub overlay deltas for Beginner Journey. See base SSoT for canonical flow.
> **📖 Authoritative Reference**: [beginner_journey.md](../../../../../documents/tutorials/01_journeys/beginner_journey.md)

## Deltas

- No additional deltas; inherits base standard.

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

## Journey Steps

### Step 2: Login as Patient

- Use demo credentials to sign in via the HealthHub UI; verify JWT issued and dashboard loads.

### Step 3: View Patient Dashboard

- Confirm appointments, prescriptions, and lab results load for the authenticated patient.

### Step 5: Login as Doctor

- Sign in as a doctor; verify access to patient list and workflows.

### Step 6: View Doctor Dashboard

- Confirm ability to view all patients and pending appointments.

### Step 7: Login as Admin

- Sign in as admin; verify ability to view and manage system-wide entities.

## Cross-References

- [HealthHub Documentation Hub](../../readme.md)
- [Base Effectful Quickstart](../../../../../documents/tutorials/quickstart.md)
- [HealthHub Domain Patterns](../../domain/)
- [HealthHub Authentication](../../engineering/authentication.md)
