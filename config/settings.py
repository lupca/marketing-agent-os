# config/settings.py

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
