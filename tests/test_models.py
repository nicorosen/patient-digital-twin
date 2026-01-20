"""
Unit tests for database models.

Tests:
- Patient model properties (full_name, age)
- Clinical model to_document() methods
- Model relationships
"""

from datetime import date
import pytest

from src.models.patient import Patient
from src.models.clinical import Allergy, Condition, Medication


# =============================================================================
# PATIENT MODEL TESTS
# =============================================================================


class TestPatientModel:
    """Tests for the Patient model."""

    def test_full_name(self, sample_patient):
        """Test full_name property returns correct format."""
        assert sample_patient.full_name == "Test Patient"

    def test_full_name_with_different_names(self, db_session):
        """Test full_name with various name combinations."""
        patient = Patient(
            first_name="Maria",
            last_name="Garcia",
            date_of_birth=date(1990, 1, 1),
            gender="female",
        )
        db_session.add(patient)
        db_session.flush()
        assert patient.full_name == "Maria Garcia"

    def test_age_calculation(self, db_session):
        """Test age is calculated correctly."""
        today = date.today()
        # Create a patient born exactly 34 years ago today
        birth_date = date(today.year - 34, today.month, today.day)
        patient = Patient(
            first_name="Test",
            last_name="User",
            date_of_birth=birth_date,
            gender="male",
        )
        db_session.add(patient)
        db_session.flush()
        assert patient.age == 34

    def test_age_before_birthday(self, db_session):
        """Test age is correct before birthday."""
        today = date.today()
        # Create a patient whose birthday is tomorrow
        # They should be (years - 1) old
        if today.month == 12 and today.day == 31:
            # Special case: if today is Dec 31, birthday is Jan 1 next year
            birth_date = date(today.year - 33, 1, 1)
        else:
            # Calculate tomorrow's date
            from datetime import timedelta
            tomorrow = today + timedelta(days=1)
            birth_date = date(today.year - 34, tomorrow.month, tomorrow.day)

        patient = Patient(
            first_name="Test",
            last_name="User",
            date_of_birth=birth_date,
            gender="male",
        )
        db_session.add(patient)
        db_session.flush()
        # Birthday hasn't happened yet this year
        assert patient.age == 33

    def test_patient_repr(self, sample_patient):
        """Test patient string representation."""
        repr_str = repr(sample_patient)
        assert "Patient" in repr_str
        assert "Test Patient" in repr_str

    def test_patient_relationships_empty(self, sample_patient):
        """Test patient relationships are empty by default."""
        assert sample_patient.conditions == []
        assert sample_patient.medications == []
        assert sample_patient.allergies == []


# =============================================================================
# CONDITION MODEL TESTS
# =============================================================================


class TestConditionModel:
    """Tests for the Condition model."""

    def test_to_document_basic(self, sample_condition):
        """Test basic condition document generation."""
        doc = sample_condition.to_document()
        assert "Type 2 Diabetes Mellitus" in doc
        assert "active" in doc

    def test_to_document_with_onset(self, sample_condition):
        """Test document includes onset date."""
        doc = sample_condition.to_document()
        assert "January 2020" in doc

    def test_to_document_with_severity(self, sample_condition):
        """Test document includes severity."""
        doc = sample_condition.to_document()
        assert "moderate" in doc

    def test_to_document_with_notes(self, sample_condition):
        """Test document includes notes."""
        doc = sample_condition.to_document()
        assert "Well-controlled" in doc

    def test_to_document_minimal(self, db_session, sample_patient):
        """Test document with minimal fields."""
        condition = Condition(
            patient_id=sample_patient.id,
            display_name="Headache",
            clinical_status="active",
        )
        db_session.add(condition)
        db_session.flush()
        doc = condition.to_document()
        assert "Headache" in doc
        assert "active" in doc

    def test_condition_repr(self, sample_condition):
        """Test condition string representation."""
        repr_str = repr(sample_condition)
        assert "Condition" in repr_str
        assert "Type 2 Diabetes" in repr_str
        assert "active" in repr_str


# =============================================================================
# MEDICATION MODEL TESTS
# =============================================================================


class TestMedicationModel:
    """Tests for the Medication model."""

    def test_to_document_basic(self, sample_medication):
        """Test basic medication document generation."""
        doc = sample_medication.to_document()
        assert "Metformin" in doc
        assert "500mg" in doc

    def test_to_document_with_frequency(self, sample_medication):
        """Test document includes frequency."""
        doc = sample_medication.to_document()
        assert "twice daily" in doc

    def test_to_document_with_route(self, sample_medication):
        """Test document includes route."""
        doc = sample_medication.to_document()
        assert "oral" in doc

    def test_to_document_with_reason(self, sample_medication):
        """Test document includes reason."""
        doc = sample_medication.to_document()
        assert "Diabetes management" in doc

    def test_to_document_inactive_status(self, db_session, sample_patient):
        """Test document shows non-active status."""
        medication = Medication(
            patient_id=sample_patient.id,
            display_name="Aspirin",
            status="discontinued",
        )
        db_session.add(medication)
        db_session.flush()
        doc = medication.to_document()
        assert "discontinued" in doc

    def test_to_document_minimal(self, db_session, sample_patient):
        """Test document with minimal fields."""
        medication = Medication(
            patient_id=sample_patient.id,
            display_name="Ibuprofen",
            status="active",
        )
        db_session.add(medication)
        db_session.flush()
        doc = medication.to_document()
        assert "Ibuprofen" in doc
        # Active status should not be mentioned
        assert "active" not in doc.lower() or "status" not in doc.lower()

    def test_medication_repr(self, sample_medication):
        """Test medication string representation."""
        repr_str = repr(sample_medication)
        assert "Medication" in repr_str
        assert "Metformin" in repr_str
        assert "500mg" in repr_str


# =============================================================================
# ALLERGY MODEL TESTS
# =============================================================================


class TestAllergyModel:
    """Tests for the Allergy model."""

    def test_to_document_basic(self, sample_allergy):
        """Test basic allergy document generation."""
        doc = sample_allergy.to_document()
        assert "Penicillin" in doc

    def test_to_document_with_category(self, sample_allergy):
        """Test document includes category."""
        doc = sample_allergy.to_document()
        assert "medication" in doc.lower()

    def test_to_document_with_criticality(self, sample_allergy):
        """Test document includes criticality."""
        doc = sample_allergy.to_document()
        assert "high" in doc

    def test_to_document_with_reaction(self, sample_allergy):
        """Test document includes reaction."""
        doc = sample_allergy.to_document()
        assert "Anaphylaxis" in doc

    def test_to_document_food_allergy(self, db_session, sample_patient):
        """Test food allergy document."""
        allergy = Allergy(
            patient_id=sample_patient.id,
            substance="Shellfish",
            category="food",
            criticality="low",
            reaction="Hives",
        )
        db_session.add(allergy)
        db_session.flush()
        doc = allergy.to_document()
        assert "Shellfish" in doc
        assert "food" in doc

    def test_to_document_minimal(self, db_session, sample_patient):
        """Test document with minimal fields."""
        allergy = Allergy(
            patient_id=sample_patient.id,
            substance="Dust",
            category="environment",
        )
        db_session.add(allergy)
        db_session.flush()
        doc = allergy.to_document()
        assert "Dust" in doc

    def test_allergy_repr(self, sample_allergy):
        """Test allergy string representation."""
        repr_str = repr(sample_allergy)
        assert "Allergy" in repr_str
        assert "Penicillin" in repr_str
        assert "high" in repr_str


# =============================================================================
# RELATIONSHIP TESTS
# =============================================================================


class TestModelRelationships:
    """Tests for model relationships."""

    def test_patient_conditions_relationship(
        self, db_session, patient_with_clinical_data
    ):
        """Test patient has access to conditions."""
        patient = patient_with_clinical_data
        assert len(patient.conditions) == 1
        assert patient.conditions[0].display_name == "Type 2 Diabetes Mellitus"

    def test_patient_medications_relationship(
        self, db_session, patient_with_clinical_data
    ):
        """Test patient has access to medications."""
        patient = patient_with_clinical_data
        assert len(patient.medications) == 1
        assert patient.medications[0].display_name == "Metformin"

    def test_patient_allergies_relationship(
        self, db_session, patient_with_clinical_data
    ):
        """Test patient has access to allergies."""
        patient = patient_with_clinical_data
        assert len(patient.allergies) == 1
        assert patient.allergies[0].substance == "Penicillin"

    def test_condition_patient_relationship(self, db_session, sample_condition):
        """Test condition has access to patient."""
        assert sample_condition.patient is not None
        assert sample_condition.patient.first_name == "Test"

    def test_medication_patient_relationship(self, db_session, sample_medication):
        """Test medication has access to patient."""
        assert sample_medication.patient is not None
        assert sample_medication.patient.first_name == "Test"

    def test_allergy_patient_relationship(self, db_session, sample_allergy):
        """Test allergy has access to patient."""
        assert sample_allergy.patient is not None
        assert sample_allergy.patient.first_name == "Test"
