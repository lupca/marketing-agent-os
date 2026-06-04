import os
import sys
import time
import logging

# Add the parent directory to sys.path to allow imports from core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from db.connection import SessionLocal
from core.models import RAGChunk, RAGDocument
from core.ai_clients.embeddings import get_embedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_embeddings")

def migrate_database_embeddings():
    db = SessionLocal()
    try:
        # Get all active chunks
        chunks = db.query(RAGChunk).filter(RAGChunk.is_deleted == False).all()
        logger.info(f"Found {len(chunks)} active chunks to re-embed.")

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)} (ID: {chunk.chunk_id})...")
            
            try:
                # Re-embed using the new Qwen3 Cloud API
                new_vector = get_embedding(chunk.content)
                if new_vector and len(new_vector) > 0:
                    chunk.embedding = new_vector
                    db.commit()
                    logger.info(f"Successfully re-embedded chunk {i+1} with length {len(new_vector)}")
                else:
                    logger.warning(f"Failed to generate embedding for chunk {i+1}")
            except Exception as e:
                logger.error(f"Error embedding chunk {i+1}: {e}")
            
            # Tiny sleep to respect API rate limits
            time.sleep(0.1)
            
        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting embedding migration to SiliconFlow Cloud API (Qwen3)...")
    migrate_database_embeddings()
