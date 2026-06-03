from core.dependencies import get_session
from core.models import WorkspaceIntegration
import uuid

with get_session() as db:
    configs = db.query(WorkspaceIntegration).filter_by(workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000002")).all()
    print("--- Workspace Integrations ---")
    for c in configs:
        print(f"Platform: {c.platform_name} | Key: {c.config_key} | Value: {c.config_value}")
