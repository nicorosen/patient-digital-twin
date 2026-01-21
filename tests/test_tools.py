"""
Unit tests for agent tools.

Tests:
- _parse_date utility function
- get_patient_profile tool
- search_patient_data tool
- add_condition tool
- add_medication tool
- add_allergy tool
"""

from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# =============================================================================
# DATE PARSING TESTS
# =============================================================================


class TestParseDateFunction:
    """Tests for the _parse_date utility function."""

    def test_parse_iso_format(self):
        """Test parsing ISO date format (YYYY-MM-DD)."""
        from src.agents.tools.patient_data import _parse_date

        result = _parse_date("2024-03-15")
        assert result == date(2024, 3, 15)

    def test_parse_us_format(self):
        """Test parsing US date format (MM/DD/YYYY)."""
        from src.agents.tools.patient_data import _parse_date

        result = _parse_date("03/15/2024")
        assert result == date(2024, 3, 15)

    def test_parse_european_format(self):
        """Test parsing European date format (DD/MM/YYYY)."""
        from src.agents.tools.patient_data import _parse_date

        # Note: This will fail for ambiguous dates, testing unambiguous case
        result = _parse_date("25/12/2024")
        assert result == date(2024, 12, 25)

    def test_parse_full_month_format(self):
        """Test parsing full month name format (Month DD, YYYY)."""
        from src.agents.tools.patient_data import _parse_date

        result = _parse_date("March 15, 2024")
        assert result == date(2024, 3, 15)

    def test_parse_abbreviated_month_format(self):
        """Test parsing abbreviated month format (Mon DD, YYYY)."""
        from src.agents.tools.patient_data import _parse_date

        result = _parse_date("Mar 15, 2024")
        assert result == date(2024, 3, 15)

    def test_parse_none(self):
        """Test parsing None returns None."""
        from src.agents.tools.patient_data import _parse_date

        result = _parse_date(None)
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        from src.agents.tools.patient_data import _parse_date

        result = _parse_date("")
        assert result is None

    def test_parse_invalid_format(self):
        """Test parsing invalid format returns None."""
        from src.agents.tools.patient_data import _parse_date

        result = _parse_date("not a date")
        assert result is None

    def test_parse_partial_date(self):
        """Test parsing partial date returns None."""
        from src.agents.tools.patient_data import _parse_date

        result = _parse_date("2024-03")
        assert result is None


# =============================================================================
# GET_PATIENT_PROFILE TOOL TESTS
# =============================================================================


class TestGetPatientProfileTool:
    """Tests for the get_patient_profile tool."""

    @patch("src.agents.tools.patient_data.get_db")
    @patch("src.agents.tools.patient_data.PatientRepository")
    def test_get_profile_success(self, mock_repo, mock_get_db):
        """Test successful profile retrieval."""
        from src.agents.tools.patient_data import get_patient_profile

        # Setup mock
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_patient = MagicMock()
        mock_patient.first_name = "Test"
        mock_patient.last_name = "Patient"
        mock_patient.age = 35
        mock_patient.gender.value = "female"
        mock_patient.date_of_birth = date(1990, 1, 1)

        mock_profile = MagicMock()
        mock_profile.patient = mock_patient
        mock_profile.conditions = []
        mock_profile.medications = []
        mock_profile.allergies = []
        mock_profile.vital_signs = []
        mock_profile.lab_results = []
        mock_profile.family_history = []
        mock_profile.social_history = []

        mock_repo.get_profile.return_value = mock_profile

        patient_id = str(uuid4())
        result = get_patient_profile.invoke({"patient_id": patient_id})

        assert "Test Patient" in result
        assert "35 years old" in result
        assert "Female" in result

    @patch("src.agents.tools.patient_data.get_db")
    @patch("src.agents.tools.patient_data.PatientRepository")
    def test_get_profile_not_found(self, mock_repo, mock_get_db):
        """Test profile retrieval for non-existent patient."""
        from src.agents.tools.patient_data import get_patient_profile

        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_repo.get_profile.return_value = None

        patient_id = str(uuid4())
        result = get_patient_profile.invoke({"patient_id": patient_id})

        assert "Error" in result
        assert "not found" in result

    def test_get_profile_invalid_uuid(self):
        """Test profile retrieval with invalid UUID."""
        from src.agents.tools.patient_data import get_patient_profile

        result = get_patient_profile.invoke({"patient_id": "not-a-uuid"})

        assert "Error" in result
        assert "Invalid patient ID" in result


# =============================================================================
# SEARCH_PATIENT_DATA TOOL TESTS
# =============================================================================


class TestSearchPatientDataTool:
    """Tests for the search_patient_data tool."""

    @patch("src.agents.tools.patient_data.get_retriever")
    def test_search_success(self, mock_get_retriever):
        """Test successful search."""
        from src.agents.tools.patient_data import search_patient_data

        mock_retriever = MagicMock()
        mock_retriever.get_context.return_value = (
            "Relevant clinical information:\n"
            "1. [CONDITION] Patient has Type 2 Diabetes"
        )
        mock_get_retriever.return_value = mock_retriever

        patient_id = str(uuid4())
        result = search_patient_data.invoke({
            "patient_id": patient_id,
            "query": "diabetes"
        })

        assert "clinical information" in result
        assert "Diabetes" in result
        mock_retriever.get_context.assert_called_once()

    def test_search_invalid_uuid(self):
        """Test search with invalid UUID."""
        from src.agents.tools.patient_data import search_patient_data

        result = search_patient_data.invoke({
            "patient_id": "invalid",
            "query": "diabetes"
        })

        assert "Error" in result
        assert "Invalid patient ID" in result


# =============================================================================
# ADD_CONDITION TOOL TESTS
# =============================================================================


class TestAddConditionTool:
    """Tests for the add_condition tool."""

    @patch("src.agents.tools.patient_data.get_retriever")
    @patch("src.agents.tools.patient_data.get_db")
    @patch("src.agents.tools.patient_data.PatientRepository")
    @patch("src.agents.tools.patient_data.ConditionRepository")
    def test_add_condition_success(
        self, mock_cond_repo, mock_patient_repo, mock_get_db, mock_get_retriever
    ):
        """Test successfully adding a condition."""
        from src.agents.tools.patient_data import add_condition

        # Setup mocks
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_patient = MagicMock()
        mock_patient_repo.get_by_id.return_value = mock_patient

        mock_condition = MagicMock()
        mock_condition.id = uuid4()
        mock_condition.to_document.return_value = "Patient has Hypertension"
        mock_cond_repo.create.return_value = mock_condition

        mock_retriever = MagicMock()
        mock_get_retriever.return_value = mock_retriever

        patient_id = str(uuid4())
        result = add_condition.invoke({
            "patient_id": patient_id,
            "display_name": "Hypertension",
            "clinical_status": "active",
            "severity": "mild",
        })

        assert "Successfully added" in result
        assert "Hypertension" in result
        mock_cond_repo.create.assert_called_once()
        mock_retriever.add_condition_document.assert_called_once()

    @patch("src.agents.tools.patient_data.get_db")
    @patch("src.agents.tools.patient_data.PatientRepository")
    def test_add_condition_patient_not_found(self, mock_patient_repo, mock_get_db):
        """Test adding condition for non-existent patient."""
        from src.agents.tools.patient_data import add_condition

        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_patient_repo.get_by_id.return_value = None

        patient_id = str(uuid4())
        result = add_condition.invoke({
            "patient_id": patient_id,
            "display_name": "Hypertension",
        })

        assert "Error" in result
        assert "not found" in result

    def test_add_condition_invalid_status(self):
        """Test adding condition with invalid clinical status."""
        from src.agents.tools.patient_data import add_condition

        patient_id = str(uuid4())
        result = add_condition.invoke({
            "patient_id": patient_id,
            "display_name": "Hypertension",
            "clinical_status": "invalid_status",
        })

        assert "Error" in result
        assert "Invalid clinical status" in result

    def test_add_condition_invalid_severity(self):
        """Test adding condition with invalid severity."""
        from src.agents.tools.patient_data import add_condition

        patient_id = str(uuid4())
        result = add_condition.invoke({
            "patient_id": patient_id,
            "display_name": "Hypertension",
            "clinical_status": "active",
            "severity": "invalid_severity",
        })

        assert "Error" in result
        assert "Invalid severity" in result


# =============================================================================
# ADD_MEDICATION TOOL TESTS
# =============================================================================


class TestAddMedicationTool:
    """Tests for the add_medication tool."""

    @patch("src.agents.tools.patient_data.get_retriever")
    @patch("src.agents.tools.patient_data.get_db")
    @patch("src.agents.tools.patient_data.PatientRepository")
    @patch("src.agents.tools.patient_data.MedicationRepository")
    def test_add_medication_success(
        self, mock_med_repo, mock_patient_repo, mock_get_db, mock_get_retriever
    ):
        """Test successfully adding a medication."""
        from src.agents.tools.patient_data import add_medication

        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_patient = MagicMock()
        mock_patient_repo.get_by_id.return_value = mock_patient

        mock_medication = MagicMock()
        mock_medication.id = uuid4()
        mock_medication.to_document.return_value = "Patient takes Metformin 500mg"
        mock_med_repo.create.return_value = mock_medication

        mock_retriever = MagicMock()
        mock_get_retriever.return_value = mock_retriever

        patient_id = str(uuid4())
        result = add_medication.invoke({
            "patient_id": patient_id,
            "display_name": "Metformin",
            "dosage": "500mg",
            "frequency": "twice daily",
        })

        assert "Successfully added" in result
        assert "Metformin" in result
        mock_retriever.add_medication_document.assert_called_once()

    def test_add_medication_invalid_status(self):
        """Test adding medication with invalid status."""
        from src.agents.tools.patient_data import add_medication

        patient_id = str(uuid4())
        result = add_medication.invoke({
            "patient_id": patient_id,
            "display_name": "Metformin",
            "status": "invalid_status",
        })

        assert "Error" in result
        assert "Invalid status" in result


# =============================================================================
# ADD_ALLERGY TOOL TESTS
# =============================================================================


class TestAddAllergyTool:
    """Tests for the add_allergy tool."""

    @patch("src.agents.tools.patient_data.get_retriever")
    @patch("src.agents.tools.patient_data.get_db")
    @patch("src.agents.tools.patient_data.PatientRepository")
    @patch("src.agents.tools.patient_data.AllergyRepository")
    def test_add_allergy_success(
        self, mock_allergy_repo, mock_patient_repo, mock_get_db, mock_get_retriever
    ):
        """Test successfully adding an allergy."""
        from src.agents.tools.patient_data import add_allergy

        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_patient = MagicMock()
        mock_patient_repo.get_by_id.return_value = mock_patient

        mock_allergy = MagicMock()
        mock_allergy.id = uuid4()
        mock_allergy.to_document.return_value = "Patient is allergic to Penicillin"
        mock_allergy_repo.create.return_value = mock_allergy

        mock_retriever = MagicMock()
        mock_get_retriever.return_value = mock_retriever

        patient_id = str(uuid4())
        result = add_allergy.invoke({
            "patient_id": patient_id,
            "substance": "Penicillin",
            "category": "medication",
            "criticality": "high",
            "reaction": "Anaphylaxis",
        })

        assert "Successfully added" in result
        assert "Penicillin" in result
        assert "high" in result
        mock_retriever.add_allergy_document.assert_called_once()

    def test_add_allergy_invalid_category(self):
        """Test adding allergy with invalid category."""
        from src.agents.tools.patient_data import add_allergy

        patient_id = str(uuid4())
        result = add_allergy.invoke({
            "patient_id": patient_id,
            "substance": "Peanuts",
            "category": "invalid_category",
        })

        assert "Error" in result
        assert "Invalid category" in result

    def test_add_allergy_invalid_criticality(self):
        """Test adding allergy with invalid criticality."""
        from src.agents.tools.patient_data import add_allergy

        patient_id = str(uuid4())
        result = add_allergy.invoke({
            "patient_id": patient_id,
            "substance": "Peanuts",
            "category": "food",
            "criticality": "invalid",
        })

        assert "Error" in result
        assert "Invalid criticality" in result

    @patch("src.agents.tools.patient_data.get_retriever")
    @patch("src.agents.tools.patient_data.get_db")
    @patch("src.agents.tools.patient_data.PatientRepository")
    @patch("src.agents.tools.patient_data.AllergyRepository")
    def test_add_food_allergy(
        self, mock_allergy_repo, mock_patient_repo, mock_get_db, mock_get_retriever
    ):
        """Test adding a food allergy."""
        from src.agents.tools.patient_data import add_allergy

        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_patient = MagicMock()
        mock_patient_repo.get_by_id.return_value = mock_patient

        mock_allergy = MagicMock()
        mock_allergy.id = uuid4()
        mock_allergy.to_document.return_value = "Patient is allergic to Shellfish"
        mock_allergy_repo.create.return_value = mock_allergy

        mock_retriever = MagicMock()
        mock_get_retriever.return_value = mock_retriever

        patient_id = str(uuid4())
        result = add_allergy.invoke({
            "patient_id": patient_id,
            "substance": "Shellfish",
            "category": "food",
            "criticality": "low",
        })

        assert "Successfully added" in result
        assert "Shellfish" in result
        assert "food" in result
