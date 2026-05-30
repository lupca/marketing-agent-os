# tests/test_parser.py
import os
import sys
import unittest

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.parser import semantic_chunk_text

class TestParserAndChunker(unittest.TestCase):
    
    def test_chunking_logic(self):
        """Verify that semantic chunking divides text into appropriate segments."""
        sample_text = "This is a sample marketing document meant to test sliding window chunking boundary conditions. It should create multiple segments if the length exceeds chunk size."
        
        # Test small chunk size
        chunks = semantic_chunk_text(sample_text, chunk_size=30, chunk_overlap=10)
        
        self.assertTrue(len(chunks) > 0)
        # Check that we got a list of strings
        for chunk in chunks:
            self.assertTrue(isinstance(chunk, str))
            self.assertTrue(len(chunk) >= 10) # Filters out < 10 chars
            
    def test_empty_text_handling(self):
        """Verify parser chunker handles empty inputs gracefully."""
        self.assertEqual(semantic_chunk_text(""), [])
        self.assertEqual(semantic_chunk_text("   "), [])

if __name__ == "__main__":
    unittest.main()
