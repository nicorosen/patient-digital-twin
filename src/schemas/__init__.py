"""
Pydantic schemas for data validation.

FHIR-inspired schemas for:
- Patient resources
- Clinical resources (Condition, Medication, Allergy)
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

__all__ = [
    # Enums
    "Gender",
    "ClinicalStatus",
    "Severity",
    "MedicationStatus",
    "AllergyCategory",
    "AllergyCriticality",
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
    # Composite
    "PatientProfile",
    "DeidentifiedContext",
]
