# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

MAX_CONTEXT_TOKENS = 14000
LLM_CTX_WINDOW = 16384
GUARDIAN_PASS_SCORE = 80

# Economic default fallbacks
DEFAULT_TARGET_CPA = 1050000.0
DEFAULT_TEST_BUDGET = 2000000.0

# Intelligent Supervisor Hub (Triage) Settings
TRIAGE_CONTEXT_MESSAGES = 10           # Số tin nhắn gần nhất cho Context Aggregator (Layer 1)
TRIAGE_FEW_SHOT_COUNT = 3             # Số mẫu few-shot từ pgvector (Layer 2)
TRIAGE_FALLBACK_INTENT = "research"   # Intent mặc định khi LLM parse thất bại

# ============================================================
# Redis & Celery (Async Task Queue)
# ============================================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# ============================================================
# RAG Chunking Strategy (Quyết định CTO v3 — Semantic Boundary)
# Lý do chunk_size=1000: Qwen2.5 14B đọc context sâu.
# Cắt vụn 500 chars khiến LLM mất bối cảnh liên trang.
# ============================================================
RAG_CHUNK_SIZE = 1000
RAG_CHUNK_OVERLAP = 200
RAG_CHUNK_SEPARATORS = ["\n\n", "\n", ".", "?", "!", " "]

# ============================================================
# RAG Retrieval Settings
# ============================================================
RAG_RETRIEVAL_LIMIT = 5          # Số chunks trả về sau rerank (top-K)
RAG_CANDIDATE_LIMIT = 10         # Số candidates trước khi rerank
RAG_DEFAULT_TAGS = ["global"]    # Tags mặc định khi không có context cụ thể

# ============================================================
# Video Agent Integration (CTO v3 Integration Plan)
# ============================================================
VIDEO_AGENT_URL = os.getenv("VIDEO_AGENT_URL", "http://localhost:8001")
VIDEO_AGENT_API_KEY = os.getenv("VIDEO_AGENT_API_KEY", "tmcp_secret_key_123")

