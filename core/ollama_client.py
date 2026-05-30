# core/ollama_client.py
# Thin facade interface exposing specialized submodules inside core/ai_clients for absolute backward compatibility.
# Adheres to the Facade Pattern and Separation of Concerns (SoC) principles, keeping the core directory clean.

from core.ai_clients.llm_client import get_dynamic_llm_client, generate_text, MODEL_PRICING, DEFAULT_PRICING
from core.ai_clients.embeddings import get_embedding
from core.ai_clients.reranker import rerank_documents
from core.ai_clients.context_manager import get_trimmed_context
