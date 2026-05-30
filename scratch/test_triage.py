# scratch/test_triage.py
import sys
import os
from langchain_core.messages import HumanMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graphs.state import AgencyState
from graphs.triage import triage_node

# Setup simple mock state
state: AgencyState = {
    "messages": [HumanMessage(content="Lên camp mới cho sản phẩm G-Agent Tech")],
    "current_channel": "#phong-sang-tao",
    "workspace_id": "00000000-0000-0000-0000-000000000002",
    "product_id": "00000000-0000-0000-0000-000000000005",
    "sop_stage": "triage",
    "feedback_log": [],
    "killed_variants_feedback": [],
    "campaign_id": "",
    "target_cpa": 0.0,
    "test_budget": 0.0,
    "current_angle": {},
    "master_content": {},
    "variants": [],
    "intent_classification": "",
    "is_follow_up": False,
    "extracted_entities": {},
    "routing_thought_process": ""
}

print("Calling triage_node...")
res = triage_node(state)
print("Finished calling triage_node! Result:")
print(res)
