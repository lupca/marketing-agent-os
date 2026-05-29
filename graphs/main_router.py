# graphs/main_router.py
import logging
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage
from graphs.state import AgencyState
from graphs.business import analyst_node, performance_node
from graphs.creative import strategist_node, copywriter_node, brand_guardian_node
from core.ollama_client import generate_text

logger = logging.getLogger("graphs_main_router")
logging.basicConfig(level=logging.INFO)

# Triage Node (Supervisor Intent Router)
def triage_node(state: AgencyState) -> dict:
    """
    Triage Node (Supervisor) at the entry gateway.
    Classifies user message intent into 'chat', 'show_metrics', or 'create_campaign'.
    Guarantees strict SOP starting path.
    """
    logger.info("Executing Triage Node (Supervisor Input Intent Classifier)...")
    
    # Retrieve last user message
    messages = state.get("messages", [])
    if not messages:
        return {"sop_stage": "triage"}
        
    last_msg = messages[-1].content.lower()
    
    # Simple keyword-based & LLM-aided classifier
    intent = "chat"
    if any(k in last_msg for k in ["báo cáo", "metrics", "số liệu", "chỉ số", "cpa tuần", "hiệu suất"]):
        intent = "show_metrics"
    elif any(k in last_msg for k in ["lên kịch bản", "viết bài", "camp mới", "tạo chiến dịch", "chiến dịch mới", "content"]):
        intent = "create_campaign"
    else:
        # LLM-assisted categorization to be highly precise
        prompt = (
            f"Classify the following User input into exactly one category: 'chat', 'show_metrics', or 'create_campaign'.\n"
            f"- 'create_campaign': User wants to create new campaigns, copywriting scripts, or content briefs.\n"
            f"- 'show_metrics': User wants reports, ads metrics, budget scale/kill reviews, or audit data.\n"
            f"- 'chat': Greeting, small talk, chit-chat.\n\n"
            f"User input: \"{messages[-1].content}\"\n"
            f"Category (one word only):"
        )
        res = generate_text(prompt, system_prompt="Answer with exactly one word: 'chat', 'show_metrics', or 'create_campaign'.")
        res_clean = res.strip().lower()
        if "create_campaign" in res_clean:
            intent = "create_campaign"
        elif "show_metrics" in res_clean:
            intent = "show_metrics"
            
    logger.info(f"Classified Intent: '{intent}'")
    
    # Save intent in messages or metadata
    return {
        "sop_stage": "triage",
        "current_channel": "#phong-kinh-doanh" if intent != "chat" else state.get("current_channel", "#phong-kinh-doanh")
    }

# Conditional routing from Triage
def route_after_triage(state: AgencyState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return END
        
    last_msg = messages[-1].content.lower()
    
    # Re-evaluate classified intent
    if any(k in last_msg for k in ["báo cáo", "metrics", "số liệu", "chỉ số", "cpa tuần", "hiệu suất"]):
        return "performance"
    elif any(k in last_msg for k in ["lên kịch bản", "viết bài", "camp mới", "tạo chiến dịch", "chiến dịch mới", "content"]):
        return "analyst"
    
    # Standard text-based fallback routing matching triage_node classification
    prompt = (
        f"Route user query. Answer with 'performance' for metrics/reports, "
        f"'analyst' for campaign creation, or 'end' for casual chat.\n"
        f"Query: \"{messages[-1].content}\"\n"
        f"Answer:"
    )
    res = generate_text(prompt).strip().lower()
    if "analyst" in res:
        return "analyst"
    elif "performance" in res:
        return "performance"
    return END

# Conditional routing from Brand Guardian (Scoring Gatekeeper)
def route_after_guardian(state: AgencyState) -> str:
    stage = state.get("sop_stage")
    logs = state.get("feedback_log", [])
    
    # Check if maximum review loops exceeded (Max 3 loops to avoid infinite cycle)
    if len(logs) >= 3:
        logger.warning("Max rewrite iterations (3) reached! Automatically passing to CEO review with warning.")
        return "waiting_approval_barrier"
        
    if stage == "waiting_approval":
        return "waiting_approval_barrier"
        
    # Return to Copywriter for revisions
    logger.warning("Feedback rewrite triggered! Routing back to Copywriter Node.")
    return "copywriter"

# Mock waiting approval node (barrier for interrupt_before)
def waiting_approval_barrier_node(state: AgencyState) -> dict:
    """A barrier node where LangGraph will pause (interrupt_before) awaiting human approval."""
    logger.info("LangGraph paused at approval barrier. Awaiting Sếp approval...")
    return {"sop_stage": "waiting_approval"}

# Publisher Node (Executed post-approval)
def publisher_node(state: AgencyState) -> dict:
    """
    Publisher Node (Ban Sáng Tạo).
    Executes after Sếp click '[Duyệt và Đăng]'. Saves variant to database.
    """
    logger.info("CEO Approved! Publishing kịch bản to PostgreSQL database...")
    
    # Save published variants to database
    import uuid
    from sqlalchemy.orm import Session
    from db.connection import SessionLocal
    from core.models import PlatformVariant, MasterContent
    
    db: Session = SessionLocal()
    workspace_id = state.get("workspace_id")
    campaign_id = state.get("campaign_id")
    product_id = state.get("product_id")
    variants = state.get("variants", [])
    master_data = state.get("master_content", {})
    
    try:
        from core.models import Workspace, MarketingCampaign
        ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        ws_id = ws.id if ws else uuid.UUID(str(workspace_id))
        
        # Resolve campaign_id NOT NULL constraint
        if not campaign_id:
            # Create a default campaign dynamically
            new_camp = MarketingCampaign(
                workspace_id=ws_id,
                product_id=uuid.UUID(str(product_id)) if product_id else None,
                name=f"Chiến dịch tự động {uuid.uuid4().hex[:6]}",
                status="active",
                budget=2000000.0
            )
            db.add(new_camp)
            db.commit()
            db.refresh(new_camp)
            campaign_id = str(new_camp.id)
            logger.info(f"Dynamically created campaign ID {campaign_id} for NOT NULL constraint.")
            
        # Save master content
        master = MasterContent(
            workspace_id=ws_id,
            campaign_id=uuid.UUID(str(campaign_id)),
            core_message=master_data.get("core_message", ""),
            approval_status="approved",
            meta_data=master_data
        )
        db.add(master)
        db.commit()
        
        # Save variants
        for v in variants:
            pv = PlatformVariant(
                workspace_id=ws_id,
                master_content_id=master.id,
                platform=v.get("platform", "facebook"),
                adapted_copy=v.get("adapted_copy", ""),
                publish_status="scheduled", # Scheduled for publishing
                content_type="text",
                meta_data=v
            )
            db.add(pv)
        db.commit()
        logger.info("Successfully persisted published campaign contents in database!")
    except Exception as e:
        logger.error(f"Error saving published contents: {e}")
    finally:
        db.close()
        
    return {"sop_stage": "execution"}

# ----------------- Build LangGraph StateGraph -----------------

builder = StateGraph(AgencyState)

# Add Nodes
builder.add_node("triage", triage_node)
builder.add_node("analyst", analyst_node)
builder.add_node("performance", performance_node)
builder.add_node("strategist", strategist_node)
builder.add_node("copywriter", copywriter_node)
builder.add_node("guardian", brand_guardian_node)
builder.add_node("waiting_approval_barrier", waiting_approval_barrier_node)
builder.add_node("publisher", publisher_node)

# Add Edges
builder.add_edge(START, "triage")

# Triage conditional routing
builder.add_conditional_edges(
    "triage",
    route_after_triage,
    {
        "analyst": "analyst",
        "performance": "performance",
        "end": END
    }
)

# Standard flows
builder.add_edge("analyst", "strategist")
builder.add_edge("strategist", "copywriter")
builder.add_edge("copywriter", "guardian")

# Guardian conditional check
builder.add_conditional_edges(
    "guardian",
    route_after_guardian,
    {
        "waiting_approval_barrier": "waiting_approval_barrier",
        "copywriter": "copywriter"
    }
)

# Post barrier
builder.add_edge("waiting_approval_barrier", "publisher")
builder.add_edge("publisher", END)
builder.add_edge("performance", END)

# Compile Graph with Interrupt before Sếp review barrier
# Postgres checkpointer is typically used, but Sqlite/Memory is fine for thread context.
# We interrupt exactly before the 'waiting_approval_barrier' node executes!
from langgraph.checkpoint.memory import MemorySaver
memory_checkpointer = MemorySaver()

graph = builder.compile(
    checkpointer=memory_checkpointer,
    interrupt_before=["waiting_approval_barrier"]
)
