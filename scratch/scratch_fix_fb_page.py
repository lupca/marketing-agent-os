import os
import sys

# Ensure the correct path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.dependencies import get_session
from core.models import WorkspaceIntegration, Workspace

with get_session() as db:
    workspaces = db.query(Workspace).all()
    count = 0
    for ws in workspaces:
        existing = db.query(WorkspaceIntegration).filter_by(
            workspace_id=ws.id,
            platform_name="upload-post",
            config_key="facebook_page_id"
        ).first()
        
        if existing:
            existing.config_value = "61580803074671"
            existing.is_active = True
        else:
            new_integ = WorkspaceIntegration(
                workspace_id=ws.id,
                platform_name="upload-post",
                config_key="facebook_page_id",
                config_value="61580803074671",
                is_active=True
            )
            db.add(new_integ)
        count += 1
    db.commit()
    print(f"Successfully updated facebook_page_id for {count} workspace(s).")
