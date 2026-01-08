"""
RAG (Retrieval-Augmented Generation) package.

This package provides document retrieval and vectorstore functionality.
"""

from .rag import RAGKnowledgeBase


def create_vectorstore(vectorstore_path="rag/vectorstore"):
    """
    Create or load a vectorstore for RAG functionality.
    
    Args:
        vectorstore_path: Path to the vectorstore directory
        
    Returns:
        FAISS vectorstore instance or None if not available
    """
    try:
        rag_kb = RAGKnowledgeBase(vectorstore_path=vectorstore_path)
        
        # Try to load existing vectorstore
        try:
            rag_kb.load_vectorstore()
            return rag_kb.vectorstore
        except Exception:
            # If loading fails, return None (will be handled by RAG service)
            return None
            
    except Exception as e:
        # Return None if RAG initialization fails
        return None


__all__ = ["RAGKnowledgeBase", "create_vectorstore"]

