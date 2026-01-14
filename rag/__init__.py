"""
RAG (Retrieval-Augmented Generation) package.

This package provides document retrieval and vectorstore functionality.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from .rag import RAGKnowledgeBase
    _RAG_AVAILABLE = True
except ImportError:
    _RAG_AVAILABLE = False
    logger.debug("RAG module dependencies not available")


def create_vectorstore(vectorstore_path="rag/vectorstore"):
    """
    Create or load a vectorstore for RAG functionality.
    
    Args:
        vectorstore_path: Path to the vectorstore directory
        
    Returns:
        FAISS vectorstore instance or None if not available
    """
    if not _RAG_AVAILABLE:
        return None
    
    try:
        rag_kb = RAGKnowledgeBase(vectorstore_path=vectorstore_path)
        
        # Try to load existing vectorstore
        try:
            rag_kb.load_vectorstore()
            return rag_kb.vectorstore
        except (FileNotFoundError, RuntimeError) as e:
            # Vectorstore doesn't exist or is corrupted
            logger.debug(f"Vectorstore not available: {e}")
            return None
            
    except Exception as e:
        # Unexpected error during RAG initialization
        logger.warning(f"RAG initialization failed: {e}")
        return None


__all__ = ["RAGKnowledgeBase", "create_vectorstore"] if _RAG_AVAILABLE else ["create_vectorstore"]
