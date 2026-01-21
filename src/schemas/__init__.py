"""
Pydantic schemas for data validation.

FHIR-inspired schemas for:
- Patient resources
- Clinical resources (Condition, Medication, Allergy)
- Extended clinical resources (VitalSigns, LabResult, FamilyHistory, SocialHistory)
- API request/response models
"""

from src.schemas.fhir import (
    # Enums
    AllergyCategory,
    AllergyCriticality,
    ClinicalStatus,
    Gender,
    MedicationStatus,
    Severity,
    # Patient schemas
    PatientBase,
    PatientCreate,
    PatientSchema,
    PatientUpdate,
    # Condition schemas
    ConditionBase,
    ConditionCreate,
    ConditionSchema,
    ConditionUpdate,
    # Medication schemas
    MedicationBase,
    MedicationCreate,
    MedicationSchema,
    MedicationUpdate,
    # Allergy schemas
    AllergyBase,
    AllergyCreate,
    AllergySchema,
    AllergyUpdate,
    # Composite schemas
    DeidentifiedContext,
    PatientProfile,
)

from src.schemas.clinical_extended import (
    # Enums
    FamilyRelationship,
    LabInterpretation,
    SocialHistoryCategory,
    SocialHistoryStatus,
    # VitalSigns schemas
    VitalSignsBase,
    VitalSignsCreate,
    VitalSignsSchema,
    VitalSignsUpdate,
    # LabResult schemas
    LabResultBase,
    LabResultCreate,
    LabResultSchema,
    LabResultUpdate,
    # FamilyHistory schemas
    FamilyHistoryBase,
    FamilyHistoryCreate,
    FamilyHistorySchema,
    FamilyHistoryUpdate,
    # SocialHistory schemas
    SocialHistoryBase,
    SocialHistoryCreate,
    SocialHistorySchema,
    SocialHistoryUpdate,
)

from src.schemas.conversation import (
    # Enums
    ConversationMode,
    # Session schemas
    ConversationSessionBase,
    ConversationSessionCreate,
    ConversationSessionSchema,
    ConversationSessionSummary,
    ConversationSessionUpdate,
    ConversationSessionWithMessages,
    # Message schemas
    ConversationMessageBase,
    ConversationMessageCreate,
    ConversationMessageSchema,
)

__all__ = [
    # Enums
    "Gender",
    "ClinicalStatus",
    "Severity",
    "MedicationStatus",
    "AllergyCategory",
    "AllergyCriticality",
    "LabInterpretation",
    "FamilyRelationship",
    "SocialHistoryCategory",
    "SocialHistoryStatus",
    # Patient
    "PatientBase",
    "PatientCreate",
    "PatientUpdate",
    "PatientSchema",
    # Condition
    "ConditionBase",
    "ConditionCreate",
    "ConditionUpdate",
    "ConditionSchema",
    # Medication
    "MedicationBase",
    "MedicationCreate",
    "MedicationUpdate",
    "MedicationSchema",
    # Allergy
    "AllergyBase",
    "AllergyCreate",
    "AllergyUpdate",
    "AllergySchema",
    # VitalSigns
    "VitalSignsBase",
    "VitalSignsCreate",
    "VitalSignsUpdate",
    "VitalSignsSchema",
    # LabResult
    "LabResultBase",
    "LabResultCreate",
    "LabResultUpdate",
    "LabResultSchema",
    # FamilyHistory
    "FamilyHistoryBase",
    "FamilyHistoryCreate",
    "FamilyHistoryUpdate",
    "FamilyHistorySchema",
    # SocialHistory
    "SocialHistoryBase",
    "SocialHistoryCreate",
    "SocialHistoryUpdate",
    "SocialHistorySchema",
    # Composite
    "PatientProfile",
    "DeidentifiedContext",
    # Conversation
    "ConversationMode",
    "ConversationSessionBase",
    "ConversationSessionCreate",
    "ConversationSessionUpdate",
    "ConversationSessionSchema",
    "ConversationSessionSummary",
    "ConversationSessionWithMessages",
    "ConversationMessageBase",
    "ConversationMessageCreate",
    "ConversationMessageSchema",
]
