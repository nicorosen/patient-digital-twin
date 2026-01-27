"""
Unit tests for consultation tool with translation integration.

Tests:
- consult_primary_care tool calls translate_specialist_response
- Audit log captures original clinical response
- Error handling for translation failures
"""

from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Import modules before using them in patch decorators
import src.agents.tools.consultation


# =============================================================================
# CONSULTATION TOOL TESTS
# =============================================================================


class TestConsultPrimaryCareTool:
    """Tests for the consult_primary_care tool with translation."""

    @patch("src.agents.tools.consultation.translate_specialist_response")
    @patch("src.agents.tools.consultation.get_specialist")
    @patch("src.agents.tools.consultation.AuditLogRepository")
    @patch("src.agents.tools.consultation.get_db")
    @patch("src.agents.tools.consultation.create_deidentified_context")
    def test_calls_translate_specialist_response(
        self,
        mock_create_context,
        mock_get_db,
        mock_audit_repo,
        mock_get_specialist,
        mock_translate,
    ):
        """Test that consult_primary_care calls translate_specialist_response."""
        from src.agents.tools.consultation import consult_primary_care
        from src.agents.specialists.base import SpecialistResponse, Recommendation

        # Setup mocks
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_context = MagicMock()
        mock_context.age = 45
        mock_context.gender = "male"
        mock_context.conditions = ["Hypertension"]
        mock_context.medications = ["Lisinopril 10mg"]
        mock_context.allergies = []
        mock_create_context.return_value = mock_context

        mock_response = SpecialistResponse(
            assessment="Clinical assessment of the patient's condition.",
            recommendations=[
                Recommendation(
                    action="Monitor blood pressure",
                    priority="routine",
                    rationale="Standard care",
                )
            ],
            red_flags=[],
            guidelines_referenced=["JNC8"],
            confidence="high",
            limitations="Based on provided information only.",
        )

        mock_specialist = MagicMock()
        mock_specialist.consult.return_value = mock_response
        mock_get_specialist.return_value = mock_specialist

        mock_translate.return_value = "Patient-friendly translated response"

        patient_id = str(uuid4())
        result = consult_primary_care.invoke({
            "patient_id": patient_id,
            "clinical_question": "How should I manage my blood pressure?",
        })

        # Verify translate was called with the specialist response
        mock_translate.assert_called_once_with(mock_response)
        assert result == "Patient-friendly translated response"

    @patch("src.agents.tools.consultation.translate_specialist_response")
    @patch("src.agents.tools.consultation.get_specialist")
    @patch("src.agents.tools.consultation.AuditLogRepository")
    @patch("src.agents.tools.consultation.get_db")
    @patch("src.agents.tools.consultation.create_deidentified_context")
    def test_audit_log_captures_original_response(
        self,
        mock_create_context,
        mock_get_db,
        mock_audit_repo,
        mock_get_specialist,
        mock_translate,
    ):
        """Test that audit log captures the original clinical response, not translated."""
        from src.agents.tools.consultation import consult_primary_care
        from src.agents.specialists.base import SpecialistResponse, Recommendation

        # Setup mocks
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_context = MagicMock()
        mock_context.age = 45
        mock_context.gender = "male"
        mock_context.conditions = ["Diabetes"]
        mock_context.medications = ["Metformin 500mg"]
        mock_context.allergies = ["Penicillin"]
        mock_create_context.return_value = mock_context

        mock_response = SpecialistResponse(
            assessment="Patient shows signs of uncontrolled diabetes.",
            recommendations=[
                Recommendation(
                    action="Increase Metformin dosage",
                    priority="routine",
                    rationale="HbA1c above target",
                )
            ],
            red_flags=["Check for diabetic ketoacidosis symptoms"],
            guidelines_referenced=["ADA 2024"],
            confidence="moderate",
            limitations="No recent lab values provided.",
        )

        mock_specialist = MagicMock()
        mock_specialist.consult.return_value = mock_response
        mock_get_specialist.return_value = mock_specialist

        mock_translate.return_value = "Simple patient-friendly response"

        patient_id = str(uuid4())
        consult_primary_care.invoke({
            "patient_id": patient_id,
            "clinical_question": "Is my diabetes under control?",
        })

        # Verify audit log was called with original clinical response
        mock_audit_repo.create.assert_called_once()
        call_kwargs = mock_audit_repo.create.call_args[1]

        # Check that the specialist_response in audit contains original clinical data
        assert call_kwargs["specialist_response"]["assessment"] == "Patient shows signs of uncontrolled diabetes."
        assert call_kwargs["specialist_response"]["confidence"] == "moderate"
        assert "diabetic ketoacidosis" in call_kwargs["specialist_response"]["red_flags"][0]

    def test_invalid_patient_id(self):
        """Test error handling for invalid patient ID."""
        from src.agents.tools.consultation import consult_primary_care

        result = consult_primary_care.invoke({
            "patient_id": "not-a-uuid",
            "clinical_question": "Any question",
        })

        assert "Error" in result
        assert "Invalid patient ID" in result

    @patch("src.agents.tools.consultation.create_deidentified_context")
    def test_patient_not_found(self, mock_create_context):
        """Test error handling when patient is not found."""
        from src.agents.tools.consultation import consult_primary_care

        mock_create_context.side_effect = ValueError("Patient not found: test-id")

        patient_id = str(uuid4())
        result = consult_primary_care.invoke({
            "patient_id": patient_id,
            "clinical_question": "Any question",
        })

        assert "Error" in result
        assert "Patient not found" in result


# =============================================================================
# DE-IDENTIFICATION TESTS
# =============================================================================


class TestCreateDeidentifiedContext:
    """Tests for the de-identification function."""

    @patch("src.agents.tools.consultation.get_db")
    @patch("src.agents.tools.consultation.PatientRepository")
    @patch("src.agents.tools.consultation.ConditionRepository")
    @patch("src.agents.tools.consultation.MedicationRepository")
    @patch("src.agents.tools.consultation.AllergyRepository")
    def test_creates_deidentified_context(
        self,
        mock_allergy_repo,
        mock_med_repo,
        mock_cond_repo,
        mock_patient_repo,
        mock_get_db,
    ):
        """Test de-identified context creation."""
        from src.agents.tools.consultation import create_deidentified_context

        # Setup mocks
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_patient = MagicMock()
        mock_patient.date_of_birth = date(1980, 5, 15)
        mock_patient.gender = "female"
        mock_patient_repo.get_by_id.return_value = mock_patient

        mock_condition = MagicMock()
        mock_condition.display_name = "Type 2 Diabetes"
        mock_cond_repo.get_by_patient.return_value = [mock_condition]

        mock_medication = MagicMock()
        mock_medication.display_name = "Metformin"
        mock_medication.dosage = "500mg"
        mock_medication.frequency = "twice daily"
        mock_med_repo.get_by_patient.return_value = [mock_medication]

        mock_allergy = MagicMock()
        mock_allergy.substance = "Penicillin"
        mock_allergy.criticality = "high"
        mock_allergy_repo.get_by_patient.return_value = [mock_allergy]

        patient_id = uuid4()
        context = create_deidentified_context(patient_id)

        # Verify de-identified context contains expected data
        assert context.gender == "female"
        assert context.conditions == ["Type 2 Diabetes"]
        assert "Metformin 500mg (twice daily)" in context.medications
        assert "Penicillin [high]" in context.allergies
        # Age should be calculated, not DOB exposed
        assert isinstance(context.age, int)

    @patch("src.agents.tools.consultation.get_db")
    @patch("src.agents.tools.consultation.PatientRepository")
    def test_patient_not_found_raises_error(self, mock_patient_repo, mock_get_db):
        """Test that missing patient raises ValueError."""
        from src.agents.tools.consultation import create_deidentified_context

        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_patient_repo.get_by_id.return_value = None

        patient_id = uuid4()
        with pytest.raises(ValueError, match="Patient not found"):
            create_deidentified_context(patient_id)
