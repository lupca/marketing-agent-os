import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from app import fastapi_app
from core.dependencies import get_session
from core.models import Workspace

client = TestClient(fastapi_app)

# Query current key
with get_session() as db:
    ws = db.query(Workspace).filter_by(id='00000000-0000-0000-0000-000000000002').first()
    print("DB key before request:", ws.settings.get("siliconflow_api_key"))

# Send POST request
payload = {
    "ai_model": "Qwen/Qwen3.6-35B-A3B",
    "temperature": 0.2,
    "max_tokens": 14000,
    "recursion_limit": 5,
    "reranker_mode": "local",
    "siliconflow_api_key": "updated_test_api_key_via_fastapi",
    "ai_api_url": "https://api.siliconflow.com/v1",
    "enable_thinking": False
}

response = client.post(
    "/api/workspace/settings?workspace_id=00000000-0000-0000-0000-000000000002",
    json=payload
)
print("Response:", response.status_code, response.json())

# Query DB key after request
with get_session() as db2:
    ws2 = db2.query(Workspace).filter_by(id='00000000-0000-0000-0000-000000000002').first()
    print("DB key after request:", ws2.settings.get("siliconflow_api_key"))
