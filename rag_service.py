import os
import logging
import threading
import asyncio
from typing import List, Tuple, Optional
from config import config
from logger_config import logger

# Default embeddings model if not specified in config
DEFAULT_EMBEDDINGS_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Knowledge base directory
KNOWLEDGE_DIR = "./knowledge"

# Check if RAG is enabled via environment variable (default: true)
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() in ("true", "1", "yes")

class RAGService:
    def __init__(self):
        # Create knowledge directory if it doesn't exist
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        
        # Initialize as disabled by default
        self.embeddings = None
        self.vectorstore = None
        self.observer = None
        
        # Check if RAG is explicitly disabled
        if not RAG_ENABLED:
            logger.info("ℹ️ RAG service disabled via RAG_ENABLED environment variable")
            return
        
        # Get embeddings model from config with safe default
        embeddings_model = getattr(config, "EMBEDDINGS_MODEL", os.getenv("EMBEDDINGS_MODEL", DEFAULT_EMBEDDINGS_MODEL))
        
        # Try to initialize embeddings - if it fails, disable RAG gracefully
        try:
            # Import dependencies here to avoid import-time crashes
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from watchdog.observers import Observer
            
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embeddings_model,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False}
            )
            self.vectorstore = None  # Will be set by _initialize_vectorstore
            self.observer = Observer()
            self._start_watcher()
            self._initialize_vectorstore()
            logger.info("✅ RAG service initialized successfully")
        except ImportError as e:
            logger.warning(f"⚠️ RAG service disabled: Missing dependency - {str(e)}")
            logger.info("💡 To enable RAG features, install: pip install -r requirements-rag.txt")
            self.embeddings = None
            self.vectorstore = None
            self.observer = None
        except Exception as e:
            logger.warning(f"⚠️ RAG service disabled: Initialization failed - {str(e)}")
            self.embeddings = None
            self.vectorstore = None
            self.observer = None
    
    def _start_watcher(self):
        # Import here since Observer is imported inside __init__ try block
        from watchdog.events import FileSystemEventHandler
        
        # Only start watcher if observer was initialized
        if not self.observer:
            return
            
        class KnowledgeBaseHandler(FileSystemEventHandler):
            def __init__(self, rag_service):
                self.rag_service = rag_service
            
            def on_any_event(self, event):
                if not event.is_directory and event.src_path.endswith(('.txt', '.md', '.pdf')):
                    logger.info(f"🔄 Обнаружено изменение в: {event.src_path}")
                    self.rag_service.reload_knowledge_base()
        
        event_handler = KnowledgeBaseHandler(self)
        self.observer.schedule(event_handler, path=KNOWLEDGE_DIR, recursive=True)
        self.observer_thread = threading.Thread(target=self.observer.start, daemon=True)
        self.observer_thread.start()
        logger.info(f"👀 Наблюдение за папкой {KNOWLEDGE_DIR} запущено")
    
    def reload_knowledge_base(self):
        logger.info("⏳ Перезагрузка RAG-базы...")
        try:
            self._initialize_vectorstore()
            logger.info("✅ RAG-база успешно перезагружена!")
        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки: {str(e)}")
    
    def _initialize_vectorstore(self):
        # Only initialize if embeddings are available
        if not self.embeddings:
            return
            
        # Import langchain dependencies here (they're imported in __init__ try block)
        from langchain_community.vectorstores import FAISS
        from langchain_community.document_loaders import (
            TextLoader, 
            PyPDFLoader, 
            UnstructuredMarkdownLoader
        )
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        documents = []
        for root, _, files in os.walk(KNOWLEDGE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if file.endswith(".txt"):
                        loader = TextLoader(file_path)
                    elif file.endswith(".pdf"):
                        loader = PyPDFLoader(file_path)
                    elif file.endswith(".md"):
                        loader = UnstructuredMarkdownLoader(file_path)
                    else:
                        continue
                    
                    docs = loader.load()
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=500,
                        chunk_overlap=50
                    )
                    documents.extend(text_splitter.split_documents(docs))
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось обработать {file_path}: {str(e)}")
        
        if documents:
            self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            logger.info(f"📚 RAG-база загружена. Документов: {len(documents)}")
        else:
            logger.warning(f"📁 Папка {KNOWLEDGE_DIR} пуста. RAG-база не инициализирована.")
    
    async def asearch(self, query: str, k: int = 3) -> List:
        """
        Search for similar documents.
        
        Args:
            query: The search query
            k: Number of results to return (default: 3)
            
        Returns:
            List of Document objects if vectorstore is available, empty list otherwise.
        """
        if not self.vectorstore:
            return []
        return await asyncio.to_thread(self.vectorstore.similarity_search, query, k=k)
    
    def is_enabled(self) -> bool:
        """Check if RAG service is enabled and has a vectorstore."""
        return self.vectorstore is not None
    
    async def get_context(self, topic: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get RAG context for a given topic.
        
        Args:
            topic: The topic to search for
            
        Returns:
            A tuple of (rag_context, rag_info) where:
            - rag_context: The context string for the topic (or None)
            - rag_info: Additional info about the RAG results (or None)
        """
        if not self.is_enabled():
            return None, None
        
        try:
            # Search for relevant documents
            docs = await self.asearch(topic, k=3)
            
            if not docs:
                return None, None
            
            # Combine document content as context
            rag_context = "\n\n".join([doc.page_content for doc in docs])
            
            # Create info string about the RAG results
            rag_info = f"\n\n📚 <i>На основе {len(docs)} документов из базы знаний</i>"
            
            return rag_context, rag_info
        except Exception as e:
            logger.error(f"❌ Ошибка при получении RAG контекста: {str(e)}")
            return None, None
    
    async def stop_observer(self):
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)
            logger.info("🛑 Наблюдение за файловой системой остановлено")
        else:
            logger.debug("🛑 Наблюдатель не инициализирован, нечего останавливать")


# Create and export singleton instance
rag_service = RAGService()

# Define exports
__all__ = ["rag_service", "RAGService"]