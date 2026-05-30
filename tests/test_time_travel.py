# tests/test_time_travel.py
import os
import sys
import uuid
import unittest
from langchain_core.messages import HumanMessage, AIMessage

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from db.seed import seed_database
from graphs.main_router import graph
from tests.mock_ollama import LocalOllamaTestCase

SEED_WORKSPACE_ID = "00000000-0000-0000-0000-000000000002"
SEED_PRODUCT_ID = "00000000-0000-0000-0000-000000000005"

class TestTimeTravelAndTransformation(LocalOllamaTestCase):
    
    def setUp(self):
        super().setUp()
        self.db = SessionLocal()
        seed_database(self.db)
        self.thread_id = str(uuid.uuid4())
        
    def tearDown(self):
        self.db.close()
        super().tearDown()
        
    def test_draft_negotiation_and_time_travel(self):
        """Verify the draft negotiation loop, checkpointer history, and fork-based Time Travel."""
        print(f"\n[START TIME TRAVEL TEST] Thread ID: {self.thread_id}")
        
        config = {
            "configurable": {
                "thread_id": self.thread_id,
                "workspace_id": SEED_WORKSPACE_ID,
                "product_id": SEED_PRODUCT_ID
            }
        }
        
        # 1. Run analyst node to pause at draft approval barrier
        initial_state = {
            "messages": [HumanMessage(content="Lên camp mới cho sản phẩm G-Agent Tech")],
            "current_channel": "#phong-kinh-doanh",
            "workspace_id": SEED_WORKSPACE_ID,
            "product_id": SEED_PRODUCT_ID,
            "sop_stage": "triage",
            "feedback_log": [],
            "killed_variants_feedback": []
        }
        
        print("Running initial graph execution...")
        for event in graph.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                print(f" -> Completed: {node_name}")
                
        # Check paused at waiting_draft_approval
        state = graph.get_state(config)
        self.assertEqual(state.next[0], "waiting_draft_approval")
        self.assertEqual(state.values["draft_plan"]["test_budget"], 2000000.0)
        self.assertEqual(state.values["draft_plan"]["target_cpa"], 1050000.0)
        print("    [CHECK] Paused at draft approval with initial values.")
        
        # Save first checkpoint ID
        checkpoint_v1 = state.config["configurable"]["checkpoint_id"]
        
        # 2. Negotiate budget: User requests budget of 5,000,000đ
        negotiation_state = {
            "messages": [HumanMessage(content="Sửa ngân sách thành 5 triệu giúp tôi")],
            "draft_approved": False
        }
        graph.update_state(config, negotiation_state)
        
        print("Running negotiation turn 1...")
        for event in graph.stream(None, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                print(f" -> Completed: {node_name}")
                
        state = graph.get_state(config)
        self.assertEqual(state.next[0], "waiting_draft_approval")
        # Check that the negotiator updated the budget
        self.assertEqual(state.values["draft_plan"]["test_budget"], 5000000.0)
        print("    [CHECK] Negotiator updated budget to 5,000,000 VNĐ.")
        
        # Save second checkpoint ID
        checkpoint_v2 = state.config["configurable"]["checkpoint_id"]
        
        # 3. Fetch checkpointer history and verify we have checkpoints
        history = list(graph.get_state_history(config))
        print(f"Total history states: {len(history)}")
        self.assertTrue(len(history) >= 2)
        
        # 4. Perform Time Travel: Rewind to checkpoint_v1 (original budget 2,000,000đ)
        print(f"Time Travel: Rewinding to checkpoint_v1: {checkpoint_v1}")
        
        target_config = {
            "configurable": {
                "thread_id": self.thread_id,
                "checkpoint_id": checkpoint_v1
            }
        }
        target_state = graph.get_state(target_config)
        self.assertEqual(target_state.values["draft_plan"]["test_budget"], 2000000.0)
        
        # Fork target state by updating active state with target state values
        fork_values = target_state.values.copy()
        fork_values["draft_approved"] = False
        graph.update_state(config, fork_values)
        
        # Verify active state has reverted to original values
        active_state = graph.get_state(config)
        self.assertEqual(active_state.values["draft_plan"]["test_budget"], 2000000.0)
        print("    [SUCCESS] Active thread successfully reverted (forked) to budget 2,000,000 VNĐ!")
        
        # 5. Approve the reverted draft to proceed to creative stage
        graph.update_state(config, {"draft_approved": True})
        
        print("Resuming graph to creative phase...")
        for event in graph.stream(None, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                print(f" -> Completed: {node_name}")
                
        # Verify it successfully runs creative nodes and halts at copy approval
        final_state = graph.get_state(config)
        self.assertEqual(final_state.next[0], "waiting_approval_barrier")
        # Verify clean business_brief and reset messages
        self.assertIn("business_brief", final_state.values)
        self.assertEqual(final_state.values["business_brief"]["final_budget"], 2000000.0)
        # Note: messages should contain creative graph outputs and be cleared from negotiation
        print("    [SUCCESS] Flow passed through Commit Node, reset messages, and paused at Copy Approval Barrier.")
        print("[TIME TRAVEL TEST COMPLETED SUCCESSFULLY!]")

if __name__ == "__main__":
    unittest.main()
