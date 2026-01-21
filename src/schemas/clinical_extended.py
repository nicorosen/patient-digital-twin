"""
Extended clinical Pydantic schemas for comprehensive EHR.

These schemas follow FHIR-inspired conventions for:
- VitalSigns: Blood pressure, heart rate, temperature, etc.
- LabResult: Laboratory test results with reference ranges
- FamilyHistory: Family medical history for risk assessment
- SocialHistory: Lifestyle factors (smoking, alcohol, exercise)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# ENUMS
# =============================================================================


class LabInterpretation(str, Enum):
    """Interpretation of lab results."""

    NORMAL = "normal"
    ABNORMAL = "abnormal"
    CRITICAL = "critical"
    INCONCLUSIVE = "inconclusive"


class FamilyRelationship(str, Enum):
    """Relationship types for family history."""

    MOTHER = "mother"
    FATHER = "father"
    SIBLING = "sibling"
    MATERNAL_GRANDMOTHER = "maternal_grandmother"
    MATERNAL_GRANDFATHER = "maternal_grandfather"
    PATERNAL_GRANDMOTHER = "paternal_grandmother"
    PATERNAL_GRANDFATHER = "paternal_grandfather"
    AUNT = "aunt"
    UNCLE = "uncle"
    CHILD = "child"
    OTHER = "other"


class SocialHistoryCategory(str, Enum):
    """Categories for social history."""

    SMOKING = "smoking"
    ALCOHOL = "alcohol"
    DRUGS = "drugs"
    EXERCISE = "exercise"
    DIET = "diet"
    OCCUPATION = "occupation"
    LIVING_SITUATION = "living_situation"
    STRESS = "stress"
    SLEEP = "sleep"
    OTHER = "other"


class SocialHistoryStatus(str, Enum):
    """Status for social history items."""

    CURRENT = "current"
    FORMER = "former"
    NEVER = "never"
    OCCASIONAL = "occasional"
    DAILY = "daily"
    UNKNOWN = "unknown"


# =============================================================================
# BASE SCHEMAS
# =============================================================================


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for created/updated timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# VITAL SIGNS SCHEMAS
# =============================================================================


class VitalSignsBase(BaseSchema):
    """Base vital signs schema with common fields."""

    recorded_at: datetime = Field(
        ...,
        description="When the measurements were taken",
    )
    systolic_bp: Optional[int] = Field(
        None,
        ge=0,
        le=300,
        description="Systolic blood pressure (mmHg)",
    )
    diastolic_bp: Optional[int] = Field(
        None,
        ge=0,
        le=200,
        description="Diastolic blood pressure (mmHg)",
    )
    heart_rate: Optional[int] = Field(
        None,
        ge=0,
        le=300,
        description="Heart rate (beats per minute)",
    )
    temperature: Optional[float] = Field(
        None,
        ge=30.0,
        le=45.0,
        description="Body temperature (Celsius)",
    )
    weight_kg: Optional[float] = Field(
        None,
        ge=0,
        le=500,
        description="Weight in kilograms",
    )
    height_cm: Optional[float] = Field(
        None,
        ge=0,
        le=300,
        description="Height in centimeters",
    )
    oxygen_saturation: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="SpO2 percentage",
    )
    notes: Optional[str] = Field(None, max_length=1000)


class VitalSignsCreate(VitalSignsBase):
    """Schema for creating vital signs."""

    patient_id: UUID


class VitalSignsUpdate(BaseSchema):
    """Schema for updating vital signs (all fields optional)."""

    recorded_at: Optional[datetime] = None
    systolic_bp: Optional[int] = Field(None, ge=0, le=300)
    diastolic_bp: Optional[int] = Field(None, ge=0, le=200)
    heart_rate: Optional[int] = Field(None, ge=0, le=300)
    temperature: Optional[float] = Field(None, ge=30.0, le=45.0)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    height_cm: Optional[float] = Field(None, ge=0, le=300)
    oxygen_saturation: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=1000)


class VitalSignsSchema(VitalSignsBase, TimestampMixin):
    """Complete vital signs schema with ID and timestamps."""

    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID

    @property
    def blood_pressure(self) -> Optional[str]:
        """Get formatted blood pressure."""
        if self.systolic_bp is not None and self.diastolic_bp is not None:
            return f"{self.systolic_bp}/{self.diastolic_bp}"
        return None

    @property
    def bmi(self) -> Optional[float]:
        """Calculate BMI if weight and height are available."""
        if self.weight_kg and self.height_cm:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m * height_m), 1)
        return None


# =============================================================================
# LAB RESULT SCHEMAS
# =============================================================================


class LabResultBase(BaseSchema):
    """Base lab result schema with common fields."""

    test_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the laboratory test",
    )
    test_code: Optional[str] = Field(
        None,
        max_length=50,
        description="LOINC code for the test",
    )
    value: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Result value as string",
    )
    value_numeric: Optional[float] = Field(
        None,
        description="Numeric value for comparison",
    )
    unit: Optional[str] = Field(
        None,
        max_length=50,
        description="Unit of measurement",
    )
    reference_range_low: Optional[float] = Field(
        None,
        description="Lower bound of normal range",
    )
    reference_range_high: Optional[float] = Field(
        None,
        description="Upper bound of normal range",
    )
    interpretation: Optional[LabInterpretation] = Field(
        None,
        description="Interpretation of the result",
    )
    result_date: datetime = Field(
        ...,
        description="When the test was performed",
    )
    notes: Optional[str] = Field(None, max_length=1000)


class LabResultCreate(LabResultBase):
    """Schema for creating a lab result."""

    patient_id: UUID


class LabResultUpdate(BaseSchema):
    """Schema for updating a lab result (all fields optional)."""

    test_name: Optional[str] = Field(None, min_length=1, max_length=255)
    test_code: Optional[str] = Field(None, max_length=50)
    value: Optional[str] = Field(None, min_length=1, max_length=100)
    value_numeric: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=50)
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    interpretation: Optional[LabInterpretation] = None
    result_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)


class LabResultSchema(LabResultBase, TimestampMixin):
    """Complete lab result schema with ID and timestamps."""

    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID

    @property
    def is_abnormal(self) -> Optional[bool]:
        """Check if result is outside reference range."""
        if self.value_numeric is None:
            return None
        if self.reference_range_low is not None and self.value_numeric < self.reference_range_low:
            return True
        if self.reference_range_high is not None and self.value_numeric > self.reference_range_high:
            return True
        return False

    @property
    def reference_range(self) -> Optional[str]:
        """Get formatted reference range."""
        if self.reference_range_low is not None and self.reference_range_high is not None:
            unit_str = f" {self.unit}" if self.unit else ""
            return f"{self.reference_range_low}-{self.reference_range_high}{unit_str}"
        return None


# =============================================================================
# FAMILY HISTORY SCHEMAS
# =============================================================================


class FamilyHistoryBase(BaseSchema):
    """Base family history schema with common fields."""

    relation: FamilyRelationship = Field(
        ...,
        description="Relationship to patient",
    )
    condition_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the medical condition",
    )
    onset_age: Optional[int] = Field(
        None,
        ge=0,
        le=150,
        description="Age when the relative was diagnosed",
    )
    notes: Optional[str] = Field(None, max_length=1000)


class FamilyHistoryCreate(FamilyHistoryBase):
    """Schema for creating family history."""

    patient_id: UUID


class FamilyHistoryUpdate(BaseSchema):
    """Schema for updating family history (all fields optional)."""

    relation: Optional[FamilyRelationship] = None
    condition_name: Optional[str] = Field(None, min_length=1, max_length=255)
    onset_age: Optional[int] = Field(None, ge=0, le=150)
    notes: Optional[str] = Field(None, max_length=1000)


class FamilyHistorySchema(FamilyHistoryBase, TimestampMixin):
    """Complete family history schema with ID and timestamps."""

    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID


# =============================================================================
# SOCIAL HISTORY SCHEMAS
# =============================================================================


class SocialHistoryBase(BaseSchema):
    """Base social history schema with common fields."""

    category: SocialHistoryCategory = Field(
        ...,
        description="Category of social history",
    )
    status: SocialHistoryStatus = Field(
        ...,
        description="Current status",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Detailed description",
    )
    notes: Optional[str] = Field(None, max_length=1000)


class SocialHistoryCreate(SocialHistoryBase):
    """Schema for creating social history."""

    patient_id: UUID


class SocialHistoryUpdate(BaseSchema):
    """Schema for updating social history (all fields optional)."""

    category: Optional[SocialHistoryCategory] = None
    status: Optional[SocialHistoryStatus] = None
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class SocialHistorySchema(SocialHistoryBase, TimestampMixin):
    """Complete social history schema with ID and timestamps."""

    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID
