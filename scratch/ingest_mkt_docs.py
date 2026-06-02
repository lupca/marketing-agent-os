import os
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.dependencies import get_session
from core.document_service import process_and_store_document, DuplicateDocumentError
from core.models import Workspace

TARGET_DIR = project_root / "docs" / "agentic ai" / "MKT"

def ingest_mkt_docs():
    if not TARGET_DIR.exists() or not TARGET_DIR.is_dir():
        print(f"Error: Target directory {TARGET_DIR} does not exist.")
        return

    with get_session() as db:
        workspace = db.query(Workspace).first()
        if not workspace:
            print("Error: No workspace found in the database.")
            return
            
        workspace_id = str(workspace.id)
        print(f"Using Workspace ID: {workspace_id}")

        for filepath in TARGET_DIR.iterdir():
            if filepath.is_file():
                try:
                    print(f"\nProcessing {filepath.name}...")
                    with open(filepath, "rb") as f:
                        file_bytes = f.read()

                    doc_info = process_and_store_document(
                        db=db,
                        workspace_id=workspace_id,
                        file_bytes=file_bytes,
                        file_name=filepath.name,
                        access_tags=["global", "mkt"]
                    )
                    print(f"Success! Document ID: {doc_info['document_id']}")
                except DuplicateDocumentError as e:
                    print(f"Skipped {filepath.name}: {e}")
                except Exception as e:
                    print(f"Failed to process {filepath.name}: {e}")

if __name__ == "__main__":
    ingest_mkt_docs()