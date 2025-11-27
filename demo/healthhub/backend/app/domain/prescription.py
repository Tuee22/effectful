"""Prescription domain model with medication interaction warnings ADT."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


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
    notes: str | None
    created_at: datetime
    expires_at: datetime


# Medication Interaction Check ADT
@dataclass(frozen=True)
class NoInteractions:
    """No medication interactions detected."""

    medications_checked: list[str]


@dataclass(frozen=True)
class MedicationInteractionWarning:
    """Warning about drug interactions.

    Severity levels:
    - minor: Low clinical significance
    - moderate: May require monitoring
    - severe: Contraindicated, should not be prescribed together
    """

    medications: list[str]
    severity: Literal["minor", "moderate", "severe"]
    description: str


type MedicationCheckResult = NoInteractions | MedicationInteractionWarning
