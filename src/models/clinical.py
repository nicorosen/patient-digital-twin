"""
Clinical data models for conditions, medications, and allergies.

These models follow FHIR resource conventions (simplified for MVP):
- Condition: Health conditions/diagnoses (problem list)
- Medication: Medications the patient is taking
- Allergy: Allergies and intolerances
"""

from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.patient import Patient


class Condition(Base, UUIDMixin, TimestampMixin):
    """
    Condition model representing a clinical condition or diagnosis.

    Based on FHIR Condition resource (simplified).

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to the patient
        code: ICD-10 or SNOMED code (optional)
        display_name: Human-readable condition name
        clinical_status: Current status (active, resolved, etc.)
        onset_date: When the condition started/was diagnosed
        severity: Severity level (mild, moderate, severe)
        notes: Additional notes about the condition
    """

    __tablename__ = "conditions"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    clinical_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )
    onset_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="conditions")

    def __repr__(self) -> str:
        return f"<Condition(id={self.id}, name='{self.display_name}', status='{self.clinical_status}')>"

    def to_document(self) -> str:
        """Convert condition to a document string for RAG indexing."""
        parts = [f"Patient has {self.clinical_status} {self.display_name}"]

        if self.onset_date:
            parts.append(f"diagnosed on {self.onset_date.strftime('%B %Y')}")

        if self.severity:
            parts.append(f"with {self.severity} severity")

        if self.notes:
            parts.append(f"Notes: {self.notes}")

        return ". ".join(parts) + "."


class Medication(Base, UUIDMixin, TimestampMixin):
    """
    Medication model representing a medication the patient takes.

    Based on FHIR MedicationStatement resource (simplified).

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to the patient
        code: RxNorm code (optional)
        display_name: Medication name
        dosage: Dosage amount (e.g., "500mg")
        frequency: How often taken (e.g., "twice daily")
        route: Route of administration (e.g., "oral")
        status: Current status (active, discontinued, etc.)
        start_date: When the medication was started
        end_date: When the medication was stopped (if applicable)
        reason: Why the medication is being taken
    """

    __tablename__ = "medications"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    frequency: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    route: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="medications")

    def __repr__(self) -> str:
        dosage_str = f" {self.dosage}" if self.dosage else ""
        return f"<Medication(id={self.id}, name='{self.display_name}{dosage_str}', status='{self.status}')>"

    def to_document(self) -> str:
        """Convert medication to a document string for RAG indexing."""
        parts = [f"Patient is taking {self.display_name}"]

        if self.dosage:
            parts[0] += f" {self.dosage}"

        if self.frequency:
            parts.append(f"{self.frequency}")

        if self.route:
            parts.append(f"administered {self.route}")

        if self.reason:
            parts.append(f"for {self.reason}")

        if self.status != "active":
            parts.append(f"(status: {self.status})")

        return " ".join(parts) + "."


class Allergy(Base, UUIDMixin, TimestampMixin):
    """
    Allergy model representing an allergy or intolerance.

    Based on FHIR AllergyIntolerance resource (simplified).

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to the patient
        code: Allergy code (optional)
        substance: What the patient is allergic to
        category: Type of allergen (food, medication, environment, biologic)
        criticality: How critical/severe (low, high, unable-to-assess)
        reaction: Description of the allergic reaction
        onset_date: When the allergy was first identified
    """

    __tablename__ = "allergies"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    substance: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="medication",
    )
    criticality: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    reaction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    onset_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="allergies")

    def __repr__(self) -> str:
        crit = f" ({self.criticality})" if self.criticality else ""
        return f"<Allergy(id={self.id}, substance='{self.substance}'{crit})>"

    def to_document(self) -> str:
        """Convert allergy to a document string for RAG indexing."""
        parts = [f"Patient is allergic to {self.substance}"]

        if self.category:
            parts.append(f"({self.category} allergy)")

        if self.criticality:
            parts.append(f"with {self.criticality} criticality")

        if self.reaction:
            parts.append(f"Reaction: {self.reaction}")

        return " ".join(parts) + "."
