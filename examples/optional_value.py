"""Runnable examples demonstrating OptionalValue patterns.

This module shows all OptionalValue usage patterns:
1. Basic usage (construction, pattern matching, type narrowing)
2. Domain models with OptionalValue fields
3. Custom effects with normalization (THE CANONICAL PATTERN)
4. Boundary conversion for external APIs
5. Generator programs with OptionalValue

All examples are type-safe (mypy --strict) and runnable.
"""

from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from effectful.domain.optional_value import (
    Absent,
    OptionalValue,
    Provided,
    from_optional_value,
    to_optional_value,
)

# ============================================================================
# Example 1: Basic Usage
# ============================================================================


def example1_basic_usage() -> None:
    """Demonstrate basic OptionalValue construction and pattern matching."""

    print("\n=== Example 1: Basic Usage ===\n")

    # Construction Option 1: Direct construction
    blood_type_provided: OptionalValue[str] = Provided(value="O+")
    blood_type_absent: OptionalValue[str] = Absent(reason="not_provided")

    print(f"Direct construction (Provided): {blood_type_provided}")
    print(f"Direct construction (Absent): {blood_type_absent}")

    # Construction Option 2: Helper function
    blood_type_from_value: OptionalValue[str] = to_optional_value("O+")
    blood_type_from_none: OptionalValue[str] = to_optional_value(None)
    blood_type_with_reason: OptionalValue[str] = to_optional_value(None, reason="not_disclosed")

    print(f"\nHelper (from value): {blood_type_from_value}")
    print(f"Helper (from None): {blood_type_from_none}")
    print(f"Helper (custom reason): {blood_type_with_reason}")

    # Pattern matching with match/case
    def describe_blood_type(bt: OptionalValue[str]) -> str:
        match bt:
            case Provided(value=value):
                return f"Blood type is {value}"
            case Absent(reason="not_provided"):
                return "Blood type not provided"
            case Absent(reason="not_disclosed"):
                return "Patient declined to disclose blood type"
            case Absent(reason=r):
                return f"Blood type unavailable: {r}"

    print(f"\nPattern matching: {describe_blood_type(blood_type_provided)}")
    print(f"Pattern matching: {describe_blood_type(blood_type_absent)}")
    print(f"Pattern matching: {describe_blood_type(blood_type_with_reason)}")

    # Type narrowing with isinstance
    if isinstance(blood_type_provided, Provided):
        # Type narrowed: can access .value
        print(f"\nType narrowing (Provided): {blood_type_provided.value}")

    if isinstance(blood_type_absent, Absent):
        # Type narrowed: can access .reason
        print(f"Type narrowing (Absent): {blood_type_absent.reason}")


# ============================================================================
# Example 2: Domain Models
# ============================================================================


@dataclass(frozen=True)
class Patient:
    """Patient domain model with optional fields using OptionalValue.

    OptionalValue is used for fields that are generically optional
    (provided or not provided) without domain-specific absence semantics.
    """

    id: UUID
    name: str
    email: str
    blood_type: OptionalValue[str]  # Generic optional: provided or not provided
    emergency_contact: OptionalValue[str]  # Generic optional


def example2_domain_models() -> None:
    """Demonstrate OptionalValue in domain models."""

    print("\n=== Example 2: Domain Models ===\n")

    # Patient with all optional fields provided
    patient_complete = Patient(
        id=uuid4(),
        name="Alice Johnson",
        email="alice@example.com",
        blood_type=Provided(value="O+"),
        emergency_contact=Provided(value="+1-555-0123"),
    )

    print(f"Complete patient: {patient_complete.name}")
    match patient_complete.blood_type:
        case Provided(value=bt):
            print(f"  Blood type: {bt}")
        case Absent():
            print("  Blood type: not provided")

    # Patient with some optional fields absent
    patient_partial = Patient(
        id=uuid4(),
        name="Bob Smith",
        email="bob@example.com",
        blood_type=Absent(reason="not_provided"),
        emergency_contact=Absent(reason="not_disclosed"),
    )

    print(f"\nPartial patient: {patient_partial.name}")
    match patient_partial.blood_type:
        case Provided(value=bt):
            print(f"  Blood type: {bt}")
        case Absent(reason=r):
            print(f"  Blood type: {r}")

    match patient_partial.emergency_contact:
        case Provided(value=contact):
            print(f"  Emergency contact: {contact}")
        case Absent(reason=r):
            print(f"  Emergency contact: {r}")


# ============================================================================
# Example 3: Custom Effect with Normalization (THE CANONICAL PATTERN)
# ============================================================================


# Local normalization - type-specific, 4 lines, simple
def _normalize_optional_datetime(
    value: datetime | OptionalValue[datetime] | None,
) -> OptionalValue[datetime]:
    """Normalize plain datetime into OptionalValue ADT."""
    if isinstance(value, (Provided, Absent)):
        return value
    return to_optional_value(value)


def _normalize_optional_str(
    value: str | OptionalValue[str] | None,
) -> OptionalValue[str]:
    """Normalize plain str into OptionalValue ADT."""
    if isinstance(value, (Provided, Absent)):
        return value
    return to_optional_value(value)


@dataclass(frozen=True, init=False)
class CreateAppointment:
    """Custom effect with OptionalValue parameters.

    This demonstrates THE CANONICAL NORMALIZATION PATTERN:
    1. Public __init__ accepts T | OptionalValue[T] | None (ergonomic)
    2. Local _normalize_optional_value() normalizes to OptionalValue
    3. Internal fields store OptionalValue[T] (type-safe)
    """

    patient_id: UUID
    doctor_id: UUID
    requested_time: OptionalValue[datetime]
    notes: OptionalValue[str]

    def __init__(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        requested_time: datetime | OptionalValue[datetime] | None = None,
        notes: str | OptionalValue[str] | None = None,
    ) -> None:
        """Create appointment with ergonomic optional parameters.

        Args:
            patient_id: UUID of patient
            doctor_id: UUID of doctor
            requested_time: Optional requested appointment time (normalized to OptionalValue)
            notes: Optional appointment notes (normalized to OptionalValue)
        """
        # Normalize to OptionalValue before storing (frozen dataclass pattern)
        object.__setattr__(self, "patient_id", patient_id)
        object.__setattr__(self, "doctor_id", doctor_id)
        object.__setattr__(self, "requested_time", _normalize_optional_datetime(requested_time))
        object.__setattr__(self, "notes", _normalize_optional_str(notes))


def example3_effect_normalization() -> None:
    """Demonstrate THE CANONICAL NORMALIZATION PATTERN in effects."""

    print("\n=== Example 3: Effect Normalization (CANONICAL PATTERN) ===\n")

    patient_id = uuid4()
    doctor_id = uuid4()

    # Ergonomic API: Pass datetime directly (normalized to Provided)
    effect1 = CreateAppointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        requested_time=datetime(2025, 1, 15, 10, 0),
        notes="Follow-up checkup",
    )

    print("Effect 1: datetime and str passed directly")
    print(f"  requested_time type: {type(effect1.requested_time).__name__}")
    assert isinstance(effect1.requested_time, Provided)
    print(f"  requested_time value: {effect1.requested_time.value}")
    assert isinstance(effect1.notes, Provided)
    print(f"  notes value: {effect1.notes.value}")

    # Ergonomic API: Omit parameters (normalized to Absent with default reason)
    effect2 = CreateAppointment(patient_id=patient_id, doctor_id=doctor_id)

    print("\nEffect 2: parameters omitted (defaults to None)")
    assert isinstance(effect2.requested_time, Absent)
    print(f"  requested_time: {effect2.requested_time}")
    assert isinstance(effect2.notes, Absent)
    print(f"  notes: {effect2.notes}")

    # Ergonomic API: Pass OptionalValue explicitly (idempotent)
    effect3 = CreateAppointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        requested_time=Absent(reason="flexible"),
        notes=Absent(reason="not_needed"),
    )

    print("\nEffect 3: OptionalValue passed explicitly (idempotent)")
    assert isinstance(effect3.requested_time, Absent)
    assert effect3.requested_time.reason == "flexible"
    print(f"  requested_time: {effect3.requested_time}")
    assert isinstance(effect3.notes, Absent)
    assert effect3.notes.reason == "not_needed"
    print(f"  notes: {effect3.notes}")

    print("\nKey takeaway: Local normalization enables ergonomic API + type-safe storage")


# ============================================================================
# Example 4: Boundary Conversion
# ============================================================================


class MockDatabaseAdapter:
    """Mock adapter showing boundary conversion pattern."""

    def save_appointment(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        requested_time: datetime | None,
        notes: str | None,
    ) -> str:
        """External API expects Optional (datetime | None, str | None).

        This simulates a real database API like sqlalchemy that uses None sentinel.
        """
        time_str = requested_time.isoformat() if requested_time else "flexible"
        notes_str = notes if notes else "no notes"
        return f"Appointment saved: {time_str}, {notes_str}"


def example4_boundary_conversion() -> None:
    """Demonstrate boundary conversion with from_optional_value()."""

    print("\n=== Example 4: Boundary Conversion ===\n")

    # Create effect with OptionalValue fields
    effect = CreateAppointment(
        patient_id=uuid4(),
        doctor_id=uuid4(),
        requested_time=datetime(2025, 1, 15, 10, 0),
        notes="Follow-up",
    )

    print("Effect with OptionalValue fields:")
    print(f"  requested_time: {effect.requested_time}")
    print(f"  notes: {effect.notes}")

    # Convert OptionalValue → Optional for external API
    requested_time_optional = from_optional_value(effect.requested_time)
    notes_optional = from_optional_value(effect.notes)

    print("\nConverted to Optional (T | None) for external API:")
    print(f"  requested_time: {requested_time_optional}")
    print(f"  notes: {notes_optional}")

    # Call external API with Optional
    adapter = MockDatabaseAdapter()
    result = adapter.save_appointment(
        patient_id=effect.patient_id,
        doctor_id=effect.doctor_id,
        requested_time=requested_time_optional,
        notes=notes_optional,
    )

    print(f"\nExternal API result: {result}")

    # Example with Absent fields
    effect_absent = CreateAppointment(patient_id=uuid4(), doctor_id=uuid4())

    print("\n\nEffect with Absent fields:")
    print(f"  requested_time: {effect_absent.requested_time}")
    print(f"  notes: {effect_absent.notes}")

    # Convert Absent → None
    requested_time_none = from_optional_value(effect_absent.requested_time)
    notes_none = from_optional_value(effect_absent.notes)

    print("\nConverted to None for external API:")
    print(f"  requested_time: {requested_time_none}")
    print(f"  notes: {notes_none}")

    result_absent = adapter.save_appointment(
        patient_id=effect_absent.patient_id,
        doctor_id=effect_absent.doctor_id,
        requested_time=requested_time_none,
        notes=notes_none,
    )

    print(f"\nExternal API result: {result_absent}")


# ============================================================================
# Example 5: Generator Programs
# ============================================================================


# Mock effect and result types for demonstration
@dataclass(frozen=True)
class GetPatient:
    """Mock effect to fetch patient."""

    patient_id: UUID


@dataclass(frozen=True)
class SendNotification:
    """Mock effect to send notification."""

    message: str


type MockEffect = GetPatient | SendNotification | CreateAppointment
type MockResult = Patient | str | None


def schedule_appointment_program(
    patient_id: UUID, doctor_id: UUID, requested_time: datetime | None, notes: str | None
) -> Generator[MockEffect, MockResult, str]:
    """Generator program demonstrating OptionalValue in effects.

    This shows how OptionalValue flows through:
    1. Effect construction (normalized from T | None)
    2. Pattern matching on results
    3. Conditional logic based on presence/absence
    """

    # Fetch patient
    patient = yield GetPatient(patient_id=patient_id)
    assert isinstance(patient, Patient)

    # Create appointment with OptionalValue parameters
    # Parameters automatically normalized by CreateAppointment.__init__
    appointment_effect = CreateAppointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        requested_time=requested_time,  # Normalized to OptionalValue
        notes=notes,  # Normalized to OptionalValue
    )

    # Pattern match on OptionalValue fields to build notification message
    match appointment_effect.requested_time:
        case Provided(value=time):
            time_msg = f"scheduled for {time.strftime('%Y-%m-%d %H:%M')}"
        case Absent(reason="flexible"):
            time_msg = "with flexible timing"
        case Absent():
            time_msg = "time TBD"

    match appointment_effect.notes:
        case Provided(value=note_text):
            notes_msg = f" - {note_text}"
        case Absent():
            notes_msg = ""

    # Send notification
    message = f"Appointment {time_msg}{notes_msg}"
    yield SendNotification(message=message)

    return f"Scheduled appointment for {patient.name}"


def example5_generator_programs() -> None:
    """Demonstrate OptionalValue in generator programs."""

    print("\n=== Example 5: Generator Programs ===\n")

    # Create a mock patient
    patient = Patient(
        id=uuid4(),
        name="Alice Johnson",
        email="alice@example.com",
        blood_type=Provided(value="O+"),
        emergency_contact=Provided(value="+1-555-0123"),
    )

    # Example 1: Program with all optionals provided
    print("Program 1: All optionals provided")
    program1 = schedule_appointment_program(
        patient_id=patient.id,
        doctor_id=uuid4(),
        requested_time=datetime(2025, 1, 15, 10, 0),
        notes="Follow-up checkup",
    )

    # Step through generator (simulated)
    effect1 = next(program1)  # GetPatient
    print(f"  Effect 1: {type(effect1).__name__}")

    effect2 = program1.send(patient)  # SendNotification
    assert isinstance(effect2, SendNotification), f"Expected SendNotification, got {type(effect2)}"
    print(f"  Effect 2: {type(effect2).__name__} - {effect2.message}")

    # Example 2: Program with optionals absent
    print("\nProgram 2: Optionals absent")
    program2 = schedule_appointment_program(
        patient_id=patient.id, doctor_id=uuid4(), requested_time=None, notes=None
    )

    effect1 = next(program2)  # GetPatient
    print(f"  Effect 1: {type(effect1).__name__}")

    effect2 = program2.send(patient)  # SendNotification
    assert isinstance(effect2, SendNotification), f"Expected SendNotification, got {type(effect2)}"
    print(f"  Effect 2: {type(effect2).__name__} - {effect2.message}")

    print("\nKey takeaway: OptionalValue flows seamlessly through generator programs")


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    """Run all OptionalValue examples."""

    print("\n" + "=" * 80)
    print("OptionalValue Pattern Examples")
    print("=" * 80)

    example1_basic_usage()
    example2_domain_models()
    example3_effect_normalization()
    example4_boundary_conversion()
    example5_generator_programs()

    print("\n" + "=" * 80)
    print("All examples completed successfully!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
