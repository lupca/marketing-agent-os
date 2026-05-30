# graphs/commit.py
import logging
import uuid
from graphs.state import AgencyState
from core.decision_logger import log_decision

logger = logging.getLogger("graphs_commit")
logging.basicConfig(level=logging.INFO)

def commit_node(state: AgencyState) -> dict:
    """
    State Schema Transformation (Garbage Collection at the Border).
    Extracts clean BusinessBrief from DraftPlan, resets the messages history to prevent memory bloat,
    and copies metrics into the flat AgencyState attributes for backwards-compatibility.
    """
    logger.info("Executing State Schema Transformation Commit Node...")
    
    draft = state.get("draft_plan") or {}
    workspace_id = state.get("workspace_id")
    campaign_id = state.get("campaign_id")
    product_id = state.get("product_id")
    
    # 1. Gather values
    final_budget = draft.get("test_budget") or state.get("test_budget") or 2000000.0
    final_cpa = draft.get("target_cpa") or state.get("target_cpa") or 150000.0
    notes = draft.get("notes_for_creative") or ""
    
    # 2. Build BusinessBrief
    brief = {
        "campaign_id": campaign_id,
        "product_id": product_id,
        "final_budget": final_budget,
        "final_cpa": final_cpa,
        "strategic_notes": notes
    }
    
    logger.info(f"Committed Business Brief! Final Budget: {final_budget:,.0f} VNĐ, Final CPA: {final_cpa:,.0f} VNĐ")
    
    # 3. Log the decision
    log_decision(
        workspace_id=workspace_id,
        campaign_id=campaign_id,
        agent_name="Commit Node",
        action="State Schema Transformation",
        decision_status="success",
        reason=f"Đúc JSON Brief thành công. Thực hiện dọn dẹp lịch sử đàm phán (messages = []) để chuyển giao sang phòng Sáng tạo.",
        metadata=brief
    )
    
    # 4. Return new state updating business_brief and resetting messages to empty
    return {
        "business_brief": brief,
        # Sync to flat fields for downstream compatibility
        "test_budget": final_budget,
        "target_cpa": final_cpa,
        "messages": [], # Reset messages list (Garbage Collection!)
        "sop_stage": "creative_generation"
    }
