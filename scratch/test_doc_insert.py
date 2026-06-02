import os
import sys
from pathlib import Path
import uuid

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.dependencies import get_session
from core.models import RAGDocument, Workspace

with get_session() as db:
    ws = db.query(Workspace).first()
    doc_id = uuid.uuid4()
    doc = RAGDocument(
        document_id=doc_id,
        workspace_id=ws.id,
        file_name="test_doc.txt",
        file_key="test_key",
        access_tags=["global"],
        upload_status="processing",
        sync_status="synced",
        file_size_bytes=100
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    print(f"Created doc: {doc.document_id}")
    
    from sqlalchemy import text
    row = db.execute(
        text("""
            SELECT upload_status, sync_status, chunk_count, file_name, updated_at
            FROM rag_documents
            WHERE document_id = CAST(:doc_id AS UUID) AND is_deleted = FALSE
        """),
        {"doc_id": str(doc.document_id)}
    ).fetchone()
    print(f"Queried row: {row}")
