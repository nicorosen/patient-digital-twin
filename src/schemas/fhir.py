"""
FHIR-inspired Pydantic schemas for patient health data.

These schemas follow FHIR (Fast Healthcare Interoperability Resources) conventions
but are simplified for MVP. They provide validation and serialization for:
- Patient demographics
- Conditions (problem list)
- Medications
- Allergies

Reference: https://www.hl7.org/fhir/
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# ENUMS (FHIR Value Sets)
# =============================================================================


class Gender(str, Enum):
    """Administrative gender - FHIR AdministrativeGender value set."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class ClinicalStatus(str, Enum):
    """Clinical status of a condition - FHIR Condition Clinical Status Codes."""

    ACTIVE = "active"
    RECURRENCE = "recurrence"
    RELAPSE = "relapse"
    INACTIVE = "inactive"
    REMISSION = "remission"
    RESOLVED = "resolved"


class Severity(str, Enum):
    """Severity of a condition - FHIR Condition Severity Codes."""

    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class MedicationStatus(str, Enum):
    """Status of a medication - FHIR MedicationStatement Status Codes."""

    ACTIVE = "active"
    ON_HOLD = "on-hold"
    DISCONTINUED = "discontinued"
    COMPLETED = "completed"


class AllergyCategory(str, Enum):
    """Category of allergy - FHIR AllergyIntolerance Category Codes."""

    FOOD = "food"
    MEDICATION = "medication"
    ENVIRONMENT = "environment"
    BIOLOGIC = "biologic"


class AllergyCriticality(str, Enum):
    """Criticality of allergy - FHIR AllergyIntolerance Criticality Codes."""

    LOW = "low"
    HIGH = "high"
    UNABLE_TO_ASSESS = "unable-to-assess"


# =============================================================================
# BASE SCHEMAS
# =============================================================================


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,  # Allow creating from ORM models
        populate_by_name=True,  # Allow using field names or aliases
    )


class TimestampMixin(BaseModel):
    """Mixin for created/updated timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# PATIENT SCHEMAS
# =============================================================================


class PatientBase(BaseSchema):
    """Base patient schema with common fields."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: Gender


class PatientCreate(PatientBase):
    """Schema for creating a new patient."""

    pass


class PatientUpdate(BaseSchema):
    """Schema for updating a patient (all fields optional)."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None


class PatientSchema(PatientBase, TimestampMixin):
    """Complete patient schema with ID and timestamps."""

    id: UUID = Field(default_factory=uuid4)

    @property
    def full_name(self) -> str:
        """Get patient's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        """Calculate patient's age in years."""
        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )


# =============================================================================
# CONDITION SCHEMAS
# =============================================================================


class ConditionBase(BaseSchema):
    """Base condition schema with common fields."""

    code: Optional[str] = Field(
        None,
        max_length=50,
        description="ICD-10 or SNOMED code",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable condition name",
    )
    clinical_status: ClinicalStatus = Field(default=ClinicalStatus.ACTIVE)
    onset_date: Optional[date] = Field(
        None,
        description="When the condition was first diagnosed/noticed",
    )
    severity: Optional[Severity] = None
    notes: Optional[str] = Field(None, max_length=1000)


class ConditionCreate(ConditionBase):
    """Schema for creating a new condition."""

    patient_id: UUID


class ConditionUpdate(BaseSchema):
    """Schema for updating a condition (all fields optional)."""

    code: Optional[str] = Field(None, max_length=50)
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    clinical_status: Optional[ClinicalStatus] = None
    onset_date: Optional[date] = None
    severity: Optional[Severity] = None
    notes: Optional[str] = Field(None, max_length=1000)


class ConditionSchema(ConditionBase, TimestampMixin):
    """Complete condition schema with ID and timestamps."""

    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID


# =============================================================================
# MEDICATION SCHEMAS
# =============================================================================


class MedicationBase(BaseSchema):
    """Base medication schema with common fields."""

    code: Optional[str] = Field(
        None,
        max_length=50,
        description="RxNorm code",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Medication name",
    )
    dosage: Optional[str] = Field(
        None,
        max_length=100,
        description="Dosage amount (e.g., '500mg')",
    )
    frequency: Optional[str] = Field(
        None,
        max_length=100,
        description="How often taken (e.g., 'twice daily')",
    )
    route: Optional[str] = Field(
        None,
        max_length=50,
        description="Route of administration (e.g., 'oral')",
    )
    status: MedicationStatus = Field(default=MedicationStatus.ACTIVE)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = Field(
        None,
        max_length=255,
        description="Reason for taking medication",
    )


class MedicationCreate(MedicationBase):
    """Schema for creating a new medication."""

    patient_id: UUID


class MedicationUpdate(BaseSchema):
    """Schema for updating a medication (all fields optional)."""

    code: Optional[str] = Field(None, max_length=50)
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    dosage: Optional[str] = Field(None, max_length=100)
    frequency: Optional[str] = Field(None, max_length=100)
    route: Optional[str] = Field(None, max_length=50)
    status: Optional[MedicationStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = Field(None, max_length=255)


class MedicationSchema(MedicationBase, TimestampMixin):
    """Complete medication schema with ID and timestamps."""

    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID


# =============================================================================
# ALLERGY SCHEMAS
# =============================================================================


class AllergyBase(BaseSchema):
    """Base allergy schema with common fields."""

    code: Optional[str] = Field(
        None,
        max_length=50,
        description="Allergy code (e.g., RxNorm for medications)",
    )
    substance: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Substance that causes the allergy",
    )
    category: AllergyCategory = Field(
        default=AllergyCategory.MEDICATION,
        description="Type of allergen",
    )
    criticality: Optional[AllergyCriticality] = Field(
        None,
        description="How critical/severe reactions typically are",
    )
    reaction: Optional[str] = Field(
        None,
        max_length=500,
        description="Description of allergic reaction",
    )
    onset_date: Optional[date] = Field(
        None,
        description="When the allergy was first identified",
    )


class AllergyCreate(AllergyBase):
    """Schema for creating a new allergy."""

    patient_id: UUID


class AllergyUpdate(BaseSchema):
    """Schema for updating an allergy (all fields optional)."""

    code: Optional[str] = Field(None, max_length=50)
    substance: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[AllergyCategory] = None
    criticality: Optional[AllergyCriticality] = None
    reaction: Optional[str] = Field(None, max_length=500)
    onset_date: Optional[date] = None


class AllergySchema(AllergyBase, TimestampMixin):
    """Complete allergy schema with ID and timestamps."""

    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID


# =============================================================================
# COMPOSITE SCHEMAS
# =============================================================================


class PatientProfile(BaseSchema):
    """Complete patient profile with all clinical data."""

    patient: PatientSchema
    conditions: list[ConditionSchema] = Field(default_factory=list)
    medications: list[MedicationSchema] = Field(default_factory=list)
    allergies: list[AllergySchema] = Field(default_factory=list)

    @property
    def active_conditions(self) -> list[ConditionSchema]:
        """Get only active conditions."""
        return [c for c in self.conditions if c.clinical_status == ClinicalStatus.ACTIVE]

    @property
    def active_medications(self) -> list[MedicationSchema]:
        """Get only active medications."""
        return [m for m in self.medications if m.status == MedicationStatus.ACTIVE]


class DeidentifiedContext(BaseSchema):
    """
    De-identified patient context for specialist consultation.

    Contains only non-identifying information safe to share
    with external specialist agents.
    """

    age: int = Field(..., ge=0, le=150)
    gender: str
    conditions: list[str] = Field(
        default_factory=list,
        description="List of active condition names only",
    )
    medications: list[str] = Field(
        default_factory=list,
        description="List of active medications with dosage",
    )
    allergies: list[str] = Field(
        default_factory=list,
        description="List of allergy substances only",
    )

    @classmethod
    def from_patient_profile(cls, profile: PatientProfile) -> "DeidentifiedContext":
        """Create de-identified context from a patient profile."""
        return cls(
            age=profile.patient.age,
            gender=profile.patient.gender.value,
            conditions=[c.display_name for c in profile.active_conditions],
            medications=[
                f"{m.display_name} {m.dosage or ''}".strip()
                for m in profile.active_medications
            ],
            allergies=[a.substance for a in profile.allergies],
        )
