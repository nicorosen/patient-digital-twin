"""
RAG retriever for patient clinical data.

Provides high-level interface for:
- Indexing patient data from PostgreSQL to Chroma
- Semantic search over patient records
- Context building for agent queries
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.database import get_db
from src.database.repositories import (
    AllergyRepository,
    ConditionRepository,
    MedicationRepository,
    PatientRepository,
)
from src.logging_config import get_logger
from src.rag.vectorstore import get_vectorstore

logger = get_logger("rag.retriever")


class PatientRetriever:
    """Retriever for patient clinical data using RAG."""

    def __init__(self):
        """Initialize the retriever."""
        self._vectorstore = get_vectorstore()

    def index_patient(self, db: Session, patient_id: UUID) -> int:
        """
        Index all clinical data for a patient into the vector store.

        Args:
            db: Database session.
            patient_id: UUID of the patient to index.

        Returns:
            Number of documents indexed.
        """
        logger.info(f"Indexing patient: {patient_id}")
        doc_ids = []
        contents = []
        patient_ids = []
        doc_types = []
        item_ids = []

        # Index conditions
        conditions = ConditionRepository.get_by_patient(db, patient_id)
        for condition in conditions:
            doc_ids.append(f"condition_{condition.id}")
            contents.append(condition.to_document())
            patient_ids.append(patient_id)
            doc_types.append("condition")
            item_ids.append(condition.id)

        # Index medications
        medications = MedicationRepository.get_by_patient(db, patient_id)
        for medication in medications:
            doc_ids.append(f"medication_{medication.id}")
            contents.append(medication.to_document())
            patient_ids.append(patient_id)
            doc_types.append("medication")
            item_ids.append(medication.id)

        # Index allergies
        allergies = AllergyRepository.get_by_patient(db, patient_id)
        for allergy in allergies:
            doc_ids.append(f"allergy_{allergy.id}")
            contents.append(allergy.to_document())
            patient_ids.append(patient_id)
            doc_types.append("allergy")
            item_ids.append(allergy.id)

        # Batch add to vector store
        if contents:
            logger.info(f"  Indexing {len(contents)} documents: "
                       f"{len(conditions)} conditions, {len(medications)} medications, {len(allergies)} allergies")
            for i, (doc_id, content) in enumerate(zip(doc_ids, contents)):
                logger.debug(f"    [{i}] {doc_id}: {content[:80]}...")
            self._vectorstore.add_documents(
                doc_ids=doc_ids,
                contents=contents,
                patient_ids=patient_ids,
                doc_types=doc_types,
                item_ids=item_ids,
            )
            logger.info(f"  Successfully indexed {len(contents)} documents for patient {patient_id}")
        else:
            logger.warning(f"  No documents to index for patient {patient_id}")

        return len(contents)

    def index_all_patients(self) -> int:
        """
        Index all patients in the database.

        Returns:
            Total number of documents indexed.
        """
        logger.info("Starting to index all patients...")
        total = 0
        with get_db() as db:
            patients = PatientRepository.get_all(db)
            logger.info(f"Found {len(patients)} patients to index")
            for patient in patients:
                count = self.index_patient(db, patient.id)
                total += count
        logger.info(f"Indexing complete: {total} total documents indexed")
        return total

    def search(
        self,
        query: str,
        patient_id: UUID,
        n_results: int = 5,
        doc_type: Optional[str] = None,
    ) -> List[dict]:
        """
        Search patient clinical data using natural language.

        Args:
            query: Natural language search query.
            patient_id: UUID of the patient to search within.
            n_results: Maximum number of results.
            doc_type: Optional filter (condition, medication, allergy).

        Returns:
            List of matching documents with content and metadata.
        """
        logger.info(f"RAG search: query='{query}', patient_id={patient_id}, n_results={n_results}")
        results = self._vectorstore.search(
            query=query,
            patient_id=patient_id,
            n_results=n_results,
            doc_type=doc_type,
        )
        logger.info(f"RAG search returned {len(results)} results")
        for i, r in enumerate(results):
            dist = r.get('distance', 'N/A')
            doc_type_r = r.get('metadata', {}).get('doc_type', 'unknown')
            content_preview = r.get('content', '')[:100]
            dist_str = f"{dist:.4f}" if isinstance(dist, float) else str(dist)
            logger.debug(f"  [{i}] type={doc_type_r}, distance={dist_str}")
            logger.debug(f"      content: {content_preview}...")
        return results

    def get_context(
        self,
        query: str,
        patient_id: UUID,
        n_results: int = 5,
    ) -> str:
        """
        Get formatted context string for agent prompts.

        Args:
            query: Natural language search query.
            patient_id: UUID of the patient.
            n_results: Maximum number of results.

        Returns:
            Formatted string with relevant clinical context.
        """
        logger.debug(f"get_context called: query='{query}', patient_id={patient_id}")
        results = self.search(query, patient_id, n_results)

        if not results:
            logger.warning(f"No results found for query: '{query}'")
            return "No relevant clinical information found."

        context_parts = ["Relevant clinical information:"]
        for i, result in enumerate(results, 1):
            doc_type = result["metadata"].get("doc_type", "unknown")
            content = result["content"]
            context_parts.append(f"\n{i}. [{doc_type.upper()}] {content}")

        context = "\n".join(context_parts)
        logger.debug(f"Context built: {len(context)} chars, {len(results)} documents")
        return context

    def add_condition_document(
        self,
        patient_id: UUID,
        condition_id: UUID,
        content: str,
    ) -> None:
        """
        Add a new condition document to the index.

        Args:
            patient_id: UUID of the patient.
            condition_id: UUID of the condition.
            content: Document content.
        """
        self._vectorstore.add_document(
            doc_id=f"condition_{condition_id}",
            content=content,
            patient_id=patient_id,
            doc_type="condition",
            item_id=condition_id,
        )

    def add_medication_document(
        self,
        patient_id: UUID,
        medication_id: UUID,
        content: str,
    ) -> None:
        """
        Add a new medication document to the index.

        Args:
            patient_id: UUID of the patient.
            medication_id: UUID of the medication.
            content: Document content.
        """
        self._vectorstore.add_document(
            doc_id=f"medication_{medication_id}",
            content=content,
            patient_id=patient_id,
            doc_type="medication",
            item_id=medication_id,
        )

    def add_allergy_document(
        self,
        patient_id: UUID,
        allergy_id: UUID,
        content: str,
    ) -> None:
        """
        Add a new allergy document to the index.

        Args:
            patient_id: UUID of the patient.
            allergy_id: UUID of the allergy.
            content: Document content.
        """
        self._vectorstore.add_document(
            doc_id=f"allergy_{allergy_id}",
            content=content,
            patient_id=patient_id,
            doc_type="allergy",
            item_id=allergy_id,
        )

    def remove_document(self, doc_type: str, item_id: UUID) -> None:
        """
        Remove a document from the index.

        Args:
            doc_type: Type of document (condition, medication, allergy).
            item_id: UUID of the item.
        """
        self._vectorstore.delete_document(f"{doc_type}_{item_id}")

    def clear_patient_index(self, patient_id: UUID) -> None:
        """
        Clear all indexed documents for a patient.

        Args:
            patient_id: UUID of the patient.
        """
        self._vectorstore.delete_patient_documents(patient_id)


# Singleton instance
_retriever: Optional[PatientRetriever] = None


def get_retriever() -> PatientRetriever:
    """Get the singleton retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = PatientRetriever()
    return _retriever
