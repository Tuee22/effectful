"""Prescription domain model with medication interaction warnings ADT."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.domain.optional_value import OptionalValue


@dataclass(frozen=True)
class Prescription:
    """Prescription entity.

    Immutable domain model following Effectful patterns.
    """

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills_remaining: int
    notes: OptionalValue[str]
    created_at: datetime
    expires_at: datetime


# Medication Interaction Check ADT
@dataclass(frozen=True)
class NoInteractions:
    """No medication interactions detected."""

    medications_checked: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "medications_checked", tuple(self.medications_checked))


@dataclass(frozen=True)
class MedicationInteractionWarning:
    """Warning about drug interactions.

    Severity levels:
    - minor: Low clinical significance
    - moderate: May require monitoring
    - severe: Contraindicated, should not be prescribed together
    """

    medications: tuple[str, ...]
    severity: Literal["minor", "moderate", "severe"]
    description: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "medications", tuple(self.medications))


type MedicationCheckResult = NoInteractions | MedicationInteractionWarning
