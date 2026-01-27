"""
Patient model for storing patient demographics.

This model follows FHIR Patient resource conventions (simplified for MVP).
"""

from datetime import date
from typing import TYPE_CHECKING, List

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.clinical import Allergy, Condition, Medication
    from src.models.clinical_extended import (
        FamilyHistory,
        LabResult,
        Procedure,
        SocialHistory,
        VitalSigns,
    )
    from src.models.patient_member import PatientMember


class Patient(Base, UUIDMixin, TimestampMixin):
    """
    Patient model representing a person receiving healthcare.

    Attributes:
        id: Unique identifier (UUID)
        first_name: Patient's first/given name
        last_name: Patient's last/family name
        date_of_birth: Patient's birth date
        gender: Administrative gender (male, female, other, unknown)
        created_at: When the record was created
        updated_at: When the record was last updated
    """

    __tablename__ = "patients"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    conditions: Mapped[List["Condition"]] = relationship(
        "Condition",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    medications: Mapped[List["Medication"]] = relationship(
        "Medication",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    allergies: Mapped[List["Allergy"]] = relationship(
        "Allergy",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    vital_signs: Mapped[List["VitalSigns"]] = relationship(
        "VitalSigns",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    lab_results: Mapped[List["LabResult"]] = relationship(
        "LabResult",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    family_history: Mapped[List["FamilyHistory"]] = relationship(
        "FamilyHistory",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    social_history: Mapped[List["SocialHistory"]] = relationship(
        "SocialHistory",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    procedures: Mapped[List["Procedure"]] = relationship(
        "Procedure",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    members: Mapped[List["PatientMember"]] = relationship(
        "PatientMember",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        """Get patient's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        """Calculate patient's current age in years."""
        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, name='{self.full_name}', age={self.age})>"
