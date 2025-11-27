# Tutorial 01: Getting Started with HealthHub

> Set up and run your first HealthHub development environment.

---

## Prerequisites

- Docker Desktop installed
- Git
- Terminal access

---

## Step 1: Clone and Start

```bash
# Navigate to the effectful directory
cd /path/to/effectful

# Start all services
docker compose -f demo/healthhub/docker/docker-compose.yml up -d
```

This starts:
- HealthHub API (port 8850)
- PostgreSQL (port 5433)
- Redis (port 6380)
- Apache Pulsar (port 6651)
- MinIO S3 (port 9001)

---

## Step 2: Verify Services

```bash
# Check all containers are running
docker compose -f demo/healthhub/docker/docker-compose.yml ps

# Check API health
curl http://localhost:8850/health
```

Expected response:
```json
{
    "status": "healthy",
    "database": "connected",
    "redis": "connected"
}
```

---

## Step 3: Run Tests

```bash
# Run all tests
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run test-all

# Run only unit tests (faster)
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run test-backend
```

---

## Step 4: Check Code Quality

```bash
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run check-code
```

This runs:
1. Black (code formatting)
2. MyPy (strict type checking)

---

## Step 5: Explore the API

### Login as a Patient

```bash
curl -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "patient123"}'
```

### Use the Token

```bash
export TOKEN="<access_token from response>"

curl http://localhost:8850/api/v1/patients/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Step 6: View Logs

```bash
# Follow API logs
docker compose -f demo/healthhub/docker/docker-compose.yml logs -f healthhub

# View database logs
docker compose -f demo/healthhub/docker/docker-compose.yml logs -f postgres
```

---

## Project Structure

```
demo/healthhub/
├── backend/
│   └── app/
│       ├── api/           # FastAPI routes
│       ├── auth/          # JWT authentication
│       ├── domain/        # Domain models (ADTs)
│       ├── effects/       # Effect definitions
│       ├── interpreters/  # Effect handlers
│       ├── programs/      # Effect programs
│       └── repositories/  # Data access
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── tests/
│   └── pytest/
│       ├── backend/       # Unit tests
│       └── integration/   # Integration tests
├── tools/
│   ├── check_code.py
│   └── test_runner.py
├── documents/             # This documentation
├── pyproject.toml
└── CLAUDE.md
```

---

## Common Commands

| Task | Command |
|------|---------|
| Start | `docker compose -f demo/healthhub/docker/docker-compose.yml up -d` |
| Stop | `docker compose -f demo/healthhub/docker/docker-compose.yml down` |
| Reset DB | `docker compose -f demo/healthhub/docker/docker-compose.yml down -v && docker compose -f demo/healthhub/docker/docker-compose.yml up -d` |
| Tests | `docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run test-all` |
| Check | `docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run check-code` |
| Shell | `docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run python` |

---

## Next Steps

- [Tutorial 02: Scheduling Appointments](02_scheduling_appointments.md)
- [Tutorial 03: Creating Prescriptions](03_prescriptions.md)
- [Architecture Overview](../product/architecture_overview.md)

---

**Last Updated**: 2025-11-25
