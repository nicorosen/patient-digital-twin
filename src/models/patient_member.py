"""
PatientMember model for managing user access to patient data.

Controls which users can access which patients' data.
"""

from typing import TYPE_CHECKING
from uuid import UUID as PyUUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.patient import Patient
    from src.models.user import User


class PatientMember(Base, TimestampMixin):
    """
    Association model linking users to patients.

    Uses a composite primary key of (user_id, patient_id).
    The user's role (on the User model) determines permissions.

    Attributes:
        user_id: Foreign key to User
        patient_id: Foreign key to Patient
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
        return f"<PatientMember(user_id={self.user_id}, patient_id={self.patient_id})>"
