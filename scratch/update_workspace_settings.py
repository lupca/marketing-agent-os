# scratch/update_workspace_settings.py
import sys
import os
import uuid
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from core.models import Workspace

db = SessionLocal()
try:
    ws_id = uuid.UUID("f97b5622-fecd-4d7e-9e12-49ecc2249793")
    ws = db.query(Workspace).filter_by(id=ws_id).first()
    if not ws:
        print("Workspace not found!")
    else:
        print("Workspace found, old settings:", ws.settings)
        ws.settings = {
            "currency": "VND", 
            "timezone": "Asia/Ho_Chi_Minh",
            "ai_api_url": "http://localhost:11434/v1",
            "ai_model": "Qwen/Qwen2.5-7B-Instruct",
            "siliconflow_api_key": "dummy_key_for_testing_do_not_use_cloud"
        }
        db.commit()
        print("Successfully updated workspace settings to seeded defaults!")
finally:
    db.close()
