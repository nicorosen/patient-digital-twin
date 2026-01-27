"""
PatientMember model for managing user access to patient data.

Controls which users can access which patients' data and with what role.
"""

from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.patient import Patient
    from src.models.user import User


class MemberRole(str, Enum):
    """Roles for patient member access."""

    DOCTOR = "doctor"
    PATIENT = "patient"
    CAREGIVER = "caregiver"


class PatientMember(Base, TimestampMixin):
    """
    Association model linking users to patients with specific roles.

    Uses a composite primary key of (user_id, patient_id).

    Attributes:
        user_id: Foreign key to User
        patient_id: Foreign key to Patient
        role: The user's role for this patient (doctor, patient, caregiver)
        created_at: When the membership was created
        updated_at: When the membership was last updated
    """

    __tablename__ = "patient_members"

    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    patient_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MemberRole.CAREGIVER.value,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="patient_memberships",
    )
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="members",
    )

    def __repr__(self) -> str:
        return f"<PatientMember(user_id={self.user_id}, patient_id={self.patient_id}, role='{self.role}')>"
