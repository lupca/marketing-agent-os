# tests/conftest.py
import os
import pytest
from dotenv import load_dotenv
from unittest.mock import patch
import responses

# 1. Load .env.test FIRST to ensure test DB is used
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env.test')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)

# Safely import app modules after env is set
from db.connection import Base
import core.dependencies

# ==========================================
# DATABASE FIXTURES (Nested Transactions)
# ==========================================
@pytest.fixture(scope="session", autouse=True)
def db_engine():
    """Create test engine and tables once per session."""
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    from sqlalchemy import create_engine, text
    test_engine = create_engine(url, pool_pre_ping=True)
    with test_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a transactional DB session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    
    from sqlalchemy.orm import sessionmaker
    TestingSessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    
    # Override get_db_base in dependencies to use this session
    def override_get_db_base():
        yield session
        
    with patch("core.dependencies.get_db_base", side_effect=override_get_db_base):
        yield session

    session.close()
    transaction.rollback()
    connection.close()

# ==========================================
# GLOBAL CLOUD API MOCKS (Block Network)
# ==========================================
def mock_get_embedding(text_content: str) -> list:
    return [0.1] * 1024

def mock_rerank_documents(query: str, documents: list, workspace_id: str = None) -> list:
    for i, doc in enumerate(documents):
        doc["rerank_score"] = 1.0 / (i + 1)
    return sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

def mock_generate_text(prompt: str, system_prompt: str = None, json_format: bool = False, workspace_id: str = None) -> str:
    if json_format:
        if "tiktok" in prompt.lower() or "video" in prompt.lower():
            return '{"angle_name": "Logic", "adapted_copy": "[Visual] Show badminton player playing. [Audio] Vợt TOPVNSPORT V200i cực kỳ chất lượng", "tone_markers": ["hào hứng"]}'
        return '{"angle_name": "Logic", "adapted_copy": "Mocked test response content for creative engines in JSON"}'
    return "Mocked test response content for creative engines"

@pytest.fixture(scope="session", autouse=True)
def auto_mock_cloud_clients():
    """Automatically mock all expensive cloud AI calls globally."""
    patches = [
        patch("core.ai_clients.embeddings.get_embedding", side_effect=mock_get_embedding, create=True),
        patch("core.ollama_client.get_embedding", side_effect=mock_get_embedding, create=True),
        patch("core.rag.get_embedding", side_effect=mock_get_embedding, create=True),
        patch("core.tasks.get_embedding", side_effect=mock_get_embedding, create=True),
        
        patch("core.ai_clients.reranker.rerank_documents", side_effect=mock_rerank_documents, create=True),
        patch("core.ollama_client.rerank_documents", side_effect=mock_rerank_documents, create=True),
        patch("core.rag.rerank_documents", side_effect=mock_rerank_documents, create=True),
        
        patch("core.ai_clients.llm_client.generate_text", side_effect=mock_generate_text, create=True),
        patch("core.ollama_client.generate_text", side_effect=mock_generate_text, create=True),
        patch("core.market_intelligence.generate_text", side_effect=mock_generate_text, create=True),
        patch("core.tasks.generate_text", side_effect=mock_generate_text, create=True),
        patch("graphs.autonomous.generation.generate_text", side_effect=mock_generate_text, create=True),
        patch("graphs.autonomous.guardian.generate_text", side_effect=mock_generate_text, create=True),
        patch("graphs.autonomous.insight.generate_text", side_effect=mock_generate_text, create=True),
    ]
    
    # Enter all patches
    for p in patches:
        p.start()
        
    yield
    
    # Stop all patches
    for p in reversed(patches):
        p.stop()
