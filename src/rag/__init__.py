"""
RAG (Retrieval-Augmented Generation) system.

Provides semantic search over patient health data:
- Embedding generation using sentence-transformers
- Chroma vector store for similarity search
- Patient-scoped retrieval
"""

from src.rag.embeddings import EmbeddingService, get_embedding_service
from src.rag.retriever import PatientRetriever, get_retriever
from src.rag.vectorstore import PatientVectorStore, get_vectorstore

__all__ = [
    # Embeddings
    "EmbeddingService",
    "get_embedding_service",
    # Vector Store
    "PatientVectorStore",
    "get_vectorstore",
    # Retriever
    "PatientRetriever",
    "get_retriever",
]
