"""
Unit tests for database repositories.

Tests CRUD operations for:
- PatientRepository
- ConditionRepository
- MedicationRepository
- AllergyRepository
- ConversationRepository
- AuditLogRepository
"""

from datetime import date
from uuid import uuid4

import pytest

from src.database.repositories import (
    AllergyRepository,
    AuditLogRepository,
    ConditionRepository,
    ConversationRepository,
    MedicationRepository,
    PatientRepository,
)
from src.schemas import (
    AllergyCategory,
    AllergyCriticality,
    AllergyCreate,
    AllergyUpdate,
    ClinicalStatus,
    ConditionCreate,
    ConditionUpdate,
    Gender,
    MedicationCreate,
    MedicationStatus,
    MedicationUpdate,
    PatientCreate,
    PatientUpdate,
    Severity,
)


# =============================================================================
# PATIENT REPOSITORY TESTS
# =============================================================================


class TestPatientRepository:
    """Tests for PatientRepository."""

    def test_create_patient(self, db_session):
        """Test creating a new patient."""
        patient_data = PatientCreate(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 3, 20),
            gender=Gender.MALE,
        )
        patient = PatientRepository.create(db_session, patient_data)

        assert patient.id is not None
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
        assert patient.gender == "male"

    def test_get_by_id(self, db_session, sample_patient):
        """Test retrieving a patient by ID."""
        found = PatientRepository.get_by_id(db_session, sample_patient.id)
        assert found is not None
        assert found.id == sample_patient.id
        assert found.first_name == sample_patient.first_name

    def test_get_by_id_not_found(self, db_session):
        """Test retrieving a non-existent patient."""
        found = PatientRepository.get_by_id(db_session, uuid4())
        assert found is None

    def test_get_all(self, db_session):
        """Test retrieving all patients."""
        # Create multiple patients
        for i in range(3):
            data = PatientCreate(
                first_name=f"Patient{i}",
                last_name="Test",
                date_of_birth=date(1990, 1, 1),
                gender=Gender.FEMALE,
            )
            PatientRepository.create(db_session, data)

        patients = PatientRepository.get_all(db_session)
        assert len(patients) == 3

    def test_get_all_ordered_by_name(self, db_session):
        """Test patients are ordered by last name, first name."""
        names = [("Zoe", "Alpha"), ("Alice", "Beta"), ("Bob", "Alpha")]
        for first, last in names:
            data = PatientCreate(
                first_name=first,
                last_name=last,
                date_of_birth=date(1990, 1, 1),
                gender=Gender.FEMALE,
            )
            PatientRepository.create(db_session, data)

        patients = PatientRepository.get_all(db_session)
        # Should be ordered: Alpha-Bob, Alpha-Zoe, Beta-Alice
        assert patients[0].last_name == "Alpha"
        assert patients[0].first_name == "Bob"

    def test_update_patient(self, db_session, sample_patient):
        """Test updating a patient."""
        update_data = PatientUpdate(first_name="Updated")
        updated = PatientRepository.update(
            db_session, sample_patient.id, update_data
        )

        assert updated is not None
        assert updated.first_name == "Updated"
        assert updated.last_name == sample_patient.last_name  # Unchanged

    def test_update_patient_gender(self, db_session, sample_patient):
        """Test updating patient gender."""
        update_data = PatientUpdate(gender=Gender.OTHER)
        updated = PatientRepository.update(
            db_session, sample_patient.id, update_data
        )

        assert updated.gender == "other"

    def test_update_patient_not_found(self, db_session):
        """Test updating a non-existent patient."""
        update_data = PatientUpdate(first_name="Updated")
        result = PatientRepository.update(db_session, uuid4(), update_data)
        assert result is None

    def test_delete_patient(self, db_session, sample_patient):
        """Test deleting a patient."""
        patient_id = sample_patient.id
        result = PatientRepository.delete(db_session, patient_id)
        assert result is True

        # Verify patient is deleted
        found = PatientRepository.get_by_id(db_session, patient_id)
        assert found is None

    def test_delete_patient_not_found(self, db_session):
        """Test deleting a non-existent patient."""
        result = PatientRepository.delete(db_session, uuid4())
        assert result is False

    def test_get_profile(self, db_session, patient_with_clinical_data):
        """Test getting complete patient profile."""
        profile = PatientRepository.get_profile(
            db_session, patient_with_clinical_data.id
        )

        assert profile is not None
        assert profile.patient.first_name == "Test"
        assert len(profile.conditions) == 1
        assert len(profile.medications) == 1
        assert len(profile.allergies) == 1

    def test_get_profile_not_found(self, db_session):
        """Test getting profile for non-existent patient."""
        profile = PatientRepository.get_profile(db_session, uuid4())
        assert profile is None


# =============================================================================
# CONDITION REPOSITORY TESTS
# =============================================================================


class TestConditionRepository:
    """Tests for ConditionRepository."""

    def test_create_condition(self, db_session, sample_patient):
        """Test creating a new condition."""
        condition_data = ConditionCreate(
            patient_id=sample_patient.id,
            display_name="Hypertension",
            code="I10",
            clinical_status=ClinicalStatus.ACTIVE,
            severity=Severity.MILD,
        )
        condition = ConditionRepository.create(db_session, condition_data)

        assert condition.id is not None
        assert condition.display_name == "Hypertension"
        assert condition.clinical_status == "active"

    def test_get_by_patient(self, db_session, sample_patient):
        """Test getting conditions for a patient."""
        # Create multiple conditions
        for name in ["Condition A", "Condition B"]:
            data = ConditionCreate(
                patient_id=sample_patient.id,
                display_name=name,
                clinical_status=ClinicalStatus.ACTIVE,
            )
            ConditionRepository.create(db_session, data)

        conditions = ConditionRepository.get_by_patient(
            db_session, sample_patient.id
        )
        assert len(conditions) == 2

    def test_get_by_patient_active_only(self, db_session, sample_patient):
        """Test filtering active conditions only."""
        # Create active and resolved conditions
        active_data = ConditionCreate(
            patient_id=sample_patient.id,
            display_name="Active Condition",
            clinical_status=ClinicalStatus.ACTIVE,
        )
        resolved_data = ConditionCreate(
            patient_id=sample_patient.id,
            display_name="Resolved Condition",
            clinical_status=ClinicalStatus.RESOLVED,
        )
        ConditionRepository.create(db_session, active_data)
        ConditionRepository.create(db_session, resolved_data)

        # Get all
        all_conditions = ConditionRepository.get_by_patient(
            db_session, sample_patient.id
        )
        assert len(all_conditions) == 2

        # Get active only
        active_conditions = ConditionRepository.get_by_patient(
            db_session, sample_patient.id, active_only=True
        )
        assert len(active_conditions) == 1
        assert active_conditions[0].display_name == "Active Condition"

    def test_update_condition(self, db_session, sample_condition):
        """Test updating a condition."""
        update_data = ConditionUpdate(
            clinical_status=ClinicalStatus.RESOLVED,
            notes="Now resolved",
        )
        updated = ConditionRepository.update(
            db_session, sample_condition.id, update_data
        )

        assert updated.clinical_status == "resolved"
        assert updated.notes == "Now resolved"

    def test_delete_condition(self, db_session, sample_condition):
        """Test deleting a condition."""
        condition_id = sample_condition.id
        result = ConditionRepository.delete(db_session, condition_id)
        assert result is True

        found = ConditionRepository.get_by_id(db_session, condition_id)
        assert found is None


# =============================================================================
# MEDICATION REPOSITORY TESTS
# =============================================================================


class TestMedicationRepository:
    """Tests for MedicationRepository."""

    def test_create_medication(self, db_session, sample_patient):
        """Test creating a new medication."""
        medication_data = MedicationCreate(
            patient_id=sample_patient.id,
            display_name="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            status=MedicationStatus.ACTIVE,
        )
        medication = MedicationRepository.create(db_session, medication_data)

        assert medication.id is not None
        assert medication.display_name == "Lisinopril"
        assert medication.status == "active"

    def test_get_by_patient_active_only(self, db_session, sample_patient):
        """Test filtering active medications only."""
        # Create active and discontinued medications
        active_data = MedicationCreate(
            patient_id=sample_patient.id,
            display_name="Active Med",
            status=MedicationStatus.ACTIVE,
        )
        discontinued_data = MedicationCreate(
            patient_id=sample_patient.id,
            display_name="Old Med",
            status=MedicationStatus.DISCONTINUED,
        )
        MedicationRepository.create(db_session, active_data)
        MedicationRepository.create(db_session, discontinued_data)

        active_meds = MedicationRepository.get_by_patient(
            db_session, sample_patient.id, active_only=True
        )
        assert len(active_meds) == 1
        assert active_meds[0].display_name == "Active Med"

    def test_update_medication_status(self, db_session, sample_medication):
        """Test updating medication status."""
        update_data = MedicationUpdate(status=MedicationStatus.DISCONTINUED)
        updated = MedicationRepository.update(
            db_session, sample_medication.id, update_data
        )

        assert updated.status == "discontinued"

    def test_delete_medication(self, db_session, sample_medication):
        """Test deleting a medication."""
        medication_id = sample_medication.id
        result = MedicationRepository.delete(db_session, medication_id)
        assert result is True


# =============================================================================
# ALLERGY REPOSITORY TESTS
# =============================================================================


class TestAllergyRepository:
    """Tests for AllergyRepository."""

    def test_create_allergy(self, db_session, sample_patient):
        """Test creating a new allergy."""
        allergy_data = AllergyCreate(
            patient_id=sample_patient.id,
            substance="Shellfish",
            category=AllergyCategory.FOOD,
            criticality=AllergyCriticality.LOW,
            reaction="Hives",
        )
        allergy = AllergyRepository.create(db_session, allergy_data)

        assert allergy.id is not None
        assert allergy.substance == "Shellfish"
        assert allergy.category == "food"

    def test_get_by_patient(self, db_session, sample_patient):
        """Test getting allergies for a patient."""
        for substance in ["Peanuts", "Latex"]:
            data = AllergyCreate(
                patient_id=sample_patient.id,
                substance=substance,
                category=AllergyCategory.FOOD,
            )
            AllergyRepository.create(db_session, data)

        allergies = AllergyRepository.get_by_patient(db_session, sample_patient.id)
        assert len(allergies) == 2

    def test_update_allergy(self, db_session, sample_allergy):
        """Test updating an allergy."""
        update_data = AllergyUpdate(
            criticality=AllergyCriticality.LOW,
            reaction="Mild skin rash",
        )
        updated = AllergyRepository.update(
            db_session, sample_allergy.id, update_data
        )

        assert updated.criticality == "low"
        assert updated.reaction == "Mild skin rash"

    def test_delete_allergy(self, db_session, sample_allergy):
        """Test deleting an allergy."""
        allergy_id = sample_allergy.id
        result = AllergyRepository.delete(db_session, allergy_id)
        assert result is True


# =============================================================================
# CONVERSATION REPOSITORY TESTS
# =============================================================================


class TestConversationRepository:
    """Tests for ConversationRepository."""

    def test_add_message(self, db_session, sample_patient):
        """Test adding a conversation message."""
        message = ConversationRepository.add_message(
            db_session,
            patient_id=sample_patient.id,
            role="user",
            content="Hello, I have a question.",
        )

        assert message.id is not None
        assert message.role == "user"
        assert message.content == "Hello, I have a question."

    def test_add_message_with_metadata(self, db_session, sample_patient):
        """Test adding a message with metadata."""
        metadata = {"tool_calls": ["search_patient_data"]}
        message = ConversationRepository.add_message(
            db_session,
            patient_id=sample_patient.id,
            role="assistant",
            content="Let me check that.",
            metadata=metadata,
        )

        assert message.metadata == metadata

    def test_get_messages(self, db_session, sample_patient):
        """Test getting conversation messages."""
        # Add multiple messages
        for i in range(3):
            ConversationRepository.add_message(
                db_session,
                patient_id=sample_patient.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )

        messages = ConversationRepository.get_messages(
            db_session, sample_patient.id
        )
        assert len(messages) == 3

    def test_get_messages_with_limit(self, db_session, sample_patient):
        """Test message limit."""
        for i in range(10):
            ConversationRepository.add_message(
                db_session,
                patient_id=sample_patient.id,
                role="user",
                content=f"Message {i}",
            )

        messages = ConversationRepository.get_messages(
            db_session, sample_patient.id, limit=5
        )
        assert len(messages) == 5

    def test_clear_messages(self, db_session, sample_patient):
        """Test clearing conversation messages."""
        # Add messages
        for i in range(5):
            ConversationRepository.add_message(
                db_session,
                patient_id=sample_patient.id,
                role="user",
                content=f"Message {i}",
            )

        # Clear messages
        count = ConversationRepository.clear_messages(
            db_session, sample_patient.id
        )
        assert count == 5

        # Verify cleared
        messages = ConversationRepository.get_messages(
            db_session, sample_patient.id
        )
        assert len(messages) == 0


# =============================================================================
# AUDIT LOG REPOSITORY TESTS
# =============================================================================


class TestAuditLogRepository:
    """Tests for AuditLogRepository."""

    def test_create_audit_log(self, db_session, sample_patient):
        """Test creating an audit log entry."""
        log = AuditLogRepository.create(
            db_session,
            patient_id=sample_patient.id,
            specialist_type="primary_care",
            clinical_question="Patient has chest pain, what should I check?",
            data_shared={"age": 35, "conditions": ["Hypertension"]},
            specialist_response={"recommendation": "Check ECG"},
        )

        assert log.id is not None
        assert log.specialist_type == "primary_care"
        assert "chest pain" in log.clinical_question

    def test_get_by_patient(self, db_session, sample_patient):
        """Test getting audit logs for a patient."""
        # Create multiple logs
        for i in range(3):
            AuditLogRepository.create(
                db_session,
                patient_id=sample_patient.id,
                specialist_type="primary_care",
                clinical_question=f"Question {i}",
                data_shared={},
                specialist_response={},
            )

        logs = AuditLogRepository.get_by_patient(db_session, sample_patient.id)
        assert len(logs) == 3

    def test_get_by_patient_with_limit(self, db_session, sample_patient):
        """Test audit log limit."""
        for i in range(10):
            AuditLogRepository.create(
                db_session,
                patient_id=sample_patient.id,
                specialist_type="primary_care",
                clinical_question=f"Question {i}",
                data_shared={},
                specialist_response={},
            )

        logs = AuditLogRepository.get_by_patient(
            db_session, sample_patient.id, limit=5
        )
        assert len(logs) == 5
