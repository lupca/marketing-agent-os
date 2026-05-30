# graphs/main_router.py
import logging
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage
from graphs.state import AgencyState
from graphs.business import analyst_node, performance_node
from graphs.creative import strategist_node, copywriter_node, brand_guardian_node
from core.ollama_client import generate_text, get_embedding
from graphs.researcher import researcher_node
from db.connection import SessionLocal
from core.models import IntentRoutingKnowledge
from core.decision_logger import log_decision

logger = logging.getLogger("graphs_main_router")
logging.basicConfig(level=logging.INFO)

# Triage Node (Supervisor Intent Router)
def triage_node(state: AgencyState) -> dict:
    """
    Triage Node (Supervisor) at the entry gateway.
    Classifies user message intent into 'chat', 'show_metrics', 'create_campaign', or 'research'.
    Uses database-driven vector similarity matching via pgvector cosine distance.
    """
    logger.info("Executing Triage Node (Database-Driven Vector Router)...")
    
    # Retrieve last user message
    messages = state.get("messages", [])
    if not messages:
        return {"sop_stage": "triage", "intent_classification": "research"}
        
    query = messages[-1].content.strip()
    
    intent = "research" # Fallback safe default (RAG QA)
    db = SessionLocal()
    
    try:
        query_vector = get_embedding(query)
        
        # Calculate cosine distance using pgvector operator
        distance_expr = IntentRoutingKnowledge.embedding.cosine_distance(query_vector)
        
        # Fetch closest matching utterance
        closest_match_data = db.query(IntentRoutingKnowledge, distance_expr).filter(
            IntentRoutingKnowledge.is_active == True
        ).order_by(distance_expr).first()
        
        if closest_match_data:
            record, distance = closest_match_data
            logger.info(f"Closest match utterance: '{record.utterance}' with cosine distance: {distance:.4f}")
            
            # Threshold check: distance < 0.30 (equivalent to similarity > 0.70)
            if distance < 0.30:
                intent = record.intent_category
                logger.info(f"Semantic Match Found: '{record.utterance}' -> Intent: {intent}")
            else:
                logger.warning(f"Closest match distance {distance:.4f} exceeds threshold 0.30. Fallback to 'research'.")
        else:
            logger.warning("No dynamic utterances found in intent_routing_knowledge table.")
            
    except Exception as e:
        logger.error(f"Semantic Router DB Error: {e}. Falling back to default 'research'.")
        # Fail fast as requested by Sếp
        raise RuntimeError(f"Lỗi hệ thống cửa ngõ: Không thể thực hiện phân tích định tuyến vector CSDL: {e}") from e
    finally:
        db.close()
        
    # Assign active UI channel based on intent
    channel = "#phong-sang-tao" if intent == "research" else "#phong-kinh-doanh"
    
    # Log triage routing decision
    ws_id = state.get("workspace_id") or "00000000-0000-0000-0000-000000000002"
    log_decision(
        workspace_id=ws_id,
        agent_name="Triage Node",
        action="Route Intent",
        decision_status="success",
        reason=f"Phân loại tin nhắn thành intent '{intent}'. Kênh điều hướng: {channel}",
        metadata={"intent": intent, "query": query}
    )
    
    return {
        "sop_stage": "triage",
        "intent_classification": intent,
        "current_channel": channel
    }

# Conditional routing from Triage
def route_after_triage(state: AgencyState) -> str:
    """
    Evaluates the classified intent in state and routes to the correct node.
    """
    intent = state.get("intent_classification", "research")
    logger.info(f"Conditional Router: routing state based on intent '{intent}'")
    if intent == "create_campaign":
        return "analyst"
    elif intent == "show_metrics":
        return "performance"
    elif intent == "research":
        return "researcher_agent"
    return "end"

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
        
        # Log publisher decision
        log_decision(
            workspace_id=ws_id,
            campaign_id=campaign_id,
            agent_name="Publisher Node",
            action="Approve & Publish",
            decision_status="success",
            reason=f"Duyệt và xuất bản thành công kịch bản. Lên lịch đăng {len(variants)} kịch bản chuyển đổi lên mạng xã hội.",
            metadata={"variants_count": len(variants), "master_content": master_data.get("core_message", "")}
        )
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
builder.add_node("researcher_agent", researcher_node)

# Add Edges
builder.add_edge(START, "triage")

# Triage conditional routing
builder.add_conditional_edges(
    "triage",
    route_after_triage,
    {
        "analyst": "analyst",
        "performance": "performance",
        "researcher_agent": "researcher_agent",
        "end": END
    }
)

# Standard flows
builder.add_edge("analyst", "strategist")
builder.add_edge("strategist", "copywriter")
builder.add_edge("copywriter", "guardian")
builder.add_edge("researcher_agent", END)

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
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from db.connection import POSTGRES_URL

class LazyPostgresSaver(BaseCheckpointSaver):
    def __init__(self, pool):
        super().__init__()
        self.pool = pool
        self._saver = None

    @property
    def saver(self):
        if self._saver is None:
            self._saver = AsyncPostgresSaver(self.pool)
        return self._saver

    def get_tuple(self, config):
        return self.saver.get_tuple(config)

    def put(self, config, checkpoint, metadata, new_versions):
        return self.saver.put(config, checkpoint, metadata, new_versions)

    def put_writes(self, config, writes, task_id):
        return self.saver.put_writes(config, writes, task_id)

    def list(self, config, *, before=None, limit=None):
        return self.saver.list(config, before=before, limit=limit)

    async def aget_tuple(self, config):
        return await self.saver.aget_tuple(config)

    async def aput(self, config, checkpoint, metadata, new_versions):
        return await self.saver.aput(config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id):
        return await self.saver.aput_writes(config, writes, task_id)

    async def alist(self, config, *, before=None, limit=None):
        return await self.saver.alist(config, before=before, limit=limit)
        
    async def setup(self):
        await self.saver.setup()

    def get_next_version(self, current, channel):
        return self.saver.get_next_version(current, channel)

# Establish Connection Pool for LangGraph AsyncPostgresSaver checkpointer
postgres_pool = AsyncConnectionPool(
    conninfo=POSTGRES_URL,
    max_size=10,
    open=False, # Prevent opening immediately during module import without a running loop
    kwargs={"autocommit": True, "row_factory": dict_row}
)

postgres_checkpointer = LazyPostgresSaver(postgres_pool)

import asyncio
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

async def setup_checkpointer():
    await postgres_pool.open()
    await postgres_checkpointer.setup()

if loop.is_running():
    loop.create_task(setup_checkpointer())
else:
    loop.run_until_complete(setup_checkpointer())

graph = builder.compile(
    checkpointer=postgres_checkpointer,
    interrupt_before=["waiting_approval_barrier"]
)
