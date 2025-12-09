"""Prescription domain model with medication interaction warnings ADT."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from effectful.domain.optional_value import OptionalValue


@dataclass(frozen=True)
class Prescription:
    """Prescription entity.

    Immutable domain model following Effectful patterns.

    Attributes:
        id: Unique prescription identifier
        patient_id: Patient UUID reference
        doctor_id: Prescribing doctor UUID reference
        medication: Medication name
        dosage: Dosage instructions
        frequency: Frequency text (e.g., "twice daily")
        duration_days: Prescription duration in days
        refills_remaining: Number of refills allowed
        notes: Optional prescription notes
        created_at: Timestamp when prescription was created
        expires_at: Prescription expiration timestamp
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
    """No medication interactions detected.

    Attributes:
        medications_checked: Tuple of medication names that were checked
    """

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

    Attributes:
        medications: Tuple of interacting medication names
        severity: Severity level of the interaction
        description: Human-readable description of the interaction
    """

    medications: tuple[str, ...]
    severity: Literal["minor", "moderate", "severe"]
    description: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "medications", tuple(self.medications))


type MedicationCheckResult = NoInteractions | MedicationInteractionWarning
"""Medication interaction check result ADT.

Variants:
    NoInteractions: No interactions detected among checked medications
    MedicationInteractionWarning: Interactions detected with severity level
"""
