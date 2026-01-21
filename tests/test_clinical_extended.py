"""
Unit tests for extended clinical models and repositories.

Tests CRUD operations for:
- VitalSignsRepository
- LabResultRepository
- FamilyHistoryRepository
- SocialHistoryRepository
"""

from datetime import datetime
from uuid import uuid4

import pytest

from src.database.repositories import (
    FamilyHistoryRepository,
    LabResultRepository,
    SocialHistoryRepository,
    VitalSignsRepository,
)
from src.schemas import (
    FamilyHistoryCreate,
    FamilyHistoryUpdate,
    FamilyRelationship,
    LabInterpretation,
    LabResultCreate,
    LabResultUpdate,
    SocialHistoryCategory,
    SocialHistoryCreate,
    SocialHistoryStatus,
    SocialHistoryUpdate,
    VitalSignsCreate,
    VitalSignsUpdate,
)


# =============================================================================
# VITAL SIGNS REPOSITORY TESTS
# =============================================================================


class TestVitalSignsRepository:
    """Tests for VitalSignsRepository."""

    def test_create_vital_signs(self, db_session, sample_patient):
        """Test creating vital signs."""
        vital_signs_data = VitalSignsCreate(
            patient_id=sample_patient.id,
            recorded_at=datetime.now(),
            systolic_bp=125,
            diastolic_bp=82,
            heart_rate=75,
            temperature=36.7,
            weight_kg=72.5,
            height_cm=175.0,
            oxygen_saturation=98,
            notes="Routine check",
        )
        vital_signs = VitalSignsRepository.create(db_session, vital_signs_data)

        assert vital_signs.id is not None
        assert vital_signs.systolic_bp == 125
        assert vital_signs.diastolic_bp == 82
        assert vital_signs.heart_rate == 75

    def test_get_by_patient(self, db_session, sample_vital_signs):
        """Test getting vital signs by patient."""
        results = VitalSignsRepository.get_by_patient(
            db_session, sample_vital_signs.patient_id
        )
        assert len(results) == 1
        assert results[0].id == sample_vital_signs.id

    def test_get_by_patient_with_limit(self, db_session, sample_patient):
        """Test getting vital signs with limit."""
        # Create multiple vital signs
        for i in range(5):
            data = VitalSignsCreate(
                patient_id=sample_patient.id,
                recorded_at=datetime.now(),
                systolic_bp=120 + i,
                diastolic_bp=80,
            )
            VitalSignsRepository.create(db_session, data)

        results = VitalSignsRepository.get_by_patient(
            db_session, sample_patient.id, limit=3
        )
        assert len(results) == 3

    def test_get_by_id(self, db_session, sample_vital_signs):
        """Test getting vital signs by ID."""
        found = VitalSignsRepository.get_by_id(db_session, sample_vital_signs.id)
        assert found is not None
        assert found.id == sample_vital_signs.id

    def test_get_by_id_not_found(self, db_session):
        """Test getting non-existent vital signs."""
        found = VitalSignsRepository.get_by_id(db_session, uuid4())
        assert found is None

    def test_update_vital_signs(self, db_session, sample_vital_signs):
        """Test updating vital signs."""
        update_data = VitalSignsUpdate(
            heart_rate=80,
            notes="Updated notes",
        )
        updated = VitalSignsRepository.update(
            db_session, sample_vital_signs.id, update_data
        )

        assert updated is not None
        assert updated.heart_rate == 80
        assert updated.notes == "Updated notes"

    def test_delete_vital_signs(self, db_session, sample_vital_signs):
        """Test deleting vital signs."""
        result = VitalSignsRepository.delete(db_session, sample_vital_signs.id)
        assert result is True

        found = VitalSignsRepository.get_by_id(db_session, sample_vital_signs.id)
        assert found is None

    def test_to_document(self, sample_vital_signs):
        """Test vital signs to_document method."""
        doc = sample_vital_signs.to_document()
        assert "Vital signs recorded" in doc
        assert "Blood pressure 120/80" in doc
        assert "Heart rate 72" in doc


# =============================================================================
# LAB RESULT REPOSITORY TESTS
# =============================================================================


class TestLabResultRepository:
    """Tests for LabResultRepository."""

    def test_create_lab_result(self, db_session, sample_patient):
        """Test creating a lab result."""
        lab_result_data = LabResultCreate(
            patient_id=sample_patient.id,
            test_name="Blood Glucose",
            test_code="2345-7",
            value="95",
            value_numeric=95.0,
            unit="mg/dL",
            reference_range_low=70,
            reference_range_high=100,
            interpretation=LabInterpretation.NORMAL,
            result_date=datetime.now(),
        )
        lab_result = LabResultRepository.create(db_session, lab_result_data)

        assert lab_result.id is not None
        assert lab_result.test_name == "Blood Glucose"
        assert lab_result.value == "95"
        assert lab_result.interpretation == "normal"

    def test_get_by_patient(self, db_session, sample_lab_result):
        """Test getting lab results by patient."""
        results = LabResultRepository.get_by_patient(
            db_session, sample_lab_result.patient_id
        )
        assert len(results) == 1
        assert results[0].id == sample_lab_result.id

    def test_get_by_patient_filtered(self, db_session, sample_patient):
        """Test getting lab results filtered by test name."""
        # Create multiple lab results
        for test_name in ["HbA1c", "Blood Glucose", "Cholesterol"]:
            data = LabResultCreate(
                patient_id=sample_patient.id,
                test_name=test_name,
                value="100",
                result_date=datetime.now(),
            )
            LabResultRepository.create(db_session, data)

        results = LabResultRepository.get_by_patient(
            db_session, sample_patient.id, test_name="glucose"
        )
        assert len(results) == 1
        assert "Glucose" in results[0].test_name

    def test_get_by_id(self, db_session, sample_lab_result):
        """Test getting lab result by ID."""
        found = LabResultRepository.get_by_id(db_session, sample_lab_result.id)
        assert found is not None
        assert found.id == sample_lab_result.id

    def test_update_lab_result(self, db_session, sample_lab_result):
        """Test updating a lab result."""
        update_data = LabResultUpdate(
            interpretation=LabInterpretation.NORMAL,
            notes="Updated interpretation",
        )
        updated = LabResultRepository.update(
            db_session, sample_lab_result.id, update_data
        )

        assert updated is not None
        assert updated.interpretation == "normal"
        assert updated.notes == "Updated interpretation"

    def test_delete_lab_result(self, db_session, sample_lab_result):
        """Test deleting a lab result."""
        result = LabResultRepository.delete(db_session, sample_lab_result.id)
        assert result is True

        found = LabResultRepository.get_by_id(db_session, sample_lab_result.id)
        assert found is None

    def test_to_document(self, sample_lab_result):
        """Test lab result to_document method."""
        doc = sample_lab_result.to_document()
        assert "HbA1c" in doc
        assert "6.8" in doc
        assert "%" in doc


# =============================================================================
# FAMILY HISTORY REPOSITORY TESTS
# =============================================================================


class TestFamilyHistoryRepository:
    """Tests for FamilyHistoryRepository."""

    def test_create_family_history(self, db_session, sample_patient):
        """Test creating family history."""
        family_history_data = FamilyHistoryCreate(
            patient_id=sample_patient.id,
            relation=FamilyRelationship.MOTHER,
            condition_name="Hypertension",
            onset_age=50,
            notes="Controlled with medication",
        )
        family_history = FamilyHistoryRepository.create(db_session, family_history_data)

        assert family_history.id is not None
        assert family_history.relation == "mother"
        assert family_history.condition_name == "Hypertension"

    def test_get_by_patient(self, db_session, sample_family_history):
        """Test getting family history by patient."""
        results = FamilyHistoryRepository.get_by_patient(
            db_session, sample_family_history.patient_id
        )
        assert len(results) == 1
        assert results[0].id == sample_family_history.id

    def test_get_by_id(self, db_session, sample_family_history):
        """Test getting family history by ID."""
        found = FamilyHistoryRepository.get_by_id(db_session, sample_family_history.id)
        assert found is not None
        assert found.id == sample_family_history.id

    def test_update_family_history(self, db_session, sample_family_history):
        """Test updating family history."""
        update_data = FamilyHistoryUpdate(
            onset_age=60,
            notes="Updated notes",
        )
        updated = FamilyHistoryRepository.update(
            db_session, sample_family_history.id, update_data
        )

        assert updated is not None
        assert updated.onset_age == 60
        assert updated.notes == "Updated notes"

    def test_delete_family_history(self, db_session, sample_family_history):
        """Test deleting family history."""
        result = FamilyHistoryRepository.delete(db_session, sample_family_history.id)
        assert result is True

        found = FamilyHistoryRepository.get_by_id(db_session, sample_family_history.id)
        assert found is None

    def test_to_document(self, sample_family_history):
        """Test family history to_document method."""
        doc = sample_family_history.to_document()
        assert "father" in doc
        assert "Type 2 Diabetes" in doc
        assert "age 55" in doc


# =============================================================================
# SOCIAL HISTORY REPOSITORY TESTS
# =============================================================================


class TestSocialHistoryRepository:
    """Tests for SocialHistoryRepository."""

    def test_create_social_history(self, db_session, sample_patient):
        """Test creating social history."""
        social_history_data = SocialHistoryCreate(
            patient_id=sample_patient.id,
            category=SocialHistoryCategory.EXERCISE,
            status=SocialHistoryStatus.CURRENT,
            description="Runs 3x per week",
        )
        social_history = SocialHistoryRepository.create(db_session, social_history_data)

        assert social_history.id is not None
        assert social_history.category == "exercise"
        assert social_history.status == "current"

    def test_get_by_patient(self, db_session, sample_social_history):
        """Test getting social history by patient."""
        results = SocialHistoryRepository.get_by_patient(
            db_session, sample_social_history.patient_id
        )
        assert len(results) == 1
        assert results[0].id == sample_social_history.id

    def test_get_by_category(self, db_session, sample_social_history):
        """Test getting social history by category."""
        result = SocialHistoryRepository.get_by_category(
            db_session, sample_social_history.patient_id, "smoking"
        )
        assert result is not None
        assert result.category == "smoking"

    def test_get_by_id(self, db_session, sample_social_history):
        """Test getting social history by ID."""
        found = SocialHistoryRepository.get_by_id(db_session, sample_social_history.id)
        assert found is not None
        assert found.id == sample_social_history.id

    def test_update_social_history(self, db_session, sample_social_history):
        """Test updating social history."""
        update_data = SocialHistoryUpdate(
            status=SocialHistoryStatus.FORMER,
            description="Quit 5 years ago",
        )
        updated = SocialHistoryRepository.update(
            db_session, sample_social_history.id, update_data
        )

        assert updated is not None
        assert updated.status == "former"
        assert updated.description == "Quit 5 years ago"

    def test_delete_social_history(self, db_session, sample_social_history):
        """Test deleting social history."""
        result = SocialHistoryRepository.delete(db_session, sample_social_history.id)
        assert result is True

        found = SocialHistoryRepository.get_by_id(db_session, sample_social_history.id)
        assert found is None

    def test_to_document(self, sample_social_history):
        """Test social history to_document method."""
        doc = sample_social_history.to_document()
        assert "smoking" in doc
        assert "never" in doc


# =============================================================================
# SCHEMA TESTS
# =============================================================================


class TestVitalSignsSchema:
    """Tests for VitalSigns Pydantic schemas."""

    def test_vital_signs_create_validation(self, sample_patient):
        """Test VitalSignsCreate validation."""
        data = VitalSignsCreate(
            patient_id=sample_patient.id,
            recorded_at=datetime.now(),
            systolic_bp=120,
            diastolic_bp=80,
        )
        assert data.systolic_bp == 120
        assert data.heart_rate is None

    def test_vital_signs_bp_limits(self, sample_patient):
        """Test blood pressure validation limits."""
        with pytest.raises(ValueError):
            VitalSignsCreate(
                patient_id=sample_patient.id,
                recorded_at=datetime.now(),
                systolic_bp=400,  # Too high
            )


class TestLabResultSchema:
    """Tests for LabResult Pydantic schemas."""

    def test_lab_result_create_validation(self, sample_patient):
        """Test LabResultCreate validation."""
        data = LabResultCreate(
            patient_id=sample_patient.id,
            test_name="HbA1c",
            value="6.5",
            result_date=datetime.now(),
        )
        assert data.test_name == "HbA1c"
        assert data.interpretation is None

    def test_lab_interpretation_enum(self, sample_patient):
        """Test LabInterpretation enum values."""
        data = LabResultCreate(
            patient_id=sample_patient.id,
            test_name="Test",
            value="100",
            result_date=datetime.now(),
            interpretation=LabInterpretation.CRITICAL,
        )
        assert data.interpretation == LabInterpretation.CRITICAL


class TestFamilyHistorySchema:
    """Tests for FamilyHistory Pydantic schemas."""

    def test_family_history_create_validation(self, sample_patient):
        """Test FamilyHistoryCreate validation."""
        data = FamilyHistoryCreate(
            patient_id=sample_patient.id,
            relation=FamilyRelationship.SIBLING,
            condition_name="Heart Disease",
        )
        assert data.relation == FamilyRelationship.SIBLING
        assert data.onset_age is None


class TestSocialHistorySchema:
    """Tests for SocialHistory Pydantic schemas."""

    def test_social_history_create_validation(self, sample_patient):
        """Test SocialHistoryCreate validation."""
        data = SocialHistoryCreate(
            patient_id=sample_patient.id,
            category=SocialHistoryCategory.ALCOHOL,
            status=SocialHistoryStatus.OCCASIONAL,
            description="Social drinker",
        )
        assert data.category == SocialHistoryCategory.ALCOHOL
        assert data.status == SocialHistoryStatus.OCCASIONAL
