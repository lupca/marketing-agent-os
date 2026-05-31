# core/dependencies.py
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from db.connection import SessionLocal
import logging

logger = logging.getLogger(__name__)

def get_db_base() -> Generator[Session, None, None]:
    """
    Base generator for database sessions.
    Used by FastAPI dependencies and the context manager.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions (for manual use).
    Usage:
        with get_session() as db:
            # do work
            db.commit()
    """
    # Simply wrap the base generator
    yield from get_db_base()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    Usage:
        @app.get("/")
        def index(db: Session = Depends(get_db)):
            ...
    """
    yield from get_db_base()


