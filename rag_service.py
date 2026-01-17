import os
import logging
import threading
import asyncio
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    UnstructuredMarkdownLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import config
from logger_config import logger

class KnowledgeBaseHandler(FileSystemEventHandler):
    def __init__(self, rag_service):
        self.rag_service = rag_service
    
    def on_any_event(self, event):
        if not event.is_directory and event.src_path.endswith(('.txt', '.md', '.pdf')):
            logger.info(f"🔄 Обнаружено изменение в: {event.src_path}")
            self.rag_service.reload_knowledge_base()

class RAGService:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBEDDINGS_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )
        self.vectorstore = None
        self.observer = Observer()
        self._start_watcher()
        self._initialize_vectorstore()
    
    def _start_watcher(self):
        event_handler = KnowledgeBaseHandler(self)
        self.observer.schedule(event_handler, path="./knowledge", recursive=True)
        self.observer_thread = threading.Thread(target=self.observer.start, daemon=True)
        self.observer_thread.start()
        logger.info("👀 Наблюдение за папкой ./knowledge запущено")
    
    def reload_knowledge_base(self):
        logger.info("⏳ Перезагрузка RAG-базы...")
        try:
            self._initialize_vectorstore()
            logger.info("✅ RAG-база успешно перезагружена!")
        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки: {str(e)}")
    
    def _initialize_vectorstore(self):
        documents = []
        for root, _, files in os.walk("./knowledge"):
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
            logger.warning("📁 Папка ./knowledge пуста. RAG-база не инициализирована.")
    
    async def asearch(self, query: str, k: int = 3) -> List[Document]:
        if not self.vectorstore:
            return []
        return await asyncio.to_thread(self.vectorstore.similarity_search, query, k=k)
    
    async def stop_observer(self):
        self.observer.stop()
        self.observer.join(timeout=5.0)
        logger.info("🛑 Наблюдение за файловой системой остановлено")