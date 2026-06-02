import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.dependencies import get_session
from core.models import RAGDocument

with get_session() as db:
    count = db.query(RAGDocument).count()
    print(f"Total documents in rag_documents: {count}")
    
    docs = db.query(RAGDocument).order_by(RAGDocument.created_at.desc()).limit(5).all()
    for doc in docs:
        print(f"ID: {doc.document_id}, Status: {doc.upload_status}, Deleted: {doc.is_deleted}")
