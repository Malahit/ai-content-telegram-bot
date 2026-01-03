from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

class RAGKnowledgeBase:
    def __init__(self, vectorstore_path="rag/vectorstore"):
        self.vectorstore_path = vectorstore_path
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("PPLX_API_KEY"))
        self.vectorstore = None
    
    def load_documents(self, files_path="rag/documents"):
        """Загрузка PDF/DOCX из папки"""
        docs = []
        for file in os.listdir(files_path):
            if file.endswith('.pdf'):
                loader = PyPDFLoader(os.path.join(files_path, file))
            elif file.endswith('.docx'):
                loader = UnstructuredWordDocumentLoader(os.path.join(files_path, file))
            else:
                continue
            docs.extend(loader.load())
        return docs
    
    def create_vectorstore(self, docs):
        """Создать/обновить векторную базу"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)
        
        self.vectorstore = FAISS.from_documents(
            splits, self.embeddings
        )
        self.vectorstore.save_local(self.vectorstore_path)
        print(f"✅ Vectorstore сохранён: {self.vectorstore_path}")
    
    def load_vectorstore(self):
        """Загрузить существующую базу"""
        self.vectorstore = FAISS.load_local(
            self.vectorstore_path, self.embeddings, allow_dangerous_deserialization=True
        )
    
    def search(self, query, k=3):
        """Поиск релевантных документов"""
        if not self.vectorstore:
            self.load_vectorstore()
        docs = self.vectorstore.similarity_search(query, k=k)
        return "\n".join([doc.page_content for doc in docs])
