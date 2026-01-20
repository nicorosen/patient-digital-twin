"""
Unit tests for RAG components.

Tests:
- EmbeddingService
- PatientVectorStore (with mocked Chroma)
- PatientRetriever
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Import modules before using them in patch decorators
import src.rag.embeddings
import src.rag.vectorstore
import src.rag.retriever


# =============================================================================
# EMBEDDING SERVICE TESTS
# =============================================================================


class TestEmbeddingService:
    """Tests for the EmbeddingService."""

    @patch("src.rag.embeddings.SentenceTransformer")
    @patch("src.rag.embeddings.get_settings")
    def test_singleton_pattern(self, mock_settings, mock_transformer):
        """Test EmbeddingService uses singleton pattern."""
        mock_settings.return_value.embedding_model = "test-model"
        mock_transformer.return_value.get_sentence_embedding_dimension.return_value = 384

        # Reset singleton state
        from src.rag.embeddings import EmbeddingService
        EmbeddingService._instance = None
        EmbeddingService._model = None

        service1 = EmbeddingService()
        service2 = EmbeddingService()

        assert service1 is service2

    @patch("src.rag.embeddings.SentenceTransformer")
    @patch("src.rag.embeddings.get_settings")
    def test_embed_text(self, mock_settings, mock_transformer):
        """Test embedding a single text."""
        mock_settings.return_value.embedding_model = "test-model"

        # Mock the model
        mock_model = MagicMock()
        import numpy as np
        mock_model.encode.return_value = np.array([0.1] * 384)
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_transformer.return_value = mock_model

        # Reset singleton
        from src.rag.embeddings import EmbeddingService
        EmbeddingService._instance = None
        EmbeddingService._model = None

        service = EmbeddingService()
        embedding = service.embed_text("Test text")

        assert len(embedding) == 384
        assert all(isinstance(v, float) for v in embedding)
        mock_model.encode.assert_called_once()

    @patch("src.rag.embeddings.SentenceTransformer")
    @patch("src.rag.embeddings.get_settings")
    def test_embed_texts_batch(self, mock_settings, mock_transformer):
        """Test embedding multiple texts."""
        mock_settings.return_value.embedding_model = "test-model"

        mock_model = MagicMock()
        import numpy as np
        mock_model.encode.return_value = np.array([[0.1] * 384, [0.2] * 384])
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_transformer.return_value = mock_model

        from src.rag.embeddings import EmbeddingService
        EmbeddingService._instance = None
        EmbeddingService._model = None

        service = EmbeddingService()
        embeddings = service.embed_texts(["Text 1", "Text 2"])

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 384

    @patch("src.rag.embeddings.SentenceTransformer")
    @patch("src.rag.embeddings.get_settings")
    def test_embedding_dimension(self, mock_settings, mock_transformer):
        """Test getting embedding dimension."""
        mock_settings.return_value.embedding_model = "test-model"

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_transformer.return_value = mock_model

        from src.rag.embeddings import EmbeddingService
        EmbeddingService._instance = None
        EmbeddingService._model = None

        service = EmbeddingService()
        assert service.embedding_dimension == 384


# =============================================================================
# VECTOR STORE TESTS
# =============================================================================


class TestPatientVectorStore:
    """Tests for PatientVectorStore."""

    @patch("src.rag.vectorstore.chromadb")
    @patch("src.rag.vectorstore.get_embedding_service")
    @patch("src.rag.vectorstore.get_settings")
    def test_add_document(self, mock_settings, mock_embedding, mock_chroma):
        """Test adding a document to the vector store."""
        # Setup mocks
        mock_settings.return_value.chroma_persist_dir = "./test_data"
        mock_embedding.return_value.embed_text.return_value = [0.1] * 384

        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 0

        # Reset singleton
        import src.rag.vectorstore as vs
        vs._vectorstore = None

        from src.rag.vectorstore import PatientVectorStore
        store = PatientVectorStore()

        patient_id = uuid4()
        store.add_document(
            doc_id="condition_123",
            content="Patient has diabetes",
            patient_id=patient_id,
            doc_type="condition",
            item_id=uuid4(),
        )

        mock_collection.upsert.assert_called_once()
        call_kwargs = mock_collection.upsert.call_args[1]
        assert call_kwargs["ids"] == ["condition_123"]
        assert call_kwargs["documents"] == ["Patient has diabetes"]

    @patch("src.rag.vectorstore.chromadb")
    @patch("src.rag.vectorstore.get_embedding_service")
    @patch("src.rag.vectorstore.get_settings")
    def test_add_documents_batch(self, mock_settings, mock_embedding, mock_chroma):
        """Test adding multiple documents."""
        mock_settings.return_value.chroma_persist_dir = "./test_data"
        mock_embedding.return_value.embed_texts.return_value = [[0.1] * 384, [0.2] * 384]

        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 0

        import src.rag.vectorstore as vs
        vs._vectorstore = None

        from src.rag.vectorstore import PatientVectorStore
        store = PatientVectorStore()

        patient_id = uuid4()
        store.add_documents(
            doc_ids=["doc1", "doc2"],
            contents=["Content 1", "Content 2"],
            patient_ids=[patient_id, patient_id],
            doc_types=["condition", "medication"],
        )

        mock_collection.upsert.assert_called_once()

    @patch("src.rag.vectorstore.chromadb")
    @patch("src.rag.vectorstore.get_embedding_service")
    @patch("src.rag.vectorstore.get_settings")
    def test_search(self, mock_settings, mock_embedding, mock_chroma):
        """Test searching for documents."""
        mock_settings.return_value.chroma_persist_dir = "./test_data"
        mock_embedding.return_value.embed_text.return_value = [0.1] * 384

        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 2

        patient_id = uuid4()
        # Mock get() for patient doc count check
        mock_collection.get.return_value = {
            "ids": ["doc1", "doc2"],
            "metadatas": [
                {"doc_type": "condition", "patient_id": str(patient_id)},
                {"doc_type": "medication", "patient_id": str(patient_id)},
            ],
        }

        # Mock query() for search results
        mock_collection.query.return_value = {
            "documents": [["Document content"]],
            "metadatas": [[{"doc_type": "condition", "patient_id": str(patient_id)}]],
            "distances": [[0.25]],
        }

        import src.rag.vectorstore as vs
        vs._vectorstore = None

        from src.rag.vectorstore import PatientVectorStore
        store = PatientVectorStore()

        results = store.search(
            query="diabetes medications",
            patient_id=patient_id,
            n_results=5,
        )

        assert len(results) == 1
        assert results[0]["content"] == "Document content"
        assert results[0]["distance"] == 0.25

    @patch("src.rag.vectorstore.chromadb")
    @patch("src.rag.vectorstore.get_embedding_service")
    @patch("src.rag.vectorstore.get_settings")
    def test_search_with_doc_type_filter(self, mock_settings, mock_embedding, mock_chroma):
        """Test search with document type filter."""
        mock_settings.return_value.chroma_persist_dir = "./test_data"
        mock_embedding.return_value.embed_text.return_value = [0.1] * 384

        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 1

        patient_id = uuid4()
        mock_collection.get.return_value = {
            "ids": ["doc1"],
            "metadatas": [{"doc_type": "medication"}],
        }
        mock_collection.query.return_value = {
            "documents": [["Metformin 500mg"]],
            "metadatas": [[{"doc_type": "medication"}]],
            "distances": [[0.3]],
        }

        import src.rag.vectorstore as vs
        vs._vectorstore = None

        from src.rag.vectorstore import PatientVectorStore
        store = PatientVectorStore()

        results = store.search(
            query="diabetes",
            patient_id=patient_id,
            doc_type="medication",
        )

        # Verify the where clause includes doc_type filter
        call_kwargs = mock_collection.query.call_args[1]
        assert "$and" in call_kwargs["where"]

    @patch("src.rag.vectorstore.chromadb")
    @patch("src.rag.vectorstore.get_embedding_service")
    @patch("src.rag.vectorstore.get_settings")
    def test_delete_patient_documents(self, mock_settings, mock_embedding, mock_chroma):
        """Test deleting all documents for a patient."""
        mock_settings.return_value.chroma_persist_dir = "./test_data"

        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 0

        import src.rag.vectorstore as vs
        vs._vectorstore = None

        from src.rag.vectorstore import PatientVectorStore
        store = PatientVectorStore()

        patient_id = uuid4()
        store.delete_patient_documents(patient_id)

        mock_collection.delete.assert_called_once()
        call_kwargs = mock_collection.delete.call_args[1]
        assert call_kwargs["where"]["patient_id"] == str(patient_id)

    @patch("src.rag.vectorstore.chromadb")
    @patch("src.rag.vectorstore.get_embedding_service")
    @patch("src.rag.vectorstore.get_settings")
    def test_get_document_count(self, mock_settings, mock_embedding, mock_chroma):
        """Test getting document count."""
        mock_settings.return_value.chroma_persist_dir = "./test_data"

        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 10

        import src.rag.vectorstore as vs
        vs._vectorstore = None

        from src.rag.vectorstore import PatientVectorStore
        store = PatientVectorStore()

        # Total count
        count = store.get_document_count()
        assert count == 10

    @patch("src.rag.vectorstore.chromadb")
    @patch("src.rag.vectorstore.get_embedding_service")
    @patch("src.rag.vectorstore.get_settings")
    def test_get_document_count_by_patient(self, mock_settings, mock_embedding, mock_chroma):
        """Test getting document count for a specific patient."""
        mock_settings.return_value.chroma_persist_dir = "./test_data"

        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 10

        patient_id = uuid4()
        mock_collection.get.return_value = {"ids": ["doc1", "doc2", "doc3"]}

        import src.rag.vectorstore as vs
        vs._vectorstore = None

        from src.rag.vectorstore import PatientVectorStore
        store = PatientVectorStore()

        count = store.get_document_count(patient_id)
        assert count == 3


# =============================================================================
# RETRIEVER TESTS
# =============================================================================


class TestPatientRetriever:
    """Tests for PatientRetriever."""

    @patch("src.rag.retriever.get_vectorstore")
    def test_index_patient(self, mock_get_vectorstore, db_session, patient_with_clinical_data):
        """Test indexing a patient's clinical data."""
        mock_vectorstore = MagicMock()
        mock_get_vectorstore.return_value = mock_vectorstore

        # Reset singleton
        import src.rag.retriever as ret
        ret._retriever = None

        from src.rag.retriever import PatientRetriever
        retriever = PatientRetriever()

        count = retriever.index_patient(db_session, patient_with_clinical_data.id)

        # Should index 1 condition + 1 medication + 1 allergy = 3 documents
        assert count == 3
        mock_vectorstore.add_documents.assert_called_once()

    @patch("src.rag.retriever.get_vectorstore")
    def test_index_patient_empty(self, mock_get_vectorstore, db_session, sample_patient):
        """Test indexing a patient with no clinical data."""
        mock_vectorstore = MagicMock()
        mock_get_vectorstore.return_value = mock_vectorstore

        import src.rag.retriever as ret
        ret._retriever = None

        from src.rag.retriever import PatientRetriever
        retriever = PatientRetriever()

        count = retriever.index_patient(db_session, sample_patient.id)

        assert count == 0
        mock_vectorstore.add_documents.assert_not_called()

    @patch("src.rag.retriever.get_vectorstore")
    def test_search(self, mock_get_vectorstore):
        """Test searching patient data."""
        mock_vectorstore = MagicMock()
        mock_vectorstore.search.return_value = [
            {
                "content": "Patient has diabetes",
                "metadata": {"doc_type": "condition"},
                "distance": 0.2,
            }
        ]
        mock_get_vectorstore.return_value = mock_vectorstore

        import src.rag.retriever as ret
        ret._retriever = None

        from src.rag.retriever import PatientRetriever
        retriever = PatientRetriever()

        patient_id = uuid4()
        results = retriever.search("diabetes", patient_id)

        assert len(results) == 1
        assert results[0]["content"] == "Patient has diabetes"
        mock_vectorstore.search.assert_called_once_with(
            query="diabetes",
            patient_id=patient_id,
            n_results=5,
            doc_type=None,
        )

    @patch("src.rag.retriever.get_vectorstore")
    def test_get_context(self, mock_get_vectorstore):
        """Test building context string from search results."""
        mock_vectorstore = MagicMock()
        mock_vectorstore.search.return_value = [
            {
                "content": "Patient has diabetes",
                "metadata": {"doc_type": "condition"},
                "distance": 0.2,
            },
            {
                "content": "Patient takes Metformin 500mg",
                "metadata": {"doc_type": "medication"},
                "distance": 0.3,
            },
        ]
        mock_get_vectorstore.return_value = mock_vectorstore

        import src.rag.retriever as ret
        ret._retriever = None

        from src.rag.retriever import PatientRetriever
        retriever = PatientRetriever()

        patient_id = uuid4()
        context = retriever.get_context("diabetes treatment", patient_id)

        assert "Relevant clinical information" in context
        assert "CONDITION" in context
        assert "MEDICATION" in context
        assert "diabetes" in context
        assert "Metformin" in context

    @patch("src.rag.retriever.get_vectorstore")
    def test_get_context_no_results(self, mock_get_vectorstore):
        """Test context building with no results."""
        mock_vectorstore = MagicMock()
        mock_vectorstore.search.return_value = []
        mock_get_vectorstore.return_value = mock_vectorstore

        import src.rag.retriever as ret
        ret._retriever = None

        from src.rag.retriever import PatientRetriever
        retriever = PatientRetriever()

        patient_id = uuid4()
        context = retriever.get_context("nonexistent condition", patient_id)

        assert "No relevant clinical information found" in context

    @patch("src.rag.retriever.get_vectorstore")
    def test_add_condition_document(self, mock_get_vectorstore):
        """Test adding a single condition document."""
        mock_vectorstore = MagicMock()
        mock_get_vectorstore.return_value = mock_vectorstore

        import src.rag.retriever as ret
        ret._retriever = None

        from src.rag.retriever import PatientRetriever
        retriever = PatientRetriever()

        patient_id = uuid4()
        condition_id = uuid4()
        retriever.add_condition_document(
            patient_id=patient_id,
            condition_id=condition_id,
            content="New condition added",
        )

        mock_vectorstore.add_document.assert_called_once()
        call_kwargs = mock_vectorstore.add_document.call_args[1]
        assert call_kwargs["doc_type"] == "condition"
        assert f"condition_{condition_id}" == call_kwargs["doc_id"]

    @patch("src.rag.retriever.get_vectorstore")
    def test_remove_document(self, mock_get_vectorstore):
        """Test removing a document."""
        mock_vectorstore = MagicMock()
        mock_get_vectorstore.return_value = mock_vectorstore

        import src.rag.retriever as ret
        ret._retriever = None

        from src.rag.retriever import PatientRetriever
        retriever = PatientRetriever()

        item_id = uuid4()
        retriever.remove_document("medication", item_id)

        mock_vectorstore.delete_document.assert_called_once_with(
            f"medication_{item_id}"
        )

    @patch("src.rag.retriever.get_vectorstore")
    def test_clear_patient_index(self, mock_get_vectorstore):
        """Test clearing all documents for a patient."""
        mock_vectorstore = MagicMock()
        mock_get_vectorstore.return_value = mock_vectorstore

        import src.rag.retriever as ret
        ret._retriever = None

        from src.rag.retriever import PatientRetriever
        retriever = PatientRetriever()

        patient_id = uuid4()
        retriever.clear_patient_index(patient_id)

        mock_vectorstore.delete_patient_documents.assert_called_once_with(patient_id)
