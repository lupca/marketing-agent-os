# graphs/main_router.py
import logging
import asyncio
from langgraph.graph import StateGraph, START, END
from graphs.state import AgencyState
from graphs.business import analyst_node, performance_node
from graphs.creative import strategist_node, copywriter_node, brand_guardian_node
from graphs.researcher import researcher_node
from graphs.creative_reporter import creative_report_node
from graphs.triage import triage_node, route_after_triage
from graphs.publisher import publisher_node, waiting_approval_barrier_node, route_after_guardian
from graphs.chat import chat_node
from graphs.negotiator import negotiator_node
from graphs.commit import commit_node
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

# ----------------- Build LangGraph StateGraph -----------------

builder = StateGraph(AgencyState)

# Add Nodes
builder.add_node("triage", triage_node)
builder.add_node("analyst", analyst_node)
builder.add_node("performance", performance_node)
builder.add_node("negotiator", negotiator_node)
builder.add_node("waiting_draft_approval", waiting_draft_approval_node)
builder.add_node("commit_node", commit_node)
builder.add_node("strategist", strategist_node)
builder.add_node("copywriter", copywriter_node)
builder.add_node("guardian", brand_guardian_node)
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
builder.add_edge("commit_node", "strategist")
builder.add_edge("strategist", "copywriter")
builder.add_edge("copywriter", "guardian")
builder.add_edge("researcher_agent", END)
builder.add_edge("chat_agent", END)
builder.add_edge("creative_report_agent", END)

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
graph = builder.compile(
    checkpointer=postgres_checkpointer,
    interrupt_before=["waiting_draft_approval", "waiting_approval_barrier"]
)
