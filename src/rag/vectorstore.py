"""
Chroma vector store for patient clinical data.

Provides semantic search over patient conditions, medications, and allergies.
Each document is tagged with patient_id for filtered retrieval.
"""

import os
from typing import List, Optional
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import get_settings
from src.logging_config import get_logger
from src.rag.embeddings import get_embedding_service

logger = get_logger("rag.vectorstore")


class PatientVectorStore:
    """Vector store for patient clinical data using Chroma."""

    COLLECTION_NAME = "patient_clinical_data"

    def __init__(self):
        """Initialize the vector store."""
        settings = get_settings()
        logger.info(f"Initializing PatientVectorStore: persist_dir={settings.chroma_persist_dir}")

        # Ensure persist directory exists
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)

        # Initialize Chroma client with persistence
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self._embedding_service = get_embedding_service()

        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Patient clinical data for RAG"},
        )
        doc_count = self._collection.count()
        logger.info(f"VectorStore ready: collection={self.COLLECTION_NAME}, documents={doc_count}")

    def add_document(
        self,
        doc_id: str,
        content: str,
        patient_id: UUID,
        doc_type: str,
        item_id: Optional[UUID] = None,
    ) -> None:
        """
        Add a document to the vector store.

        Args:
            doc_id: Unique identifier for the document.
            content: Text content to embed and store.
            patient_id: UUID of the patient this document belongs to.
            doc_type: Type of document (condition, medication, allergy).
            item_id: Optional ID of the source item (condition_id, medication_id, etc.).
        """
        embedding = self._embedding_service.embed_text(content)

        metadata = {
            "patient_id": str(patient_id),
            "doc_type": doc_type,
        }
        if item_id:
            metadata["item_id"] = str(item_id)

        self._collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata],
        )

    def add_documents(
        self,
        doc_ids: List[str],
        contents: List[str],
        patient_ids: List[UUID],
        doc_types: List[str],
        item_ids: Optional[List[Optional[UUID]]] = None,
    ) -> None:
        """
        Add multiple documents to the vector store.

        Args:
            doc_ids: List of unique identifiers.
            contents: List of text contents.
            patient_ids: List of patient UUIDs.
            doc_types: List of document types.
            item_ids: Optional list of source item IDs.
        """
        if not contents:
            return

        embeddings = self._embedding_service.embed_texts(contents)

        metadatas = []
        for i, (patient_id, doc_type) in enumerate(zip(patient_ids, doc_types)):
            metadata = {
                "patient_id": str(patient_id),
                "doc_type": doc_type,
            }
            if item_ids and item_ids[i]:
                metadata["item_id"] = str(item_ids[i])
            metadatas.append(metadata)

        self._collection.upsert(
            ids=doc_ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )

    def search(
        self,
        query: str,
        patient_id: UUID,
        n_results: int = 5,
        doc_type: Optional[str] = None,
    ) -> List[dict]:
        """
        Search for documents matching the query for a specific patient.

        Args:
            query: Natural language search query.
            patient_id: UUID of the patient to search within.
            n_results: Maximum number of results to return.
            doc_type: Optional filter by document type.

        Returns:
            List of matching documents with metadata and distances.
        """
        logger.debug(f"VectorStore.search: query='{query}'")
        logger.debug(f"  patient_id={patient_id}, n_results={n_results}, doc_type={doc_type}")

        query_embedding = self._embedding_service.embed_text(query)
        logger.debug(f"  Query embedding: dim={len(query_embedding)}, first_5={query_embedding[:5]}")

        # Build where clause for filtering
        where_clause = {"patient_id": str(patient_id)}
        if doc_type:
            where_clause = {
                "$and": [
                    {"patient_id": str(patient_id)},
                    {"doc_type": doc_type},
                ]
            }
        logger.debug(f"  Where clause: {where_clause}")

        # Check how many docs exist for this patient
        patient_docs = self._collection.get(
            where={"patient_id": str(patient_id)},
            include=["metadatas"],
        )
        num_docs = len(patient_docs['ids'])
        if num_docs == 0:
            logger.warning(f"  NO DOCUMENTS INDEXED for patient {patient_id}!")
            logger.warning(f"  Run 'python run.py --index' to index patient data for RAG")
        else:
            logger.info(f"  Total docs for patient: {num_docs}")
            doc_types_in_store = {}
            for meta in patient_docs['metadatas']:
                dt = meta.get('doc_type', 'unknown')
                doc_types_in_store[dt] = doc_types_in_store.get(dt, 0) + 1
            logger.info(f"  Docs by type: {doc_types_in_store}")

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        documents = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else None
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                documents.append(
                    {
                        "content": doc,
                        "metadata": metadata,
                        "distance": distance,
                    }
                )
                dist_str = f"{distance:.4f}" if distance is not None else "N/A"
                logger.debug(f"  Result [{i}]: distance={dist_str}, "
                           f"type={metadata.get('doc_type')}, content_len={len(doc)}")
        else:
            logger.warning(f"  No results returned from Chroma query")

        return documents

    def delete_patient_documents(self, patient_id: UUID) -> None:
        """
        Delete all documents for a patient.

        Args:
            patient_id: UUID of the patient.
        """
        self._collection.delete(where={"patient_id": str(patient_id)})

    def delete_document(self, doc_id: str) -> None:
        """
        Delete a specific document.

        Args:
            doc_id: ID of the document to delete.
        """
        self._collection.delete(ids=[doc_id])

    def get_document_count(self, patient_id: Optional[UUID] = None) -> int:
        """
        Get the number of documents in the store.

        Args:
            patient_id: Optional patient filter.

        Returns:
            Number of documents.
        """
        if patient_id:
            results = self._collection.get(
                where={"patient_id": str(patient_id)},
                include=[],
            )
            return len(results["ids"])
        return self._collection.count()


# Singleton instance
_vectorstore: Optional[PatientVectorStore] = None


def get_vectorstore() -> PatientVectorStore:
    """Get the singleton vector store instance."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = PatientVectorStore()
    return _vectorstore
