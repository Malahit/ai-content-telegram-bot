"""
# Copilot TASK:
# 1. Добавь автоматическую перезагрузку FAISS-индекса при изменении файлов в ./knowledge/
# 2. Используй библиотеку watchdog (Observer + FileSystemEventHandler)
# 3. Реализуй в методе __init__:
#    - Запуск observer в отдельном потоке
#    - Обработчик on_modified/on_created для файлов .txt/.md/.pdf
# 4. При изменении файлов:
#    - Пересоздай self.vectorstore через self._initialize_vectorstore()
#    - Залогируй событие: "🔄 RAG-база перезагружена из-за изменений в {file_path}"
# 5. Сохраняй асинхронность:
#    - Используй asyncio.to_thread для blocking-операций watchdog
#    - Добавь метод async def stop_observer(self) для graceful shutdown
# 6. Добавь в импорты:
#    import threading
#    from watchdog.observers import Observer
#    from watchdog.events import FileSystemEventHandler
RAG (Retrieval-Augmented Generation) service module.

This module handles RAG functionality with proper error handling
and fallback mechanisms when RAG is not available.
"""

from typing import Optional, List, Tuple
from logger_config import logger
from config import config


# Try to import RAG module
try:
    from rag import create_vectorstore
    RAG_ENABLED = True
except ImportError:
    RAG_ENABLED = False
    logger.warning("RAG module not available - dependencies not installed")
    create_vectorstore = None


class RAGService:
    """
    Service for RAG (Retrieval-Augmented Generation) operations.
    
    Provides document retrieval and context building for enhanced
    content generation.
    """
    
    def __init__(self):
        """Initialize RAG service."""
        self.enabled = RAG_ENABLED
        self.vectorstore = None
        
        if self.enabled:
            try:
                self.vectorstore = create_vectorstore()
                logger.info("RAG service initialized successfully")
            except Exception as e:
                self.enabled = False
                logger.error(f"Failed to initialize RAG vectorstore: {e}")
        else:
            logger.info("RAG service disabled - module not available")
    
    def is_enabled(self) -> bool:
        """
        Check if RAG is enabled.
        
        Returns:
            bool: True if RAG is available
        """
        return self.enabled and self.vectorstore is not None
    
    def get_context(self, query: str, k: Optional[int] = None) -> Tuple[str, str]:
        """
        Get RAG context for a query.
        
        Args:
            query: Search query
            k: Number of documents to retrieve (default from config)
            
        Returns:
            Tuple[str, str]: RAG context and info string
        """
        if not self.is_enabled():
            logger.debug("RAG disabled, returning empty context")
            return "", ""
        
        k = k or config.rag_search_k
        
        try:
            logger.debug(f"Searching RAG vectorstore for: {query} (k={k})")
            relevant_docs = self.vectorstore.similarity_search(query, k=k)
            
            if not relevant_docs:
                logger.debug("No relevant documents found")
                return "", ""
            
            # Build context from documents
            max_chars = config.rag_context_max_chars
            context_parts = [doc.page_content[:max_chars] for doc in relevant_docs]
            context = "\n".join(context_parts)
            
            info = f"\n📚 {len(relevant_docs)} файлов"
            
            logger.info(f"Retrieved {len(relevant_docs)} relevant documents")
            logger.debug(f"RAG context length: {len(context)} characters")
            
            return context, info
            
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return "", ""
    
    def get_status_info(self) -> dict:
        """
        Get RAG service status information.
        
        Returns:
            dict: Status information
        """
        return {
            "enabled": self.is_enabled(),
            "vectorstore_loaded": self.vectorstore is not None
        }


# Global RAG service instance
rag_service = RAGService()
