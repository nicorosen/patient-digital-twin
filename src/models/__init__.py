"""
Database models for patient health data.

Contains SQLAlchemy ORM models for:
- Patient demographics
- Clinical data (conditions, medications, allergies)
- Conversation history and audit logs
"""

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.models.clinical import Allergy, Condition, Medication
from src.models.clinical_extended import (
    FamilyHistory,
    LabResult,
    SocialHistory,
    VitalSigns,
)
from src.models.conversation import (
    ConsultationAuditLog,
    ConversationMessage,
    ConversationSession,
)
from src.models.patient import Patient
from src.models.patient_member import MemberRole, PatientMember
from src.models.user import User

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    # Patient
    "Patient",
    # Clinical
    "Condition",
    "Medication",
    "Allergy",
    # Clinical Extended
    "VitalSigns",
    "LabResult",
    "FamilyHistory",
    "SocialHistory",
    # Conversation
    "ConversationSession",
    "ConversationMessage",
    "ConsultationAuditLog",
    # User & Members
    "User",
    "PatientMember",
    "MemberRole",
]
