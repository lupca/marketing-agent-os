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

# Connection String Configurations
POSTGRES_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:secret_password@localhost:5432/marketing_agent_db"
)

engine = None
SessionLocal = None
IS_MOCK_DATABASE = False

# Attempt connecting to PostgreSQL
logger.info("Connecting to PostgreSQL database...")
engine = create_engine(
    POSTGRES_URL, 
    pool_pre_ping=True
)
# Test connection
with engine.connect() as conn:
    conn.execute(text("SELECT 1"))

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
