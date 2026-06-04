# tests/mock_ollama.py
import os
import unittest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage

class LocalOllamaTestCase(unittest.TestCase):
    """
    Base test class for Clean Code multi-agent workflow testing.
    Automatically patches get_dynamic_llm_client to return a mock local model instance,
    safeguarding against all cloud LLM API cost consumption during tests.
    """
    
    def setUp(self):
        # Create a mock client that returns structured JSON
        self.mock_client = MagicMock()
        self.mock_client.model = "qwen2.5:3b"
        
        # Default mock response representing a platform variant copy dynamic to platform
        def mock_invoke(messages, *args, **kwargs):
            # Extract content from human message
            human_content = ""
            for msg in messages:
                if getattr(msg, "content", None) and msg.__class__.__name__ == "HumanMessage":
                    human_content = msg.content
                    break
            
            if "TIKTOK" in human_content.upper():
                content = '{"adapted_copy": "[Visual] Show badminton player playing. [Audio] Vợt TOPVNSPORT V200i cực kỳ chất lượng", "angle_name": "Fear", "tone_markers": ["hào hứng"]}'
            else:
                content = '{"adapted_copy": "Vợt TOPVNSPORT V200i cực kỳ chất lượng - hàng chính hãng 100%!", "angle_name": "Fear", "tone_markers": ["chuyên nghiệp"]}'
                
            return AIMessage(
                content=content,
                response_metadata={"token_usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}
            )
            
        self.mock_client.invoke.side_effect = mock_invoke
        
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
