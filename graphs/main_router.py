# graphs/main_router.py
import logging
import asyncio
from langgraph.graph import StateGraph, START, END
from graphs.supervisor.state import AgencyState
from graphs.business.business import analyst_node, performance_node
from graphs.creative.creative_subgraph import creative_graph
from graphs.research.researcher import researcher_node
from graphs.creative.creative_reporter import creative_report_node
from graphs.supervisor.triage import triage_node, route_after_triage
from graphs.creative.publisher import publisher_node, waiting_approval_barrier_node
from graphs.supervisor.chat import chat_node
from graphs.business.negotiator import negotiator_node
from graphs.business.commit import commit_node
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from db.connection import POSTGRES_URL, PSYCOPG_CONNINFO

logger = logging.getLogger("graphs_main_router")
logging.basicConfig(level=logging.INFO)

# ----------------- Lazy PostgreSQL Saver for LangGraph -----------------

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

    def _run_sync(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import threading
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result()
        else:
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

    def get_tuple(self, config):
        return self._run_sync(self.saver.aget_tuple(config))

    def put(self, config, checkpoint, metadata, new_versions):
        return self._run_sync(self.saver.aput(config, checkpoint, metadata, new_versions))

    def put_writes(self, config, writes, task_id):
        return self._run_sync(self.saver.aput_writes(config, writes, task_id))

    def list(self, config, *args, **kwargs):
        async def collect():
            return [x async for x in self.saver.alist(config, *args, **kwargs)]
        return self._run_sync(collect())

    async def aget_tuple(self, config):
        return await self.saver.aget_tuple(config)

    async def aput(self, config, checkpoint, metadata, new_versions):
        return await self.saver.aput(config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id):
        return await self.saver.aput_writes(config, writes, task_id)

    async def alist(self, config, *args, **kwargs):
        async for checkpoint_tuple in self.saver.alist(config, *args, **kwargs):
            yield checkpoint_tuple
        
    async def setup(self):
        await self.saver.setup()

    def get_next_version(self, current, channel):
        return self.saver.get_next_version(current, channel)

import sys
import os
from langgraph.checkpoint.memory import MemorySaver

# Detect if we are running under testing environment (pytest, unittest, etc.)
is_testing = (
    "unittest" in sys.modules
    or "pytest" in sys.modules
    or (len(sys.argv) > 0 and "pytest" in sys.argv[0])
    or os.getenv("TESTING") == "true"
)

if is_testing:
    logger.info("TESTING MODE DETECTED: Utilizing in-memory MemorySaver checkpointer.")
    postgres_checkpointer = MemorySaver()
else:
    # Establish Connection Pool for LangGraph AsyncPostgresSaver checkpointer in production
    postgres_pool = AsyncConnectionPool(
        conninfo=PSYCOPG_CONNINFO,
        max_size=10,
        open=False, # Prevent opening immediately during module import without a running loop
        kwargs={"autocommit": True, "row_factory": dict_row}
    )

    postgres_checkpointer = LazyPostgresSaver(postgres_pool)

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


# ----------------- v3.2 Negotiation & Commit Nodes -----------------

def waiting_draft_approval_node(state: AgencyState) -> dict:
    """A barrier node where LangGraph will pause (interrupt_before) awaiting draft approval."""
    logger.info("LangGraph paused at draft approval barrier. Awaiting CMO approval...")
    return {"sop_stage": "waiting_draft_approval"}

def route_after_draft_barrier(state: AgencyState) -> str:
    """Conditional routing after draft approval barrier."""
    if state.get("draft_approved"):
        return "commit_node"
    return "negotiator"

def intelligence_node(state: AgencyState) -> dict:
    """
    Intelligence Node (Market Intelligence Agent).
    Checks CPA and product constraints, fetches competitor kịch bản & comments from SerpApi,
    pre-processes them with LLM to extract hook/sentiment/pain-points, cold-stores raw files,
    and vectorizes findings in pgvector RAG for the Strategist Agent.
    """
    logger.info("Executing Intelligence Node (SerpApi YouTube Competitor Research)...")
    from core.market_intelligence import fetch_and_process_market_data
    from core.dependencies import get_session
    from langchain_core.messages import AIMessage
    from core.decision_logger import log_decision
    
    workspace_id = state.get("workspace_id")
    business_context = state.get("business_context") or {}
    product_name = business_context.get("product", {}).get("name") or "Marketing OS Software"

    with get_session() as db:
        try:
            logger.info(f"Running SerpApi competitor research for query: '{product_name}'...")
            processed_videos = fetch_and_process_market_data(db, str(workspace_id), product_name, limit=3)
            
            if processed_videos:
                report_content = (
                    f"🔍 **[Market Intelligence]** Đã hoàn tất phân tích `{len(processed_videos)} kịch bản đối thủ`!\n"
                    f"- Raw JSON được lưu giữ vĩnh viễn trong bucket `market-intel-raw` (Cold Storage).\n"
                    f"- Tài liệu phân tích tinh hoa đã được tự động băm vector vào Knowledge Base (Hot Storage) với nhãn `market_intel`.\n"
                    f"- **Danh sách video đối thủ đã xử lý:**\n"
                )
                for idx, pv in enumerate(processed_videos):
                    meta = pv["analysis"]
                    report_content += (
                        f"  {idx+1}. **{pv['title']}** (Kênh: *{pv['channel']}*)\n"
                        f"     - Hook bóc tách: *\"{meta.get('hook', 'N/A')}\"* (Loại: {meta.get('hook_type', 'N/A')})\n"
                        f"     - Sentiment bình luận: Tích cực {meta.get('sentiment', {}).get('positive_pct', 0)}%, Tiêu cực {meta.get('sentiment', {}).get('negative_pct', 0)}%\n"
                        f"     - Pain Points tìm thấy: {', '.join(meta.get('pain_points', []))}\n"
                    )
            else:
                report_content = (
                    f"🔍 **[Market Intelligence]** Không tìm thấy kịch bản đối thủ mới liên quan đến sản phẩm `{product_name}`. "
                    f"Hệ thống sẽ sử dụng tri thức sẵn có từ Knowledge Base."
                )

            log_decision(
                workspace_id=workspace_id,
                campaign_id=state.get("campaign_id"),
                agent_name="Market Intelligence Agent",
                action="Fetch Competitor Intel",
                decision_status="success",
                reason=f"Đã cào và xử lý thành công {len(processed_videos)} kịch bản đối thủ từ YouTube qua SerpApi.",
                metadata={"processed_videos_count": len(processed_videos)}
            )
            
            return {
                "sop_stage": "creative_generation",
                "messages": [AIMessage(content=report_content)]
            }
        except Exception as e:
            logger.error(f"Intelligence Node failed: {e}", exc_info=True)
            fallback_msg = f"🔍 **[Market Intelligence]** [Cảnh báo] Lỗi kết nối SerpApi. Bỏ qua tìm kiếm trực tiếp và sử dụng dữ liệu RAG sẵn có."
            return {
                "sop_stage": "creative_generation",
                "messages": [AIMessage(content=fallback_msg)]
            }

# ----------------- Build LangGraph StateGraph -----------------

builder = StateGraph(AgencyState)

# Add Nodes
builder.add_node("triage", triage_node)
builder.add_node("analyst", analyst_node)
builder.add_node("performance", performance_node)
builder.add_node("negotiator", negotiator_node)
builder.add_node("waiting_draft_approval", waiting_draft_approval_node)
builder.add_node("commit_node", commit_node)
builder.add_node("intelligence_node", intelligence_node)
builder.add_node("creative_subgraph", creative_graph)
builder.add_node("waiting_approval_barrier", waiting_approval_barrier_node)
builder.add_node("publisher", publisher_node)
builder.add_node("researcher_agent", researcher_node)
builder.add_node("chat_agent", chat_node)
builder.add_node("creative_report_agent", creative_report_node)

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
        "chat_agent": "chat_agent",
        "creative_report_agent": "creative_report_agent",
        "end": END
    }
)

# Standard flows
builder.add_edge("analyst", "waiting_draft_approval")
builder.add_conditional_edges(
    "waiting_draft_approval",
    route_after_draft_barrier,
    {
        "commit_node": "commit_node",
        "negotiator": "negotiator"
    }
)
builder.add_edge("negotiator", "waiting_draft_approval")
builder.add_edge("commit_node", "intelligence_node")
builder.add_edge("intelligence_node", "creative_subgraph")
builder.add_edge("creative_subgraph", "waiting_approval_barrier")
builder.add_edge("researcher_agent", END)
builder.add_edge("chat_agent", END)
builder.add_edge("creative_report_agent", END)

# Post barrier
builder.add_edge("waiting_approval_barrier", "publisher")
builder.add_edge("publisher", END)
builder.add_edge("performance", END)

# Compile Graph with Interrupt before Sếp review barrier
graph = builder.compile(
    checkpointer=postgres_checkpointer,
    interrupt_before=["waiting_draft_approval", "waiting_approval_barrier"]
)
