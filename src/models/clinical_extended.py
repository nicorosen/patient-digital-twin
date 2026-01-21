"""
Extended clinical data models for comprehensive EHR.

These models extend the core clinical data with:
- VitalSigns: Blood pressure, heart rate, temperature, etc.
- LabResult: Laboratory test results with reference ranges
- FamilyHistory: Family medical history for risk assessment
- SocialHistory: Lifestyle factors (smoking, alcohol, exercise)
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.patient import Patient


class VitalSigns(Base, UUIDMixin, TimestampMixin):
    """
    VitalSigns model representing a set of vital sign measurements.

    Captures point-in-time physiological measurements including:
    - Blood pressure (systolic/diastolic)
    - Heart rate
    - Temperature
    - Weight/Height
    - Oxygen saturation

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to the patient
        recorded_at: When the measurements were taken
        systolic_bp: Systolic blood pressure (mmHg)
        diastolic_bp: Diastolic blood pressure (mmHg)
        heart_rate: Heart rate (beats per minute)
        temperature: Body temperature (Celsius)
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        oxygen_saturation: SpO2 percentage
        notes: Additional notes about the measurements
    """

    __tablename__ = "vital_signs"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    systolic_bp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    diastolic_bp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    oxygen_saturation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="vital_signs")

    def __repr__(self) -> str:
        bp = f"{self.systolic_bp}/{self.diastolic_bp}" if self.systolic_bp else "N/A"
        return f"<VitalSigns(id={self.id}, bp={bp}, recorded={self.recorded_at})>"

    def to_document(self) -> str:
        """Convert vital signs to a document string for RAG indexing."""
        parts = [f"Vital signs recorded on {self.recorded_at.strftime('%B %d, %Y')}:"]

        if self.systolic_bp and self.diastolic_bp:
            parts.append(f"Blood pressure {self.systolic_bp}/{self.diastolic_bp} mmHg")

        if self.heart_rate:
            parts.append(f"Heart rate {self.heart_rate} bpm")

        if self.temperature:
            parts.append(f"Temperature {self.temperature}°C")

        if self.weight_kg:
            parts.append(f"Weight {self.weight_kg} kg")

        if self.height_cm:
            parts.append(f"Height {self.height_cm} cm")

        if self.oxygen_saturation:
            parts.append(f"Oxygen saturation {self.oxygen_saturation}%")

        if self.notes:
            parts.append(f"Notes: {self.notes}")

        return " ".join(parts)


class LabResult(Base, UUIDMixin, TimestampMixin):
    """
    LabResult model representing a laboratory test result.

    Captures structured lab results with reference ranges for interpretation.

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to the patient
        test_name: Name of the laboratory test
        test_code: LOINC code for the test (optional)
        value: Result value as string (for flexibility)
        value_numeric: Numeric value for comparison (optional)
        unit: Unit of measurement
        reference_range_low: Lower bound of normal range
        reference_range_high: Upper bound of normal range
        interpretation: normal, abnormal, critical
        result_date: When the test was performed
        notes: Additional notes about the result
    """

    __tablename__ = "lab_results"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    test_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    value_numeric: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_range_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reference_range_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    interpretation: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    result_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="lab_results")

    def __repr__(self) -> str:
        unit_str = f" {self.unit}" if self.unit else ""
        return f"<LabResult(id={self.id}, test='{self.test_name}', value='{self.value}{unit_str}')>"

    def to_document(self) -> str:
        """Convert lab result to a document string for RAG indexing."""
        unit_str = f" {self.unit}" if self.unit else ""
        parts = [
            f"Lab result for {self.test_name}: {self.value}{unit_str}",
            f"on {self.result_date.strftime('%B %d, %Y')}"
        ]

        if self.reference_range_low is not None and self.reference_range_high is not None:
            parts.append(
                f"(reference range: {self.reference_range_low}-{self.reference_range_high}{unit_str})"
            )

        if self.interpretation:
            parts.append(f"Interpretation: {self.interpretation}")

        if self.notes:
            parts.append(f"Notes: {self.notes}")

        return " ".join(parts)


class FamilyHistory(Base, UUIDMixin, TimestampMixin):
    """
    FamilyHistory model representing family medical history.

    Important for risk assessment and genetic predisposition analysis.

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to the patient
        relation: Relationship to patient (mother, father, sibling, etc.)
        condition_name: Name of the medical condition
        onset_age: Age when the relative was diagnosed (optional)
        notes: Additional notes about the condition
    """

    __tablename__ = "family_history"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation: Mapped[str] = mapped_column(String(50), nullable=False)
    condition_name: Mapped[str] = mapped_column(String(255), nullable=False)
    onset_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="family_history")

    def __repr__(self) -> str:
        return f"<FamilyHistory(id={self.id}, relation='{self.relation}', condition='{self.condition_name}')>"

    def to_document(self) -> str:
        """Convert family history to a document string for RAG indexing."""
        parts = [f"Patient's {self.relation} has/had {self.condition_name}"]

        if self.onset_age:
            parts.append(f"diagnosed at age {self.onset_age}")

        if self.notes:
            parts.append(f"Notes: {self.notes}")

        return ". ".join(parts) + "."


class SocialHistory(Base, UUIDMixin, TimestampMixin):
    """
    SocialHistory model representing lifestyle and social factors.

    Captures important lifestyle factors that affect health outcomes.

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to the patient
        category: Category of social history (smoking, alcohol, exercise, diet, occupation)
        status: Current status (current, former, never)
        description: Detailed description of the behavior/factor
        notes: Additional notes
    """

    __tablename__ = "social_history"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="social_history")

    def __repr__(self) -> str:
        return f"<SocialHistory(id={self.id}, category='{self.category}', status='{self.status}')>"

    def to_document(self) -> str:
        """Convert social history to a document string for RAG indexing."""
        parts = [f"Patient's {self.category} status: {self.status}"]

        if self.description:
            parts.append(self.description)

        if self.notes:
            parts.append(f"Notes: {self.notes}")

        return ". ".join(parts) + "."
