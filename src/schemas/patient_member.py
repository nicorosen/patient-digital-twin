"""
Pydantic schemas for PatientMember model validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.schemas.user import UserSummary


class MemberRole(str, Enum):
    """Roles for patient member access."""

    DOCTOR = "doctor"
    PATIENT = "patient"
    CAREGIVER = "caregiver"


class PatientMemberBase(BaseModel):
    """Base schema with common patient member attributes."""

    role: MemberRole = MemberRole.CAREGIVER


class PatientMemberCreate(PatientMemberBase):
    """Schema for creating a new patient member."""

    user_id: UUID
    patient_id: UUID


class PatientMemberUpdate(BaseModel):
    """Schema for updating a patient member's role."""

    role: MemberRole


class PatientMemberSchema(PatientMemberBase):
    """Full patient member schema for API responses."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    patient_id: UUID
    created_at: datetime
    updated_at: datetime


class PatientMemberWithUser(PatientMemberSchema):
    """Patient member schema with user details included."""

    user: Optional[UserSummary] = None
