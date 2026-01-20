"""
Shared pytest fixtures for Patient Digital Twin tests.

Provides:
- In-memory SQLite database session for isolation
- Sample patient data fixtures
- Mock fixtures for external services (vectorstore, embeddings, LLM)
"""

import os
import sys
from datetime import date
from typing import Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.base import Base
from src.models.patient import Patient
from src.models.clinical import Allergy, Condition, Medication


# =============================================================================
# DATABASE FIXTURES
# =============================================================================


@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =============================================================================
# PATIENT DATA FIXTURES
# =============================================================================


@pytest.fixture
def sample_patient_data() -> dict:
    """Sample patient data for creating test patients."""
    return {
        "first_name": "Test",
        "last_name": "Patient",
        "date_of_birth": date(1990, 5, 15),
        "gender": "female",
    }


@pytest.fixture
def sample_patient(db_session, sample_patient_data) -> Patient:
    """Create a sample patient in the database."""
    patient = Patient(**sample_patient_data)
    db_session.add(patient)
    db_session.flush()
    return patient


@pytest.fixture
def sample_condition_data(sample_patient) -> dict:
    """Sample condition data."""
    return {
        "patient_id": sample_patient.id,
        "code": "E11.9",
        "display_name": "Type 2 Diabetes Mellitus",
        "clinical_status": "active",
        "onset_date": date(2020, 1, 15),
        "severity": "moderate",
        "notes": "Well-controlled with medication",
    }


@pytest.fixture
def sample_condition(db_session, sample_condition_data) -> Condition:
    """Create a sample condition in the database."""
    condition = Condition(**sample_condition_data)
    db_session.add(condition)
    db_session.flush()
    return condition


@pytest.fixture
def sample_medication_data(sample_patient) -> dict:
    """Sample medication data."""
    return {
        "patient_id": sample_patient.id,
        "code": "860975",
        "display_name": "Metformin",
        "dosage": "500mg",
        "frequency": "twice daily",
        "route": "oral",
        "status": "active",
        "start_date": date(2020, 2, 1),
        "reason": "Diabetes management",
    }


@pytest.fixture
def sample_medication(db_session, sample_medication_data) -> Medication:
    """Create a sample medication in the database."""
    medication = Medication(**sample_medication_data)
    db_session.add(medication)
    db_session.flush()
    return medication


@pytest.fixture
def sample_allergy_data(sample_patient) -> dict:
    """Sample allergy data."""
    return {
        "patient_id": sample_patient.id,
        "code": "70618",
        "substance": "Penicillin",
        "category": "medication",
        "criticality": "high",
        "reaction": "Anaphylaxis - throat swelling",
        "onset_date": date(2010, 7, 20),
    }


@pytest.fixture
def sample_allergy(db_session, sample_allergy_data) -> Allergy:
    """Create a sample allergy in the database."""
    allergy = Allergy(**sample_allergy_data)
    db_session.add(allergy)
    db_session.flush()
    return allergy


@pytest.fixture
def patient_with_clinical_data(
    db_session, sample_patient, sample_condition, sample_medication, sample_allergy
) -> Patient:
    """Create a patient with full clinical data."""
    db_session.flush()
    db_session.refresh(sample_patient)
    return sample_patient


# =============================================================================
# MOCK FIXTURES
# =============================================================================


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service that returns consistent test vectors."""
    mock = MagicMock()
    # Return a consistent 384-dimensional vector (matching all-MiniLM-L6-v2)
    test_embedding = [0.1] * 384
    mock.embed_text.return_value = test_embedding
    mock.embed_texts.return_value = [test_embedding]
    mock.embedding_dimension = 384
    return mock


@pytest.fixture
def mock_vectorstore(mock_embedding_service):
    """Mock vector store for testing without Chroma."""
    mock = MagicMock()
    mock._embedding_service = mock_embedding_service

    # Store documents in memory for testing
    mock._documents = {}

    def add_document(doc_id, content, patient_id, doc_type, item_id=None):
        mock._documents[doc_id] = {
            "content": content,
            "patient_id": str(patient_id),
            "doc_type": doc_type,
            "item_id": str(item_id) if item_id else None,
        }

    def search(query, patient_id, n_results=5, doc_type=None):
        results = []
        for doc_id, doc in mock._documents.items():
            if doc["patient_id"] == str(patient_id):
                if doc_type is None or doc["doc_type"] == doc_type:
                    results.append({
                        "content": doc["content"],
                        "metadata": {
                            "patient_id": doc["patient_id"],
                            "doc_type": doc["doc_type"],
                        },
                        "distance": 0.5,  # Mock distance
                    })
        return results[:n_results]

    def get_document_count(patient_id=None):
        if patient_id:
            return sum(
                1 for doc in mock._documents.values()
                if doc["patient_id"] == str(patient_id)
            )
        return len(mock._documents)

    mock.add_document.side_effect = add_document
    mock.search.side_effect = search
    mock.get_document_count.side_effect = get_document_count

    return mock


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    mock = MagicMock()
    mock.llm_provider = "anthropic"
    mock.model_name = "claude-sonnet-4-20250514"
    mock.max_tokens = 4096
    mock.anthropic_api_key = "test-key"
    mock.openai_api_key = None
    mock.google_api_key = None
    mock.embedding_model = "all-MiniLM-L6-v2"
    mock.chroma_persist_dir = "./test_data/embeddings"
    mock.database_url = "sqlite:///:memory:"
    return mock


# =============================================================================
# UTILITY FIXTURES
# =============================================================================


@pytest.fixture
def random_uuid():
    """Generate a random UUID for testing."""
    return uuid4()
