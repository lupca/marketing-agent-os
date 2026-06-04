# graphs/main_router.py
import logging
from langgraph.graph import StateGraph, START, END
from graphs.supervisor.state import AgencyState
from graphs.autonomous_nodes import (
    scoring_node, action_selector_node, creative_generation_node,
    guardian_sandbox_node, insight_generator_node, publisher_node
)

logger = logging.getLogger("graphs_main_router")
logging.basicConfig(level=logging.INFO)

def route_after_guardian(state: AgencyState) -> str:
    """
    Conditional routing edge for Brand Safety Sandbox.
    If FAIL -> route back to creative_generation for correction (max 3 attempts).
    If PASS -> route to insight_generator and then publisher.
    """
    feedbacks = state.get("sandbox_feedbacks") or []
    if feedbacks and len(feedbacks) < 3:
        logger.warning(f"Brand Safety violations detected ({len(feedbacks)}). Routing back to creative_generation...")
        return "creative_generation"
    logger.info("Brand Safety passed or max retries reached. Proceeding to insight_generator.")
    return "insight_generator"

# Initialize Stateless StateGraph with lightweight AgencyState
builder = StateGraph(AgencyState)

# 1. Add Stateless Nodes
builder.add_node("scoring", scoring_node)
builder.add_node("selector", action_selector_node)
builder.add_node("creative_generation", creative_generation_node)
builder.add_node("guardian_sandbox", guardian_sandbox_node)
builder.add_node("insight_generator", insight_generator_node)
builder.add_node("publisher", publisher_node)

def route_after_selector(state: AgencyState) -> str:
    """
    Conditional routing edge for Selector.
    If _skip_generation is True, skip creative_generation and go directly to publisher
    (used in Darwin Pruning / Overload scenarios).
    """
    if state.get("_skip_generation"):
        logger.info("Skip Generation flag is True (Darwin Pruning). Bypassing creative_generation directly to publisher.")
        return "publisher"
    return "creative_generation"

# 2. Add Stateless Uninterrupted Edges
builder.add_edge(START, "scoring")
builder.add_edge("scoring", "selector")

# Conditional Edge for Selector to skip generation if needed
builder.add_conditional_edges(
    "selector",
    route_after_selector,
    {
        "creative_generation": "creative_generation",
        "publisher": "publisher"
    }
)
builder.add_edge("creative_generation", "guardian_sandbox")

# 3. Add Conditional Edge for Guardian Compliance check
builder.add_conditional_edges(
    "guardian_sandbox",
    route_after_guardian,
    {
        "creative_generation": "creative_generation",
        "insight_generator": "insight_generator"
    }
)

builder.add_edge("insight_generator", "publisher")
builder.add_edge("publisher", END)

# Compile Graph (NO checkpointers, NO interrupts to keep it 100% Stateless and RAM-friendly)
graph = builder.compile()
logger.info("Stateless Creative Intelligence Engine Graph with Conditional Safety loop compiled successfully!")
