"""
Pydantic schemas for PatientMember model validation and serialization.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.schemas.user import UserSummary


class PatientMemberCreate(BaseModel):
    """Schema for creating a new patient member."""

    user_id: UUID
    patient_id: UUID


class PatientMemberSchema(BaseModel):
    """Full patient member schema for API responses."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    patient_id: UUID
    created_at: datetime
    updated_at: datetime


class PatientMemberWithUser(PatientMemberSchema):
    """Patient member schema with user details included."""

    user: Optional[UserSummary] = None
