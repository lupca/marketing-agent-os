# tests/test_workflow.py
import os
import sys
import uuid
import unittest
from langchain_core.messages import HumanMessage

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from db.seed import seed_database
from core.models import PlatformVariant, MasterContent
from graphs.main_router import graph
from tests.mock_ollama import LocalOllamaTestCase

# Query seeded Workspace & Product IDs dynamically from DB to avoid hardcoding
def _get_test_seeded_ids():
    from core.models import Workspace, ProductService
    with SessionLocal() as db:
        ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        if not ws:
            ws = db.query(Workspace).first()
        ws_id = str(ws.id) if ws else "00000000-0000-0000-0000-000000000002"
        
        prod = None
        if ws:
            prod = db.query(ProductService).filter_by(workspace_id=ws.id).first()
        if not prod:
            prod = db.query(ProductService).first()
        prod_id = str(prod.id) if prod else "00000000-0000-0000-0000-000000000005"
        
        return ws_id, prod_id

SEED_WORKSPACE_ID, SEED_PRODUCT_ID = _get_test_seeded_ids()

class TestMultiAgentWorkflow(LocalOllamaTestCase):
    
    def setUp(self):
        super().setUp()
        self.db = SessionLocal()
        seed_database(self.db)
        self.thread_id = str(uuid.uuid4())
        
    def tearDown(self):
        self.db.close()
        super().tearDown()
        
    def test_full_agent_workflow(self):
        """Simulate the complete SOP sequence and verify that it halts at the approval barrier."""
        print(f"\n[START WORKFLOW TEST] Thread ID: {self.thread_id}")
        
        config = {
            "configurable": {
                "thread_id": self.thread_id,
                "workspace_id": SEED_WORKSPACE_ID,
                "product_id": SEED_PRODUCT_ID
            }
        }
        
        initial_state = {
            "messages": [HumanMessage(content="Lên camp mới cho sản phẩm G-Agent Tech")],
            "current_channel": "#phong-kinh-doanh",
            "workspace_id": SEED_WORKSPACE_ID,
            "product_id": SEED_PRODUCT_ID,
            "sop_stage": "triage",
            "feedback_log": [],
            "killed_variants_feedback": []
        }
        
        # 1. Step through LangGraph (Phase 1: Triage -> Analyst -> Draft Approval pause)
        print("Stepping through LangGraph Nodes (Phase 1)...")
        for event in graph.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                print(f" -> Completed Node: '{node_name}'")
                if node_name == "analyst":
                    self.assertIn("target_cpa", node_update)
                    self.assertIn("test_budget", node_update)
                    self.assertEqual(node_update["target_cpa"], 1050000.0)
                    self.assertEqual(node_update["test_budget"], 2000000.0)
                    print(f"    [CHECK] Analyst Node calculated CPA target successfully: {node_update['target_cpa']} VNĐ")
                    
        # Verify graph paused at draft approval barrier (waiting_draft_approval)
        current_state = graph.get_state(config)
        self.assertTrue(len(current_state.next) > 0)
        self.assertEqual(current_state.next[0], "waiting_draft_approval")
        print("    [SUCCESS] LangGraph successfully paused at draft approval barrier!")
        
        # Resume Phase 2: Approve the draft plan to trigger strategist, copywriter, and brand guardian
        print("CMO approved draft plan. Resuming to Creative Graph (Phase 2)...")
        graph.update_state(config, {"draft_approved": True})
        
        for event in graph.stream(None, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                print(f" -> Completed Node: '{node_name}'")
                if node_name == "creative_subgraph":
                    self.assertIn("master_content", node_update)
                    self.assertIn("variants", node_update)
                    print(f"    [CHECK] Creative Sub-graph generated Core message and variants successfully!")
                    
        # 2. Verify graph paused at copy approval barrier (waiting_approval_barrier)
        current_state = graph.get_state(config)
        self.assertTrue(len(current_state.next) > 0)
        self.assertEqual(current_state.next[0], "waiting_approval_barrier")
        print("    [SUCCESS] LangGraph successfully paused at copy approval barrier for Human-in-the-loop!")
        
        # 3. Resume the graph (Approve the proposed copy)
        print("CEO approved kịch bản. Resuming LangGraph workflow...")
        
        # Count variants before resume
        vars_count_before = self.db.query(PlatformVariant).count()
        
        # Stream resume by passing None to the memory saver config
        for event in graph.stream(None, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                print(f" -> Resumed Node: '{node_name}'")
                
        # 4. Verify publisher stored content in database
        vars_count_after = self.db.query(PlatformVariant).count()
        self.assertTrue(vars_count_after > vars_count_before)
        
        # Query saved variant
        saved_var = self.db.query(PlatformVariant).order_by(PlatformVariant.created_at.desc()).first()
        self.assertIsNotNone(saved_var)
        self.assertEqual(saved_var.publish_status, "scheduled")
        print(f"    [SUCCESS] Kịch bản saved to DB. Publish Status: {saved_var.publish_status}")
        print("    [CHECK] Adapted Copy:\n", saved_var.adapted_copy)
        
        print("[WORKFLOW TEST COMPLETED SUCCESSFULLY!]")

    def test_research_routing_workflow(self):
        """Simulate the general policy query and verify that it routes to Researcher Node and runs RAG QA."""
        print(f"\n[START RESEARCH ROUTING TEST] Thread ID: {self.thread_id}")
        
        config = {
            "configurable": {
                "thread_id": self.thread_id,
                "workspace_id": SEED_WORKSPACE_ID,
                "product_id": SEED_PRODUCT_ID
            }
        }
        
        initial_state = {
            "messages": [HumanMessage(content="Quảng cáo bị Facebook quét từ khóa cấm là gì?")],
            "current_channel": "#phong-sang-tao",
            "workspace_id": SEED_WORKSPACE_ID,
            "product_id": SEED_PRODUCT_ID,
            "sop_stage": "triage",
            "feedback_log": [],
            "killed_variants_feedback": []
        }
        
        # Step through LangGraph
        print("Stepping through LangGraph Nodes for Research intent...")
        stages_hit = []
        for event in graph.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                print(f" -> Completed Node: '{node_name}'")
                stages_hit.append(node_name)
                
                if node_name == "researcher_agent":
                    self.assertIn("messages", node_update)
                    report_msg = node_update["messages"][-1].content
                    self.assertTrue(len(report_msg) > 50)
                    self.assertIn("Facebook", report_msg)
                    print(f"    [SUCCESS] Researcher synthesized report successfully:\n{report_msg[:200]}...")
                    
        self.assertIn("triage", stages_hit)
        self.assertIn("researcher_agent", stages_hit)
        print("[RESEARCH ROUTING TEST COMPLETED SUCCESSFULLY!]")

if __name__ == "__main__":
    unittest.main()
