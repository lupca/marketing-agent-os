# scratch/test_ollama.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ollama_client import get_embedding, generate_text

print("Testing get_embedding...")
try:
    emb = get_embedding("Hello world")
    print(f"Success! Embedding length: {len(emb)}")
except Exception as e:
    print(f"Error in get_embedding: {e}")

print("Testing generate_text...")
try:
    resp = generate_text("Say hello!", system_prompt="You are a helper.")
    print(f"Success! Response: {resp}")
except Exception as e:
    print(f"Error in generate_text: {e}")
