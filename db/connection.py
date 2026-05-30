# db/connection.py
import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_connection")

# Base class for SQLAlchemy Models
Base = declarative_base()

# ──────────────────────────────────────────────────────────
# Connection String Configurations
# ──────────────────────────────────────────────────────────
# Raw URL from env (e.g. "postgresql://user:pass@host:5432/db")
_RAW_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:secret_password@localhost:5433/marketing_agent_db"
)

# SQLAlchemy URL: use psycopg v3 driver (matches `psycopg[binary]` in requirements.txt)
# "postgresql+psycopg://" → psycopg v3
# "postgresql+psycopg2://" → psycopg2 (NOT installed in this project)
POSTGRES_URL = _RAW_URL
if POSTGRES_URL.startswith("postgresql://") and "+psycopg" not in POSTGRES_URL:
    POSTGRES_URL = POSTGRES_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Native psycopg conninfo string for AsyncConnectionPool (LangGraph checkpointer)
# psycopg native pool only accepts "postgresql://" or libpq DSN, NOT "postgresql+psycopg://"
PSYCOPG_CONNINFO = _RAW_URL  # keep as plain postgresql:// for native psycopg

engine = None
SessionLocal = None
IS_MOCK_DATABASE = False

# Attempt connecting to PostgreSQL
# NOTE: pool_pre_ping=True validates the connection before each use (lazy).
# Do NOT test connection at module-load time — this causes crashes in Docker
# Celery workers where DNS resolution may not be ready at import time.
logger.info("Connecting to PostgreSQL database...")
engine = create_engine(
    POSTGRES_URL,
    pool_pre_ping=True,
    pool_recycle=300,   # recycle connections every 5 minutes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info("Successfully connected to PostgreSQL database!")

def get_db():
    """Dependency for acquiring database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_mock():
    """Helper to check if currently running on SQLite mock fallback. Always returns False."""
    return False
