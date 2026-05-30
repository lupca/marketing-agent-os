# scratch/test_graph_stream.py
import sys
import os
import uuid
from langchain_core.messages import HumanMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from db.seed import seed_database
from graphs.main_router import graph

db = SessionLocal()
seed_database(db)
db.close()

thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        "thread_id": thread_id,
        "workspace_id": "00000000-0000-0000-0000-000000000002",
        "product_id": "00000000-0000-0000-0000-000000000005"
    }
}

initial_state = {
    "messages": [HumanMessage(content="Lên camp mới cho sản phẩm G-Agent Tech")],
    "current_channel": "#phong-kinh-doanh",
    "workspace_id": "00000000-0000-0000-0000-000000000002",
    "product_id": "00000000-0000-0000-0000-000000000005",
    "sop_stage": "triage",
    "feedback_log": [],
    "killed_variants_feedback": []
}

print(f"Starting graph stream with thread_id: {thread_id}...")
try:
    for event in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, node_update in event.items():
            print(f"\n====== COMPLETED NODE: '{node_name}' ======")
            print(node_update)
except Exception as e:
    print(f"Error during graph execution: {e}")
