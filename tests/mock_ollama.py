# tests/mock_ollama.py
import os
import unittest
from unittest.mock import patch
from langchain_openai import ChatOpenAI

class LocalOllamaTestCase(unittest.TestCase):
    """
    Base test class for Clean Code multi-agent workflow testing.
    Automatically patches get_dynamic_llm_client to return a local Ollama model instance,
    safeguarding against all cloud LLM API cost consumption during tests.
    """
    
    def setUp(self):
        # Determine local Ollama URL
        ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        if not ollama_url.endswith("/v1"):
            ollama_url = ollama_url.rstrip("/") + "/v1"
            
        # Create a mock local Ollama model client
        self.mock_client = ChatOpenAI(
            base_url=ollama_url,
            api_key="ollama",  # dummy key for local Ollama
            model="qwen2.5:3b",
            temperature=0.2,
            max_retries=1
        )
        
        # Apply patch to replace get_dynamic_llm_client with our mock local client
        # MUST patch the original source in 'core.ai_clients.llm_client' to intercept 
        # internal calls from generate_text() and other modules.
        self.llm_patcher = patch("core.ai_clients.llm_client.get_dynamic_llm_client")
        self.mock_get_client = self.llm_patcher.start()
        self.mock_get_client.return_value = self.mock_client
        
        super().setUp()
        
    def tearDown(self):
        self.llm_patcher.stop()
        super().tearDown()
