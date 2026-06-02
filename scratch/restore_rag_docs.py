import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.dependencies import get_session
from core.document_service import process_and_store_document, DuplicateDocumentError
from core.models import Workspace

STORAGE_DIR = project_root / "data" / "storage" / "marketing-assets" / "rag"

def restore_docs():
    print(f"Scanning directory: {STORAGE_DIR}")
    if not STORAGE_DIR.exists():
        print("Storage directory does not exist.")
        return

    with get_session() as db:
        workspace = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        if not workspace:
            print("Workspace not found!")
            return
        
        ws_id = str(workspace.id)
        print(f"Restoring files to Workspace: {ws_id}")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        # Recursively find all files in the RAG storage directory
        for file_path in STORAGE_DIR.rglob("*.*"):
            if file_path.is_file():
                try:
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    
                    # We pass the file to process_and_store_document which handles DB insertion & triggers Celery
                    doc_info = process_and_store_document(
                        db=db,
                        workspace_id=ws_id,
                        file_bytes=file_bytes,
                        file_name=f"restored_{file_path.name}", # Prefix to indicate it was restored
                        access_tags=["global", "restored"]
                    )
                    success_count += 1
                    print(f"✅ Restored: {file_path.name} -> New Doc ID: {doc_info['document_id']}")
                except DuplicateDocumentError:
                    skip_count += 1
                    print(f"⏭️ Skipped (Already in DB): {file_path.name}")
                except Exception as e:
                    error_count += 1
                    print(f"❌ Failed to restore {file_path.name}: {e}")
                    
        print(f"\n--- RESTORE COMPLETE ---")
        print(f"Successfully Queued: {success_count}")
        print(f"Skipped (Duplicates): {skip_count}")
        print(f"Failed/Errors: {error_count}")

if __name__ == "__main__":
    restore_docs()