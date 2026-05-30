# core/ollama_client.py
import os
import logging
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.messages import trim_messages, SystemMessage, HumanMessage

load_dotenv()
logger = logging.getLogger("ollama_client")
logging.basicConfig(level=logging.INFO)

# Configs
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://172.22.45.28:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b-instruct")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
OLLAMA_RERANK_MODEL = os.getenv("OLLAMA_RERANK_MODEL", "bge-reranker-large:latest")

# Initialize LangChain Ollama Models
llm = ChatOllama(
    base_url=OLLAMA_HOST,
    model=OLLAMA_LLM_MODEL,
    temperature=0.2,
    num_ctx=16384
)

llm_json = ChatOllama(
    base_url=OLLAMA_HOST,
    model=OLLAMA_LLM_MODEL,
    temperature=0.2,
    num_ctx=16384,
    format="json"
)

embeddings_model = OllamaEmbeddings(
    base_url=OLLAMA_HOST,
    model=OLLAMA_EMBED_MODEL
)

def generate_text(prompt: str, system_prompt: str = None, json_format: bool = False) -> str:
    """Generate text using Ollama's ChatOllama model through LangChain."""
    try:
        model = llm_json if json_format else llm
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        response = model.invoke(messages)
        return response.content
    except Exception as e:
        logger.error(f"Error in generate_text: {e}")
        raise

def get_embedding(text_content: str) -> list:
    """Generate vector embedding (1024-dim) using bge-m3 via OllamaEmbeddings."""
    try:
        return embeddings_model.embed_query(text_content)
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
        raise

def get_trimmed_context(messages: list, max_tokens: int = 14000) -> list:
    """
    Trims the conversation messages list using LangChain's trim_messages utility
    to ensure it fits within the context window (default max 14000 tokens).
    """
    if not messages:
        return []
        
    def count_tokens(msgs: list) -> int:
        total_tokens = 0
        for m in msgs:
            total_tokens += len(m.content or "") // 3.5 + 4
        return int(total_tokens)
        
    try:
        trimmed = trim_messages(
            messages,
            max_tokens=max_tokens,
            strategy="last",
            token_counter=count_tokens,
            include_system=True,
            allow_partial=False
        )
        logger.info(f"Successfully trimmed messages context. Count before: {len(messages)}, after: {len(trimmed)}")
        return trimmed
    except Exception as e:
        logger.error(f"Error in trim_messages: {e}. Falling back to basic slice.", exc_info=True)
        from langchain_core.messages import SystemMessage
        system_msg = [messages[0]] if isinstance(messages[0], SystemMessage) else []
        other_msgs = messages[1:] if system_msg else messages
        return system_msg + other_msgs[-8:]
