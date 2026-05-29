# core/ollama_client.py
import os
import json
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("ollama_client")
logging.basicConfig(level=logging.INFO)

# Configs
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://172.22.45.28:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:14b-instruct")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
OLLAMA_RERANK_MODEL = os.getenv("OLLAMA_RERANK_MODEL", "bge-reranker-large:latest")

def generate_text(prompt: str, system_prompt: str = None, json_format: bool = False) -> str:
    """Generate text using Ollama's Qwen2.5 14B model."""
    try:
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": OLLAMA_LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_format:
            payload["format"] = "json"
            
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ollama server returned code {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error in generate_text: {e}")
        raise

def get_embedding(text_content: str) -> list:
    """Generate vector embedding (1024-dim) using bge-m3."""
    try:
        url = f"{OLLAMA_HOST}/api/embeddings"
        payload = {
            "model": OLLAMA_EMBED_MODEL,
            "prompt": text_content
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json().get("embedding", [])
        else:
            raise Exception(f"Ollama embedding returned code {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error in get_embedding: {e}")
        raise

def rerank_documents(query: str, documents: list) -> list:
    """
    Rerank retrieved documents using bge-reranker-large:latest.
    Each item in documents should be a dict: {"content": str, ...}
    Returns documents sorted by score descending, with a "rerank_score" injected.
    """
    if not documents:
        return []
        
    try:
        reranked_docs = []
        for doc in documents:
            prompt = (
                f"Rate the relevance of the following Document to the User Query on a scale from 0.0 to 1.0.\n"
                f"User Query: {query}\n"
                f"Document: {doc.get('content', '')}\n\n"
                f"Output ONLY a single floating-point number between 0.0 and 1.0 (e.g. 0.85). No other text."
            )
            score_str = generate_text(prompt, system_prompt="You are an expert search reranker. Output numbers only.")
            try:
                # Find any float in output
                import re
                match = re.search(r"(\d+\.\d+)", score_str)
                score = float(match.group(1)) if match else 0.5
            except Exception:
                score = 0.5
            doc["rerank_score"] = score
            reranked_docs.append(doc)
            
        return sorted(reranked_docs, key=lambda x: x["rerank_score"], reverse=True)
    except Exception as e:
        logger.error(f"Error in rerank_documents: {e}")
        raiseower().split()
            match_count = sum(1 for w in query_words if w in content_words)
            doc["rerank_score"] = float(match_count) / max(len(query_words), 1)
        return sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
