# core/document_service.py
import os
import uuid
import hashlib
import tempfile
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.storage import upload_file
from core.rag import store_document

logger = logging.getLogger("document_service")
logging.basicConfig(level=logging.INFO)

class DuplicateDocumentError(Exception):
    """Exception raised when a document already exists in the workspace."""
    pass

def process_and_store_document(
    db: Session,
    workspace_id: str,
    file_bytes: bytes,
    file_name: str,
    access_tags: List[str] = None
) -> dict:
    """
    Service Layer: Handle file upload, deduplication, MinIO upload, and RAG ingestion triggering.
    Returns a dict with document details or raises exceptions.
    """
    if access_tags is None:
        access_tags = ["global"]

    file_size = len(file_bytes)
    
    # Calculate SHA-256 for deduplication
    hasher = hashlib.sha256()
    hasher.update(file_bytes)
    file_hash = hasher.hexdigest()

    # Check for duplicate
    duplicate = db.execute(
        text("""
            SELECT document_id FROM rag_documents 
            WHERE workspace_id = CAST(:workspace_id AS uuid) 
              AND file_hash = :file_hash 
              AND is_deleted = FALSE 
            LIMIT 1
        """),
        {"workspace_id": str(workspace_id), "file_hash": file_hash}
    ).fetchone()

    if duplicate:
        raise DuplicateDocumentError("Tài liệu này đã tồn tại trong Knowledge Base. Bỏ qua quá trình xử lý để tiết kiệm tài nguyên.")

    # Determine extension
    ext = os.path.splitext(file_name)[-1].lower()

    # Save to temp file
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "temp"))
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_{file_name}")

    try:
        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)

        # Upload to MinIO
        object_key = f"rag/{workspace_id}/{uuid.uuid4()}{ext}"
        upload_file(temp_file_path, object_key)

        # Store in DB and kick Celery (handled by store_document)
        doc = store_document(
            db=db,
            workspace_id=workspace_id,
            file_name=file_name,
            file_key=object_key,
            access_tags=access_tags,
            file_size_bytes=file_size,
            file_hash=file_hash,
        )

        return {
            "document_id": str(doc.document_id),
            "file_name": file_name,
            "access_tags": access_tags,
            "status": "processing"
        }

    except Exception as e:
        logger.error(f"[process_and_store_document] Failed to process document {file_name}: {e}")
        raise e
    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
