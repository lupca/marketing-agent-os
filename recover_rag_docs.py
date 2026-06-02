import os
import sys
import uuid
import tempfile

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from db.connection import SessionLocal
from core.models import Workspace, RAGDocument
from core.tasks import ingest_document

def recover_files():
    db = SessionLocal()
    rag_dir = "data/storage/marketing-assets/rag/"
    
    # Get the default workspace ID
    workspace = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
    if not workspace:
        print("Error: Team Alpha Workspace not found!")
        return
        
    workspace_id = str(workspace.id)
    recovered_count = 0
    
    if not os.path.exists(rag_dir):
        print(f"Directory {rag_dir} does not exist.")
        return

    print(f"Starting recovery for files in {rag_dir} to Workspace {workspace_id}...")

    # For each file in the rag directory
    for filename in os.listdir(rag_dir):
        file_path = os.path.join(rag_dir, filename)
        if os.path.isfile(file_path):
            # Check if record exists in DB
            existing_doc = db.query(RAGDocument).filter_by(
                workspace_id=uuid.UUID(workspace_id), 
                file_name=filename
            ).first()
            
            if not existing_doc:
                # We need to simulate the file existing in MinIO or bypass MinIO.
                # Ingest_document downloads from MinIO using file_key. 
                # Let's assume file_key is just the path or the filename in the rag bucket.
                file_key = f"marketing-assets/rag/{filename}"
                file_size = os.path.getsize(file_path)
                
                # Create the Document record first
                doc_id = uuid.uuid4()
                new_doc = RAGDocument(
                    document_id=doc_id,
                    workspace_id=uuid.UUID(workspace_id),
                    file_name=filename,
                    file_key=file_key,
                    access_tags=["global", "recovered"],
                    upload_status="processing",
                    sync_status="synced",
                    file_size_bytes=file_size,
                    is_deleted=False
                )
                db.add(new_doc)
                db.commit()
                print(f"Created RAGDocument record for {filename} (ID: {doc_id})")
                
                # Trigger Celery Task to ingest chunks
                try:
                    # Note: You need MinIO to actually serve this file or you might need to upload it to MinIO first
                    # If it's already in the local path but not MinIO, ingest_document might fail.
                    ingest_document.delay(str(doc_id), file_key, workspace_id, ["global", "recovered"])
                    print(f"Triggered vector ingestion task for {filename}")
                    recovered_count += 1
                except Exception as e:
                    print(f"Failed to trigger ingestion for {filename}: {e}")

    print(f"Recovery complete. Triggered re-ingestion for {recovered_count} documents.")

if __name__ == '__main__':
    recover_files()
