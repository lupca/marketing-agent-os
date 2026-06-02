import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import uuid
from core.dependencies import get_session
from core.models import Workspace

with get_session() as db:
    ws = db.query(Workspace).filter_by(id='00000000-0000-0000-0000-000000000002').first()
    if ws:
        print("Initial settings:", ws.settings)
        # Modify a key
        current_settings = dict(ws.settings) if ws.settings else {}
        current_settings["siliconflow_api_key"] = "test_key_" + str(uuid.uuid4())[:8]
        ws.settings = current_settings
        db.commit()

with get_session() as db2:
    ws2 = db2.query(Workspace).filter_by(id='00000000-0000-0000-0000-000000000002').first()
    print("Settings after commit:", ws2.settings)
