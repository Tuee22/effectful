# HealthHub Tutorials

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/readme.md

> **Purpose**: Navigation hub for HealthHub journey-based tutorials demonstrating progressive learning paths using the Effectful library.

> **📖 Authoritative Reference**: [Effectful Tutorials](../../../../documents/tutorials/) - Learn core Effectful patterns first, then apply them to HealthHub healthcare domain.

---

## Overview

HealthHub tutorials demonstrate pure functional effect systems applied to healthcare management through journey-based progressive learning paths (Beginner → Intermediate → Advanced).

**Additional Documentation**:
- **Role-Specific Guides**: [Product Documentation - Role Guides](../product/roles/README.md)
- **Feature Engineering Patterns**: [Engineering Documentation - Features](../engineering/features/README.md)
- **End-to-End Workflows**: [Product Documentation - Workflows](../product/workflows/README.md)

---

## Quick Start

**New to HealthHub?** Start here:
1. [Beginner Journey](01_journeys/beginner_journey.md) - Login, navigation, viewing data (1 hour)
2. [Intermediate Journey](01_journeys/intermediate_journey.md) - Appointments, prescriptions, state machines (2 hours)
3. [Advanced Journey](01_journeys/advanced_journey.md) - Custom effects, performance, production (3 hours)

**Need other documentation?**
- **Role-specific operational guides**: [Product Documentation - Role Guides](../product/roles/README.md)
- **Feature engineering patterns**: [Engineering Documentation - Features](../engineering/features/README.md)
- **Multi-feature workflows**: [Product Documentation - Workflows](../product/workflows/README.md)

---

## Journey-Based Learning Path

Progressive learning from basics to production deployment.

| Tutorial | Duration | Topics | Prerequisites |
|----------|----------|--------|---------------|
| [Beginner Journey](01_journeys/beginner_journey.md) | 1 hour | Login, RBAC, viewing data, ADTs | Base effectful quickstart |
| [Intermediate Journey](01_journeys/intermediate_journey.md) | 2 hours | State machines, effect programs, workflows | Beginner journey |
| [Advanced Journey](01_journeys/advanced_journey.md) | 3 hours | Custom effects, performance, production | Intermediate journey |

**Total Time**: ~6 hours
**Outcome**: Complete understanding of HealthHub architecture and patterns

---

## Library Delta Tutorials

HealthHub-specific deltas for base Effectful tutorials. These are minimal reference documents (~17 lines each) that document only HealthHub-specific differences (compose stack, service name, ports, credentials).

See [00_library_deltas/README.md](00_library_deltas/README.md) for the complete list.

**When to use**: Reference when following base Effectful tutorials but need HealthHub-specific configuration.

---

## Demo Data

All tutorials use seeded demo data from `backend/scripts/seed_data.sql`:

**Credentials** (all users: password `password123`):
- **Admins**: admin@healthhub.com, superadmin@healthhub.com
- **Doctors**: dr.smith@healthhub.com (Cardiology), dr.johnson@healthhub.com (Orthopedics), dr.williams@healthhub.com (Dermatology), dr.brown@healthhub.com (Neurology)
- **Patients**: alice.patient@example.com, bob.patient@example.com, carol.patient@example.com, david.patient@example.com, emily.patient@example.com

**Sample Data**: 3 appointments, 2 prescriptions, 2 lab results, 1 invoice

**Reset Demo Data**:
```bash
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

---

## Prerequisites

**All tutorials require**:
1. Docker running with HealthHub stack: `docker compose -f docker/docker-compose.yml up -d`
2. Completed [Effectful Quickstart](../../../../documents/tutorials/quickstart.md)
3. Familiarity with Python generators and type hints

**Recommended background**:
- Understanding of ADTs and Result types from [ADTs and Results](../../../../documents/tutorials/adts_and_results.md)
- Basic knowledge of effect systems from [Effect Types](../../../../documents/tutorials/effect_types.md)

---

## Tutorial Structure

Every tutorial follows this pattern:

1. **Header Metadata**: Status, purpose, cross-references
2. **Prerequisites**: Required prior knowledge and tutorials
3. **Learning Objectives**: 3-5 measurable outcomes
4. **Step-by-Step Instructions**: Executable with demo data
5. **Code Deep Dive**: Effect programs, domain models, interpreters
6. **Summary**: Achievements and key takeaways
7. **Next Steps**: Related tutorials and documentation
8. **Cross-References**: Links to SSoT documents

---

## E2E Test Coverage

Every tutorial workflow has corresponding e2e tests verifying correctness:

- Tutorial steps → Test cases (conceptual feature coverage, not metric-driven)
- Code examples → Verified in integration tests
- State machines → All transitions tested
- RBAC → All role restrictions enforced

---

## Cross-References

- [HealthHub Documentation Hub](../readme.md)
- [Effectful Base Tutorials](../../../../documents/tutorials/)
- [HealthHub Engineering Standards](../engineering/README.md)
- [HealthHub Product Documentation](../product/roles/README.md)
- [HealthHub Domain Documentation](../domain/)
- [Documentation Standards](../documentation_standards.md)
