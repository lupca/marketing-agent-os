# scratch_update_page.py
import uuid
from db.connection import SessionLocal
from core.models import WorkspaceIntegration

def update_page_id():
    db = SessionLocal()
    try:
        workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        print("Locating Facebook Page integration config...")
        integration = db.query(WorkspaceIntegration).filter_by(
            workspace_id=workspace_id,
            platform_name="upload-post",
            config_key="facebook_page_id"
        ).first()
        
        if not integration:
            print("Error: Facebook Page integration config not found.")
            return
            
        print("Old Page ID:", integration.config_value)
        new_page_id = "1036098656250618"
        
        integration.config_value = new_page_id
        db.add(integration)
        db.commit()
        print("SUCCESS! Facebook Page ID updated to:", new_page_id)
        
    except Exception as e:
        print("Failed to update Page ID:", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_page_id()
