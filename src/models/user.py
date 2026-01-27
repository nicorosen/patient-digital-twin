"""
User model for authentication and authorization.

Stores user credentials and profile information.
"""

from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.patient_member import PatientMember


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model for application authentication.

    Attributes:
        id: Unique identifier (UUID)
        username: Unique username for login
        email: Unique email address
        hashed_password: Bcrypt hashed password
        name: Display name
        is_active: Whether the user account is active
        created_at: When the record was created
        updated_at: When the record was last updated
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship to patient memberships
    patient_memberships: Mapped[List["PatientMember"]] = relationship(
        "PatientMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', name='{self.name}')>"
