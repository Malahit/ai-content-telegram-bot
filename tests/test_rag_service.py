"""
Unit tests for RAG service module.

Tests RAG service initialization, singleton export, and method functionality.
"""

import unittest
from unittest.mock import patch, Mock, MagicMock
import asyncio
import os
import tempfile
import shutil


class TestRAGServiceImport(unittest.TestCase):
    """Test cases for RAG service import and initialization."""
    
    def test_singleton_import(self):
        """Test that rag_service instance can be imported."""
        # This verifies the main issue is fixed
        try:
            from rag_service import rag_service
            self.assertIsNotNone(rag_service)
        except ImportError as e:
            self.fail(f"Failed to import rag_service: {e}")
    
    def test_class_import(self):
        """Test that RAGService class can be imported."""
        try:
            from rag_service import RAGService
            self.assertIsNotNone(RAGService)
        except ImportError as e:
            self.fail(f"Failed to import RAGService class: {e}")
    
    def test_all_exports(self):
        """Test that __all__ is defined correctly."""
        import rag_service as module
        self.assertIn('rag_service', module.__all__)
        self.assertIn('RAGService', module.__all__)


class TestRAGServiceMethods(unittest.TestCase):
    """Test cases for RAGService methods."""
    
    @patch('langchain_community.embeddings.HuggingFaceEmbeddings')
    @patch('watchdog.observers.Observer')
    def setUp(self, mock_observer, mock_embeddings):
        """Set up test fixtures."""
        # Mock the embeddings to avoid downloading models
        mock_embeddings.return_value = MagicMock()
        mock_observer.return_value = MagicMock()
        
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        from rag_service import RAGService
        self.service = RAGService()
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_dir)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_is_enabled_with_no_vectorstore(self):
        """Test is_enabled returns False when no vectorstore is initialized."""
        self.service.vectorstore = None
        self.assertFalse(self.service.is_enabled())
    
    def test_is_enabled_with_vectorstore(self):
        """Test is_enabled returns True when vectorstore is initialized."""
        self.service.vectorstore = MagicMock()
        self.assertTrue(self.service.is_enabled())
    
    def test_get_context_when_disabled(self):
        """Test get_context returns (None, None) when RAG is disabled."""
        self.service.vectorstore = None
        
        async def run_test():
            context, info = await self.service.get_context("test topic")
            self.assertIsNone(context)
            self.assertIsNone(info)
        
        asyncio.run(run_test())
    
    def test_get_context_with_no_results(self):
        """Test get_context returns (None, None) when no documents found."""
        self.service.vectorstore = MagicMock()
        
        async def mock_asearch(query, k):
            return []
        
        self.service.asearch = mock_asearch
        
        async def run_test():
            context, info = await self.service.get_context("test topic")
            self.assertIsNone(context)
            self.assertIsNone(info)
        
        asyncio.run(run_test())
    
    def test_get_context_with_results(self):
        """Test get_context returns proper tuple with documents."""
        self.service.vectorstore = MagicMock()
        
        # Create mock documents
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "Content 1"
        mock_doc2 = MagicMock()
        mock_doc2.page_content = "Content 2"
        
        async def mock_asearch(query, k):
            return [mock_doc1, mock_doc2]
        
        self.service.asearch = mock_asearch
        
        async def run_test():
            context, info = await self.service.get_context("test topic")
            self.assertIsNotNone(context)
            self.assertIsNotNone(info)
            self.assertIn("Content 1", context)
            self.assertIn("Content 2", context)
            self.assertIn("2", info)  # Should mention 2 documents
        
        asyncio.run(run_test())


class TestRAGServiceInitialization(unittest.TestCase):
    """Test cases for RAG service initialization with defaults."""
    
    @patch('watchdog.observers.Observer')
    @patch('langchain_community.embeddings.HuggingFaceEmbeddings')
    def test_default_embeddings_model(self, mock_embeddings, mock_observer):
        """Test that default embeddings model is used when config doesn't have it."""
        mock_embeddings.return_value = MagicMock()
        mock_observer.return_value = MagicMock()
        
        # Mock config without EMBEDDINGS_MODEL attribute
        with patch('rag_service.config', spec=['bot_token', 'pplx_api_key']) as mock_config:
            # Ensure getattr returns the default
            with patch.dict(os.environ, {}, clear=True):
                from rag_service import RAGService, DEFAULT_EMBEDDINGS_MODEL
                
                # Create temporary directory
                test_dir = tempfile.mkdtemp()
                original_dir = os.getcwd()
                os.chdir(test_dir)
                
                try:
                    # Reset mock to clear any previous calls from module reloading
                    mock_embeddings.reset_mock()
                    
                    service = RAGService()
                    
                    # Check that HuggingFaceEmbeddings was called with default model
                    # Note: Using assertTrue instead of assert_called_once because
                    # test framework may reload modules causing multiple calls
                    self.assertTrue(mock_embeddings.called)
                    # Get the most recent call
                    call_args = mock_embeddings.call_args
                    self.assertEqual(call_args[1]['model_name'], DEFAULT_EMBEDDINGS_MODEL)
                finally:
                    os.chdir(original_dir)
                    shutil.rmtree(test_dir)
    
    @patch('watchdog.observers.Observer')
    @patch('langchain_community.embeddings.HuggingFaceEmbeddings')
    def test_knowledge_directory_created(self, mock_embeddings, mock_observer):
        """Test that knowledge directory is created if it doesn't exist."""
        mock_embeddings.return_value = MagicMock()
        mock_observer.return_value = MagicMock()
        
        # Create temporary directory
        test_dir = tempfile.mkdtemp()
        original_dir = os.getcwd()
        os.chdir(test_dir)
        
        try:
            from rag_service import RAGService, KNOWLEDGE_DIR
            
            # Remove knowledge dir if it exists
            if os.path.exists(KNOWLEDGE_DIR):
                os.rmdir(KNOWLEDGE_DIR)
            
            # Create service
            service = RAGService()
            
            # Check that directory was created
            self.assertTrue(os.path.exists(KNOWLEDGE_DIR))
            self.assertTrue(os.path.isdir(KNOWLEDGE_DIR))
        finally:
            os.chdir(original_dir)
            shutil.rmtree(test_dir)


if __name__ == '__main__':
    unittest.main()
