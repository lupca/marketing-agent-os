# tests/test_parser.py
import os
import sys
import unittest

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.parser import chunk_text

class TestParserAndChunker(unittest.TestCase):
    
    def test_chunking_logic(self):
        """Verify that chunking divides text into appropriate overlapping boundaries."""
        sample_text = "This is a sample marketing document meant to test sliding window chunking boundary conditions. It should create multiple segments if the length exceeds chunk size."
        
        # Test small chunk size
        chunks = chunk_text(sample_text, chunk_size=30, overlap=10)
        
        self.assertTrue(len(chunks) > 1)
        # Check start and end indexes
        for chunk in chunks:
            self.assertIn("content", chunk)
            self.assertIn("start_idx", chunk)
            self.assertIn("end_idx", chunk)
            
            # Verify reconstructed text slice
            sliced = sample_text[chunk["start_idx"]:chunk["end_idx"]].strip()
            self.assertEqual(sliced, chunk["content"])
            
    def test_empty_text_handling(self):
        """Verify parser chunker handles empty inputs gracefully."""
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   "), [])

if __name__ == "__main__":
    unittest.main()
