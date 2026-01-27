"""
Pydantic schemas for User model validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
import re


class UserRole(str, Enum):
    """Roles for user access control."""

    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"
    CAREGIVER = "caregiver"


class UserBase(BaseModel):
    """Base schema with common user attributes."""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.PATIENT

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Simple email validation."""
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Simple email validation."""
        if v is not None and not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower() if v else None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=6)
    is_active: Optional[bool] = None


class UserSchema(UserBase):
    """Full user schema for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserSummary(BaseModel):
    """Minimal user info for listing members."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    name: str
