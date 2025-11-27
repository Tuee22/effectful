"""E2E Browser Tests for HealthHub.

Uses Playwright with pytest following ShipNorth patterns:
- Function-scoped browser fixtures (prevents resource exhaustion)
- ADT state synchronization (no timing hacks)
- Storage clearing after each test (prevents auth token leakage)
- TRUNCATE + seed before each test (reproducible starting state)

Test Categories:
- test_login_flow.py: Authentication state machine (12 tests)
- test_rbac.py: Role-based access control (21 tests)
- test_appointments.py: Appointment state machine (8 tests)
- test_prescriptions.py: Prescription management (4 tests)
- test_lab_results.py: Lab result viewing/review (4 tests)
- test_invoices.py: Invoice management (4 tests)

Total: 53 tests x 3 browsers = 159 test runs
"""
